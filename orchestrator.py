from __future__ import annotations
import json
import logging
import os
import time
from typing import List
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END

from schemas import (
    InputProfile,
    TickerInfo,
    FundamentalsReport,
    TechnicalReport,
    NewsReport,
    SectorMacroReport,
    AlternativesReport,
    DecisionPlan,
    AnalysisBundle,
)
from tools.resolver import resolve_to_ticker
from advisors.fundamentals_advisor import analyze_fundamentals
from advisors.technical_advisor import analyze_technical
from advisors.news_advisor import analyze_news
from advisors.sector_macro_advisor import analyze_sector_macro
from advisors.alternatives_advisor import analyze_alternatives
from llm import llm

logger = logging.getLogger("finbot.orchestrator")


class GraphState(TypedDict, total=False):
    company_name: str
    profile: InputProfile
    run_dir: str
    stream: bool
    committee_rounds: int
    ticker: TickerInfo
    fundamentals: FundamentalsReport
    technical: TechnicalReport
    news: NewsReport
    sector_macro: SectorMacroReport
    alternatives: AlternativesReport
    decision: DecisionPlan


def _save_json_if_possible(state: dict, filename: str, payload: dict) -> None:
    run_dir = state.get("run_dir")
    if not run_dir:
        return
    try:
        os.makedirs(run_dir, exist_ok=True)
        path = os.path.join(run_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.debug("Save failed for %s: %s", filename, e)


def node_resolve(state: GraphState) -> GraphState:
    start = time.perf_counter()
    name: str = state["company_name"]
    logger.debug("Stage resolve: input company='%s'", name)
    symbol = resolve_to_ticker(name) or name
    yf_symbol = symbol
    ticker = TickerInfo(name=name, exchange=None, symbol=symbol, yf_symbol=yf_symbol)
    _save_json_if_possible(state, "ticker.json", ticker.model_dump())
    logger.debug("Stage resolve: resolved to symbol='%s' (yf='%s') in %.2f ms", symbol, yf_symbol, (time.perf_counter() - start) * 1000)
    if state.get("stream"):
        logger.info("Resolved -> %s", yf_symbol)
    return {"ticker": ticker}


def node_fundamentals(state: GraphState) -> GraphState:
    start = time.perf_counter()
    ticker: TickerInfo = state["ticker"]
    logger.debug("Stage fundamentals: analyzing for %s", ticker.yf_symbol)
    report = analyze_fundamentals(ticker.yf_symbol, ticker.name)
    _save_json_if_possible(state, "fundamentals.json", report.model_dump())
    logger.debug(
        "Stage fundamentals: metrics=%d score=%.1f (%.2f ms)",
        len(report.metrics or {}),
        report.score,
        (time.perf_counter() - start) * 1000,
    )
    if state.get("stream"):
        logger.info("Fundamentals -> score %.1f (metrics=%d)", report.score, len(report.metrics or {}))
    return {"fundamentals": report}


def node_technical(state: GraphState) -> GraphState:
    start = time.perf_counter()
    ticker: TickerInfo = state["ticker"]
    logger.debug("Stage technical: analyzing for %s", ticker.yf_symbol)
    report = analyze_technical(ticker.yf_symbol)
    _save_json_if_possible(state, "technical.json", report.model_dump())
    logger.debug(
        "Stage technical: trend=%s keys=%s (%.2f ms)",
        report.trend,
        list((report.metrics or {}).keys()),
        (time.perf_counter() - start) * 1000,
    )
    if state.get("stream"):
        logger.info("Technical -> trend=%s", report.trend)
    return {"technical": report}


def node_news(state: GraphState) -> GraphState:
    start = time.perf_counter()
    ticker: TickerInfo = state["ticker"]
    logger.debug("Stage news: analyzing for %s", ticker.name)
    report = analyze_news(ticker.name)
    _save_json_if_possible(state, "news.json", report.model_dump())
    logger.debug(
        "Stage news: items=%d summary_len=%d (%.2f ms)",
        len(report.items or []),
        len(report.summary or ""),
        (time.perf_counter() - start) * 1000,
    )
    if state.get("stream"):
        logger.info("News -> %d items", len(report.items or []))
    return {"news": report}


def node_sector_macro(state: GraphState) -> GraphState:
    start = time.perf_counter()
    ticker: TickerInfo = state["ticker"]
    logger.debug("Stage sector_macro: analyzing for %s", ticker.name)
    report = analyze_sector_macro(ticker.name)
    _save_json_if_possible(state, "sector_macro.json", report.model_dump())
    logger.debug(
        "Stage sector_macro: summary_len=%d (%.2f ms)",
        len(report.summary or ""),
        (time.perf_counter() - start) * 1000,
    )
    if state.get("stream"):
        logger.info("Macro -> %d chars", len(report.summary or ""))
    return {"sector_macro": report}


def node_alternatives(state: GraphState) -> GraphState:
    start = time.perf_counter()
    ticker: TickerInfo = state["ticker"]
    logger.debug("Stage alternatives: analyzing for %s", ticker.name)
    report = analyze_alternatives(ticker.name)
    _save_json_if_possible(state, "alternatives.json", report.model_dump())
    logger.debug(
        "Stage alternatives: candidates=%d (%.2f ms)",
        len(report.candidates or []),
        (time.perf_counter() - start) * 1000,
    )
    if state.get("stream"):
        logger.info("Alternatives -> %d candidates", len(report.candidates or []))
    return {"alternatives": report}


def node_decide(state: GraphState) -> GraphState:
    start = time.perf_counter()
    ticker: TickerInfo = state["ticker"]
    profile: InputProfile = state["profile"]
    fundamentals: FundamentalsReport = state["fundamentals"]
    technical: TechnicalReport = state["technical"]
    news: NewsReport = state["news"]
    sector_macro: SectorMacroReport = state["sector_macro"]
    alternatives: AlternativesReport = state["alternatives"]
    max_rounds: int = int(state.get("committee_rounds", 0) or 0)

    prompt = f"""
You are a team lead investment advisor for Indian long-term investors. Decide Buy/Hold/Avoid with confidence (0-1), entry timing, simple position size (conservative/medium/aggressive with % guidance), risk controls (stops or time-based), and a clear rationale in simple English.

Inputs:
- Company: {ticker.name} ({ticker.yf_symbol})
- Profile: risk={profile.risk_level}, horizon_years={profile.horizon_years}
- Fundamentals: {fundamentals.model_dump()}
- Technical: {technical.model_dump()}
- News: {news.summary}
- Sector/Macro: {sector_macro.summary}
- Alternatives: {[c.model_dump() for c in alternatives.candidates]}
Return JSON with keys: decision, confidence, entry_timing, position_size, dca_plan, risk_controls, rationale.
"""
    logger.debug(
        "Stage decide: building plan for %s risk=%s horizon=%.2f",
        ticker.yf_symbol,
        profile.risk_level,
        profile.horizon_years,
    )
    # Safeguard extremely long inputs to the model
    def _truncate(text: str, max_len: int = 6000) -> str:
        return text if len(text) <= max_len else text[:max_len] + "\n...[truncated]"

    json_text = llm.reason(
        _truncate(prompt, 12000),
        system=(
            "Return ONLY valid JSON. Keep it conservative, avoid jargon, respect long-term focus and risk profile."
        ),
        response_format={"type": "json_object"},
    )
    import json

    data = {}
    try:
        data = json.loads(json_text)
    except Exception:
        data = {
            "decision": "Hold",
            "confidence": 0.5,
            "entry_timing": "staged over 4-8 weeks",
            "position_size": "moderate ~5% of portfolio",
            "dca_plan": "2-4 tranches",
            "risk_controls": {"stop": "break of 200DMA or -20%"},
            "rationale": "Holding pattern due to mixed signals.",
        }

    plan = DecisionPlan(
        decision=data.get("decision", "Hold"),
        confidence=float(data.get("confidence", 0.5)),
        entry_timing=data.get("entry_timing", "staged over 4-8 weeks"),
        position_size=data.get("position_size", "moderate ~5% of portfolio"),
        dca_plan=data.get("dca_plan"),
        risk_controls=data.get("risk_controls", {}),
        rationale=data.get("rationale", ""),
    )

    # Save initial proposal
    _save_json_if_possible(state, "decision_round0.json", plan.model_dump())

    # Optional round-robin discussion
    for round_idx in range(1, max_rounds + 1):
        if state.get("stream"):
            logger.info("Committee round %d: critique", round_idx)
        critique_prompt = (
            "Assume a round-table of 4 senior advisors (Fundamentals Lead, Technical Lead, Macro Lead, Risk Manager). "
            "Given the current plan and inputs, list concise critiques and suggested tweaks. Be practical and conservative.\n\n"
            f"Company: {ticker.name} ({ticker.yf_symbol})\n"
            f"Profile: risk={profile.risk_level}, horizon_years={profile.horizon_years}\n"
            f"Current Plan: {plan.model_dump()}\n"
            f"Key Technical: {technical.model_dump()}\n"
            f"Key Fundamentals: {fundamentals.model_dump()}\n"
            f"News: {news.summary[:1000]}\n"
            f"Macro: {sector_macro.summary[:800]}\n"
            f"Alternatives: {[c.model_dump() for c in alternatives.candidates]}\n"
            "Return bullets like '- [Role] Critique: ... | Change: ...'."
        )
        critique_text = llm.summarize(critique_prompt, system="You are chairing a concise, no-jargon investment committee.")
        _save_json_if_possible(state, f"critique_round{round_idx}.json", {"round": round_idx, "text": critique_text})
        if state.get("stream") and critique_text:
            first_line = (critique_text.split("\n")[0])[:200]
            logger.info("Round %d critique: %s", round_idx, first_line)

        if state.get("stream"):
            logger.info("Committee round %d: revise", round_idx)
        revise_prompt = f"""
You are the team lead. Revise the plan considering the committee's critiques below. Keep output JSON keys: decision, confidence, entry_timing, position_size, dca_plan, risk_controls, rationale. Keep explanations short and grounded.

Critiques:\n{critique_text}

Context:
- Company: {ticker.name} ({ticker.yf_symbol})
- Profile: risk={profile.risk_level}, horizon_years={profile.horizon_years}
- Technical: {technical.model_dump()}
- Fundamentals: {fundamentals.model_dump()}
- News: {news.summary[:1000]}
- Macro: {sector_macro.summary[:800]}
- Alternatives: {[c.model_dump() for c in alternatives.candidates]}
"""
        revised_json = llm.reason(
            _truncate(revise_prompt, 12000),
            system=(
                "Return ONLY valid JSON. Stay conservative, simple, long-term focused."
            ),
            response_format={"type": "json_object"},
        )
        try:
            revised_data = json.loads(revised_json)
            plan = DecisionPlan(
                decision=revised_data.get("decision", plan.decision),
                confidence=float(revised_data.get("confidence", plan.confidence)),
                entry_timing=revised_data.get("entry_timing", plan.entry_timing),
                position_size=revised_data.get("position_size", plan.position_size),
                dca_plan=revised_data.get("dca_plan", plan.dca_plan),
                risk_controls=revised_data.get("risk_controls", plan.risk_controls),
                rationale=revised_data.get("rationale", plan.rationale),
            )
        except Exception:
            # Keep previous plan on parse failure
            pass
        _save_json_if_possible(state, f"decision_round{round_idx}.json", plan.model_dump())
        if state.get("stream"):
            logger.info("Round %d revised -> %s (conf=%.2f)", round_idx, plan.decision, plan.confidence)

    # Save final decision
    _save_json_if_possible(state, "decision.json", plan.model_dump())
    logger.debug(
        "Stage decide: decision=%s confidence=%.2f (%.2f ms)",
        plan.decision,
        plan.confidence,
        (time.perf_counter() - start) * 1000,
    )
    return {"decision": plan}


def build_graph():
    g = StateGraph(GraphState)
    g.add_node("n_resolve", node_resolve)
    g.add_node("n_fundamentals", node_fundamentals)
    g.add_node("n_technical", node_technical)
    g.add_node("n_news", node_news)
    g.add_node("n_sector_macro", node_sector_macro)
    g.add_node("n_alternatives", node_alternatives)
    g.add_node("n_decide", node_decide)

    g.set_entry_point("n_resolve")
    # Fan-out
    g.add_edge("n_resolve", "n_fundamentals")
    g.add_edge("n_resolve", "n_technical")
    g.add_edge("n_resolve", "n_news")
    g.add_edge("n_resolve", "n_sector_macro")
    g.add_edge("n_resolve", "n_alternatives")

    # Fan-in
    g.add_edge("n_fundamentals", "n_decide")
    g.add_edge("n_technical", "n_decide")
    g.add_edge("n_news", "n_decide")
    g.add_edge("n_sector_macro", "n_decide")
    g.add_edge("n_alternatives", "n_decide")

    g.add_edge("n_decide", END)

    return g.compile()
