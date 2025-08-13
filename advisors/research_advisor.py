import logging
from typing import Optional

from llm import llm
from schemas import (
    ResearchDebateReport,
    FundamentalsReport,
    TechnicalReport,
    NewsReport,
    SectorMacroReport,
)
from prompts import RESEARCH_PROMPT_TEMPLATE, RESEARCH_SYSTEM_MESSAGE


logger = logging.getLogger("finbot.advisors.research")


def conduct_research_debate(
    company_name: str,
    fundamentals: FundamentalsReport,
    technical: TechnicalReport,
    news: NewsReport,
    sector_macro: SectorMacroReport,
    sentiment_summary: Optional[str] = None,
) -> ResearchDebateReport:
    prompt = RESEARCH_PROMPT_TEMPLATE.format(
        company_name=company_name,
        fundamentals=fundamentals.model_dump(),
        technical=technical.model_dump(),
        news_summary=news.summary[:1000],
        macro_summary=sector_macro.summary[:800],
        sentiment_summary=sentiment_summary or ''
    )
    try:
        text = llm.reason(prompt, system=RESEARCH_SYSTEM_MESSAGE, response_format={"type": "json_object"})
        import json
        data = json.loads(text)
        bull = [str(x) for x in (data.get("bull_points") or [])]
        bear = [str(x) for x in (data.get("bear_points") or [])]
        consensus = str(data.get("consensus") or "")
        return ResearchDebateReport(bull_points=bull, bear_points=bear, consensus=consensus)
    except Exception as e:
        logger.debug("Research debate JSON parse failed: %s", e)
        return ResearchDebateReport(bull_points=[], bear_points=[], consensus="Inconclusive; more data recommended.")


