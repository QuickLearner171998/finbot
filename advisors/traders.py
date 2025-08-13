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
from prompts import TRADER_PROMPT_TEMPLATE, TRADER_SYSTEM_MESSAGE


logger = logging.getLogger("finbot.advisors.traders")


RISK_PROFILES = ["conservative", "moderate", "aggressive"]


def _trader_prompt(profile: str, company: str, fundamentals: FundamentalsReport, technical: TechnicalReport, news: NewsReport, macro: SectorMacroReport, research: ResearchDebateReport) -> str:
    return TRADER_PROMPT_TEMPLATE.format(
        profile=profile,
        company=company,
        fundamentals=fundamentals.model_dump(),
        technical=technical.model_dump(),
        news_summary=news.summary[:800],
        macro_summary=macro.summary[:600],
        bull_points=research.bull_points,
        bear_points=research.bear_points,
        consensus=research.consensus
    )


def generate_trader_signals(company: str, fundamentals: FundamentalsReport, technical: TechnicalReport, news: NewsReport, macro: SectorMacroReport, research: ResearchDebateReport) -> List[TraderSignal]:
    signals: List[TraderSignal] = []
    for profile in RISK_PROFILES:
        try:
            text = llm.reason(
                _trader_prompt(profile, company, fundamentals, technical, news, macro, research),
                system=TRADER_SYSTEM_MESSAGE,
                response_format={"type": "json_object"},
            )
            import json
            data = json.loads(text)
            action = str(data.get("action") or "Hold")
            
            # Handle confidence value more gracefully
            conf_val = data.get("confidence") or 0.0
            try:
                conf = float(conf_val)
            except (ValueError, TypeError):
                # If it's a string like "0.8" or something else, try to convert or default
                try:
                    conf = float(str(conf_val).replace('%', '').strip()) / 100 if '%' in str(conf_val) else float(str(conf_val))
                except (ValueError, TypeError):
                    conf = 0.5  # Default to medium confidence
            
            entry = str(data.get("entry_timing") or "")
            
            # Handle position_size more gracefully
            size_val = data.get("position_size")
            if isinstance(size_val, (int, float)):
                # Convert numeric values to string format
                size = f"{size_val}% of portfolio"
            else:
                size = str(size_val or "")
                
            rationale = str(data.get("rationale") or "")
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


