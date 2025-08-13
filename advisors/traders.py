import logging
from typing import List

from schemas import (
    TraderSignal,
    TraderEnsemble,
    FundamentalsReport,
    TechnicalReport,
    NewsReport,
    SectorMacroReport,
    ResearchDebateReport,
)
from llm import llm


logger = logging.getLogger("finbot.advisors.traders")


RISK_PROFILES = ["conservative", "moderate", "aggressive"]


def _trader_prompt(profile: str, company: str, fundamentals: FundamentalsReport, technical: TechnicalReport, news: NewsReport, macro: SectorMacroReport, research: ResearchDebateReport) -> str:
    return (
        f"Act as a {profile} trader. Output JSON with keys: action (Buy|Hold|Avoid), confidence (0-1), entry_timing, position_size, rationale.\n"
        f"Company: {company}\n"
        f"Fundamentals: {fundamentals.model_dump()}\n"
        f"Technical: {technical.model_dump()}\n"
        f"News: {news.summary[:800]}\n"
        f"Macro: {macro.summary[:600]}\n"
        f"Research: bull={research.bull_points} bear={research.bear_points} consensus={research.consensus}\n"
        "Return ONLY JSON."
    )


def generate_trader_signals(company: str, fundamentals: FundamentalsReport, technical: TechnicalReport, news: NewsReport, macro: SectorMacroReport, research: ResearchDebateReport) -> List[TraderSignal]:
    signals: List[TraderSignal] = []
    for profile in RISK_PROFILES:
        try:
            text = llm.reason(
                _trader_prompt(profile, company, fundamentals, technical, news, macro, research),
                system="Return ONLY JSON with keys: action, confidence, entry_timing, position_size, rationale.",
                response_format={"type": "json_object"},
            )
            import json
            data = json.loads(text)
            action = str(data.get("action") or "Hold")
            conf = float(data.get("confidence") or 0.0)
            entry = data.get("entry_timing")
            size = data.get("position_size")
            rationale = data.get("rationale")
            signals.append(TraderSignal(risk_profile=profile, action=action, confidence=conf, entry_timing=entry, position_size=size, rationale=rationale))
        except Exception as e:
            logger.debug("Trader %s parse failed: %s", profile, e)
            signals.append(TraderSignal(risk_profile=profile, action="Hold", confidence=0.0, rationale="fallback"))
    return signals


def aggregate_trader_signals(signals: List[TraderSignal]) -> TraderEnsemble:
    # Simple aggregation: majority vote weighted by confidence; tie -> Hold
    weights = {"Buy": 0.0, "Hold": 0.0, "Avoid": 0.0}
    for s in signals:
        if s.action in weights:
            weights[s.action] += max(0.0, min(1.0, s.confidence))
    consensus_action = max(weights.items(), key=lambda kv: kv[1])[0]
    total = sum(weights.values()) or 1.0
    consensus_confidence = weights[consensus_action] / total
    notes = f"weights={weights}"
    return TraderEnsemble(signals=signals, consensus_action=consensus_action, consensus_confidence=consensus_confidence, notes=notes)


