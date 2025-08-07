from __future__ import annotations
import json
import logging
import os
import time
from typing import List
from typing_extensions import TypedDict
from pydantic import ValidationError
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


def _save_text_if_possible(state: dict, filename: str, text: str) -> None:
    run_dir = state.get("run_dir")
    if not run_dir:
        return
    try:
        os.makedirs(run_dir, exist_ok=True)
        path = os.path.join(run_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception as e:
        logger.debug("Save text failed for %s: %s", filename, e)


# JSON Schema that the LLM must follow for decision outputs
DECISION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["Buy", "Hold", "Avoid"]},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "entry_timing": {"type": "string"},
        "position_size": {"type": "string"},
        "dca_plan": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "risk_controls": {"type": "object", "additionalProperties": {"type": "string"}},
        "rationale": {"type": "string"}
    },
    "required": [
        "decision",
        "confidence",
        "entry_timing",
        "position_size",
        "dca_plan",
        "risk_controls",
        "rationale"
    ],
    "additionalProperties": False
}


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
 You MUST output JSON that STRICTLY matches the following JSON Schema: {json.dumps(DECISION_JSON_SCHEMA)}. If you cannot fill a field, set it to null and keep the key present. Ensure risk_controls values are strings (not numbers or lists). No extra properties.
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

    def _request_plan(sys_prompt: str, user_prompt: str) -> str:
        return llm.reason(
            _truncate(user_prompt, 12000),
            system=sys_prompt,
        response_format={"type": "json_object"},
        )

    sys_msg = (
        "Return ONLY valid JSON. Keep it conservative, avoid jargon, and respect the long-term focus and risk profile."
    )

    json_text = _request_plan(sys_msg, prompt)
    _save_text_if_possible(state, "decision_raw_try1.json", json_text)

    def _parse_plan(text: str) -> DecisionPlan:
        data = json.loads(text)
        # Best-effort coercion to keep pipeline flowing; leave None if truly missing
        decision = data.get("decision") if isinstance(data.get("decision"), str) else None
        try:
            confidence = float(data.get("confidence")) if data.get("confidence") is not None else None
        except Exception:
            confidence = None
        entry_timing = data.get("entry_timing") if isinstance(data.get("entry_timing"), str) else None

        pos = data.get("position_size")
        if isinstance(pos, str):
            position_size = pos
        elif isinstance(pos, (int, float)):
            position_size = f"~{float(pos):.0f}% of portfolio"
        elif isinstance(pos, dict):
            strategy = pos.get("strategy") or pos.get("style") or pos.get("risk")
            percentage = pos.get("percentage") or pos.get("percent") or pos.get("allocation")
            try:
                position_size = f"{str(strategy)} ~{float(percentage):.0f}% of portfolio" if (strategy is not None and percentage is not None) else None
            except Exception:
                position_size = None
        else:
            position_size = None

        dca_plan = data.get("dca_plan")
        if dca_plan is not None and not isinstance(dca_plan, str):
            dca_plan = str(dca_plan)

        rc = data.get("risk_controls")
        if isinstance(rc, dict):
            risk_controls = {str(k): (json.dumps(v) if isinstance(v, (dict, list)) else str(v)) for k, v in rc.items()}
        elif isinstance(rc, list):
            risk_controls = {}
            for idx, item in enumerate(rc, start=1):
                key = None
                val = item
                if isinstance(item, dict):
                    key = item.get("type") or item.get("name") or f"rule_{idx}"
                    val = item.get("desc") or item.get("description") or item.get("rule") or item
                risk_controls[str(key or f"rule_{idx}")] = json.dumps(val) if isinstance(val, (dict, list)) else str(val)
        elif isinstance(rc, str):
            risk_controls = {"note": rc}
        else:
            risk_controls = {}

        rationale = data.get("rationale") if isinstance(data.get("rationale"), str) else None

        return DecisionPlan(
            decision=decision,
            confidence=confidence,
            entry_timing=entry_timing,
            position_size=position_size,
            dca_plan=dca_plan,
            risk_controls=risk_controls,
            rationale=rationale,
        )

    plan: DecisionPlan
    try:
        plan = _parse_plan(json_text)
    except (ValidationError, json.JSONDecodeError) as e1:
        _save_text_if_possible(state, "decision_validation_error_try1.txt", str(e1))
        logger.info("Decision JSON invalid, requesting correction (attempt 2)")
        fix_prompt = (
            "The previous JSON did not match the schema. Here are the errors: "
            f"{str(e1)}.\n"
            "Please FIX the JSON to STRICTLY match this JSON Schema (no extra fields, correct types):\n"
            f"{json.dumps(DECISION_JSON_SCHEMA)}\n"
            "Return ONLY the corrected JSON."
        )
        json_text2 = _request_plan(sys_msg, fix_prompt)
        _save_text_if_possible(state, "decision_raw_try2.json", json_text2)
        try:
            plan = _parse_plan(json_text2)
        except (ValidationError, json.JSONDecodeError) as e2:
            _save_text_if_possible(state, "decision_validation_error_try2.txt", str(e2))
            logger.error("Decision JSON still invalid after correction. Aborting.")
            raise

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
        revised_json = _request_plan(sys_msg, revise_prompt)
        _save_text_if_possible(state, f"decision_round{round_idx}_raw.json", revised_json)
        try:
            plan = _parse_plan(revised_json)
        except (ValidationError, json.JSONDecodeError) as e:
            _save_text_if_possible(state, f"decision_round{round_idx}_validation_error.txt", str(e))
            # Try one correction per round
            fix_prompt2 = (
                f"Correction needed. Errors: {str(e)}. Fix JSON to STRICTLY match schema: {json.dumps(DECISION_JSON_SCHEMA)}"
            )
            revised_json2 = _request_plan(sys_msg, fix_prompt2)
            _save_text_if_possible(state, f"decision_round{round_idx}_raw_retry.json", revised_json2)
            plan = _parse_plan(revised_json2)
        _save_json_if_possible(state, f"decision_round{round_idx}.json", plan.model_dump())
        if state.get("stream"):
            logger.info("Round %d revised -> %s (conf=%.2f)", round_idx, plan.decision, plan.confidence)

    # Save final decision (allow None fields)
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


