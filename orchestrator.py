from __future__ import annotations
import logging
import time
from typing import List
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


def node_resolve(state: dict) -> dict:
    start = time.perf_counter()
    name: str = state["company_name"]
    logger.debug("Stage resolve: input company='%s'", name)
    symbol = resolve_to_ticker(name) or name
    yf_symbol = symbol
    ticker = TickerInfo(name=name, exchange=None, symbol=symbol, yf_symbol=yf_symbol)
    state["ticker"] = ticker
    logger.debug("Stage resolve: resolved to symbol='%s' (yf='%s') in %.2f ms", symbol, yf_symbol, (time.perf_counter() - start) * 1000)
    return state


def node_fundamentals(state: dict) -> dict:
    start = time.perf_counter()
    ticker: TickerInfo = state["ticker"]
    logger.debug("Stage fundamentals: analyzing for %s", ticker.yf_symbol)
    report = analyze_fundamentals(ticker.yf_symbol, ticker.name)
    state["fundamentals"] = report
    logger.debug(
        "Stage fundamentals: metrics=%d score=%.1f (%.2f ms)",
        len(report.metrics or {}),
        report.score,
        (time.perf_counter() - start) * 1000,
    )
    return state


def node_technical(state: dict) -> dict:
    start = time.perf_counter()
    ticker: TickerInfo = state["ticker"]
    logger.debug("Stage technical: analyzing for %s", ticker.yf_symbol)
    report = analyze_technical(ticker.yf_symbol)
    state["technical"] = report
    logger.debug(
        "Stage technical: trend=%s keys=%s (%.2f ms)",
        report.trend,
        list((report.metrics or {}).keys()),
        (time.perf_counter() - start) * 1000,
    )
    return state


def node_news(state: dict) -> dict:
    start = time.perf_counter()
    ticker: TickerInfo = state["ticker"]
    logger.debug("Stage news: analyzing for %s", ticker.name)
    report = analyze_news(ticker.name)
    state["news"] = report
    logger.debug(
        "Stage news: items=%d summary_len=%d (%.2f ms)",
        len(report.items or []),
        len(report.summary or ""),
        (time.perf_counter() - start) * 1000,
    )
    return state


def node_sector_macro(state: dict) -> dict:
    start = time.perf_counter()
    ticker: TickerInfo = state["ticker"]
    logger.debug("Stage sector_macro: analyzing for %s", ticker.name)
    report = analyze_sector_macro(ticker.name)
    state["sector_macro"] = report
    logger.debug(
        "Stage sector_macro: summary_len=%d (%.2f ms)",
        len(report.summary or ""),
        (time.perf_counter() - start) * 1000,
    )
    return state


def node_alternatives(state: dict) -> dict:
    start = time.perf_counter()
    ticker: TickerInfo = state["ticker"]
    logger.debug("Stage alternatives: analyzing for %s", ticker.name)
    report = analyze_alternatives(ticker.name)
    state["alternatives"] = report
    logger.debug(
        "Stage alternatives: candidates=%d (%.2f ms)",
        len(report.candidates or []),
        (time.perf_counter() - start) * 1000,
    )
    return state


def node_decide(state: dict) -> dict:
    start = time.perf_counter()
    ticker: TickerInfo = state["ticker"]
    profile: InputProfile = state["profile"]
    fundamentals: FundamentalsReport = state["fundamentals"]
    technical: TechnicalReport = state["technical"]
    news: NewsReport = state["news"]
    sector_macro: SectorMacroReport = state["sector_macro"]
    alternatives: AlternativesReport = state["alternatives"]

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
    json_text = llm.reason(
        prompt,
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

    state["decision"] = plan
    logger.debug(
        "Stage decide: decision=%s confidence=%.2f (%.2f ms)",
        plan.decision,
        plan.confidence,
        (time.perf_counter() - start) * 1000,
    )
    return state


def build_graph():
    g = StateGraph(dict)
    g.add_node("resolve", node_resolve)
    g.add_node("fundamentals", node_fundamentals)
    g.add_node("technical", node_technical)
    g.add_node("news", node_news)
    g.add_node("sector_macro", node_sector_macro)
    g.add_node("alternatives", node_alternatives)
    g.add_node("decide", node_decide)

    g.set_entry_point("resolve")
    # Fan-out
    g.add_edge("resolve", "fundamentals")
    g.add_edge("resolve", "technical")
    g.add_edge("resolve", "news")
    g.add_edge("resolve", "sector_macro")
    g.add_edge("resolve", "alternatives")

    # Fan-in
    g.add_edge("fundamentals", "decide")
    g.add_edge("technical", "decide")
    g.add_edge("news", "decide")
    g.add_edge("sector_macro", "decide")
    g.add_edge("alternatives", "decide")

    g.add_edge("decide", END)

    return g.compile()
