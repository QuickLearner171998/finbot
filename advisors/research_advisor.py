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


logger = logging.getLogger("finbot.advisors.research")


def conduct_research_debate(
    company_name: str,
    fundamentals: FundamentalsReport,
    technical: TechnicalReport,
    news: NewsReport,
    sector_macro: SectorMacroReport,
    sentiment_summary: Optional[str] = None,
) -> ResearchDebateReport:
    prompt = (
        "Two researchers debate. Output JSON with: bull_points (list), bear_points (list), consensus (short string).\n"
        f"Company: {company_name}\n"
        f"Fundamentals: {fundamentals.model_dump()}\n"
        f"Technical: {technical.model_dump()}\n"
        f"News summary: {news.summary[:1000]}\n"
        f"Macro: {sector_macro.summary[:800]}\n"
        f"Sentiment (optional): {sentiment_summary or ''}"
    )
    try:
        text = llm.reason(prompt, system="Return ONLY JSON with keys: bull_points, bear_points, consensus.", response_format={"type": "json_object"})
        import json
        data = json.loads(text)
        bull = [str(x) for x in (data.get("bull_points") or [])]
        bear = [str(x) for x in (data.get("bear_points") or [])]
        consensus = str(data.get("consensus") or "")
        return ResearchDebateReport(bull_points=bull, bear_points=bear, consensus=consensus)
    except Exception as e:
        logger.debug("Research debate JSON parse failed: %s", e)
        return ResearchDebateReport(bull_points=[], bear_points=[], consensus="Inconclusive; more data recommended.")