# ----------------------
# Post-processing helpers
# ----------------------
def _list_missing_fields(plan: DecisionPlan) -> list:
    missing = []
    if not plan.decision:
        missing.append("decision")
    if plan.confidence is None:
        missing.append("confidence")
    if not plan.entry_timing:
        missing.append("entry_timing")
    if not plan.position_size:
        missing.append("position_size")
    if plan.dca_plan is None:
        missing.append("dca_plan")
    if not plan.risk_controls:
        missing.append("risk_controls")
    if not plan.rationale:
        missing.append("rationale")
    return missing


def _coerce_partial_update(update: dict) -> dict:
    coerced = {}
    if "decision" in update and isinstance(update["decision"], str):
        coerced["decision"] = update["decision"]
    if "confidence" in update:
        try:
            coerced["confidence"] = float(update["confidence"]) if update["confidence"] is not None else None
        except Exception:
            pass
    if "entry_timing" in update and isinstance(update["entry_timing"], str):
        coerced["entry_timing"] = update["entry_timing"]
    if "position_size" in update:
        pos = update["position_size"]
        if isinstance(pos, str):
            coerced["position_size"] = pos
        elif isinstance(pos, (int, float)):
            coerced["position_size"] = f"~{float(pos):.0f}% of portfolio"
        elif isinstance(pos, dict):
            strategy = pos.get("strategy") or pos.get("style") or pos.get("risk")
            percentage = pos.get("percentage") or pos.get("percent") or pos.get("allocation")
            try:
                if strategy is not None and percentage is not None:
                    coerced["position_size"] = f"{str(strategy)} ~{float(percentage):.0f}% of portfolio"
            except Exception:
                pass
    if "dca_plan" in update:
        coerced["dca_plan"] = str(update["dca_plan"]) if update["dca_plan"] is not None else None
    if "risk_controls" in update:
        rc = update["risk_controls"]
        if isinstance(rc, dict):
            coerced["risk_controls"] = {str(k): (json.dumps(v) if isinstance(v, (dict, list)) else str(v)) for k, v in rc.items()}
        elif isinstance(rc, list):
            out = {}
            for idx, item in enumerate(rc, start=1):
                key = None
                val = item
                if isinstance(item, dict):
                    key = item.get("type") or item.get("name") or f"rule_{idx}"
                    val = item.get("desc") or item.get("description") or item.get("rule") or item
                out[str(key or f"rule_{idx}")] = json.dumps(val) if isinstance(val, (dict, list)) else str(val)
            coerced["risk_controls"] = out
        elif isinstance(rc, str):
            coerced["risk_controls"] = {"note": rc}
        elif rc is None:
            coerced["risk_controls"] = {}
    if "rationale" in update and isinstance(update["rationale"], str):
        coerced["rationale"] = update["rationale"]
    return coerced


def fill_missing_decision_fields(
    run_dir: str,
    plan: DecisionPlan,
    ticker: TickerInfo,
    profile: InputProfile,
    fundamentals: FundamentalsReport,
    technical: TechnicalReport,
    news: NewsReport,
    sector_macro: SectorMacroReport,
    alternatives: AlternativesReport,
    stream: bool = False,
) -> DecisionPlan:
    """If the final decision has missing fields, ask the LLM to fill only those fields.
    Saves a gaps report and any filled decision to the run directory.
    """
    state: dict = {"run_dir": run_dir}
    before_missing = _list_missing_fields(plan)
    _save_json_if_possible(state, "gaps_report.json", {"missing_before": before_missing})
    if not before_missing:
        return plan

    if stream:
        logger.info("Filling missing fields: %s", ", ".join(before_missing))

    fill_prompt = f"""
Fill ONLY the following missing fields in the decision JSON: {before_missing}.
Output JSON with exactly those keys. If you don't know, use null.
Constraints:
- position_size MUST be a single string (e.g., 'moderate ~5% of portfolio').
- risk_controls MUST be an object mapping strings to strings.
- confidence MUST be between 0 and 1.

Context:
- Company: {ticker.name} ({ticker.yf_symbol})
- Profile: risk={profile.risk_level}, horizon_years={profile.horizon_years}
- Technical: {technical.model_dump()}
- Fundamentals: {fundamentals.model_dump()}
- News: {news.summary[:1000]}
- Macro: {sector_macro.summary[:800]}
- Alternatives: {[c.model_dump() for c in alternatives.candidates]}

Current Decision JSON: {plan.model_dump()}
"""
    filled_json = llm.reason(
        fill_prompt,
        system="Return ONLY valid JSON with exactly the keys requested.",
        response_format={"type": "json_object"},
    )
    _save_text_if_possible(state, "decision_fill_raw.json", filled_json)
    try:
        update = json.loads(filled_json)
    except Exception:
        update = {}

    coerced_update = _coerce_partial_update(update)
    new_data = plan.model_dump()
    new_data.update(coerced_update)
    new_plan = DecisionPlan(**new_data)
    after_missing = _list_missing_fields(new_plan)
    _save_json_if_possible(state, "gaps_report.json", {"missing_before": before_missing, "missing_after": after_missing})
    _save_json_if_possible(state, "decision_filled.json", new_plan.model_dump())
    if stream:
        logger.info("Missing after fill: %s", ", ".join(after_missing) if after_missing else "none")
    return new_plan
