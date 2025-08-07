from __future__ import annotations
import logging
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
    name: str = state["company_name"]
    symbol = resolve_to_ticker(name) or name
    yf_symbol = symbol
    ticker = TickerInfo(name=name, exchange=None, symbol=symbol, yf_symbol=yf_symbol)
    state["ticker"] = ticker
    return state


def node_fundamentals(state: dict) -> dict:
    ticker: TickerInfo = state["ticker"]
    state["fundamentals"] = analyze_fundamentals(ticker.yf_symbol, ticker.name)
    return state


def node_technical(state: dict) -> dict:
    ticker: TickerInfo = state["ticker"]
    state["technical"] = analyze_technical(ticker.yf_symbol)
    return state


def node_news(state: dict) -> dict:
    ticker: TickerInfo = state["ticker"]
    state["news"] = analyze_news(ticker.name)
    return state


def node_sector_macro(state: dict) -> dict:
    ticker: TickerInfo = state["ticker"]
    state["sector_macro"] = analyze_sector_macro(ticker.name)
    return state


def node_alternatives(state: dict) -> dict:
    ticker: TickerInfo = state["ticker"]
    state["alternatives"] = analyze_alternatives(ticker.name)
    return state


def node_decide(state: dict) -> dict:
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
