import logging
from typing import Optional

from llm import llm
from schemas import SentimentReport, NewsReport


logger = logging.getLogger("finbot.advisors.sentiment")


def analyze_sentiment(company_name: str, news: Optional[NewsReport] = None, symbol: Optional[str] = None) -> SentimentReport:
    summary = (news.summary if news else "") or ""
    prompt = (
        "You are a markets sentiment analyst. Given the context, output a JSON with fields: "
        "score (float in [-1,1]), drivers (list of short phrases), summary (brief).\n"
        f"Company: {company_name} {f'({symbol})' if symbol else ''}\n"
        f"News summary: {summary[:1200]}\n"
        "If information is sparse, keep score near 0 and be conservative."
    )
    try:
        text = llm.reason(prompt, system="Return ONLY JSON with keys: score, drivers, summary.", response_format={"type": "json_object"})
        import json
        data = json.loads(text)
        score = float(data.get("score", 0.0))
        score = max(-1.0, min(1.0, score))
        drivers = [str(x) for x in (data.get("drivers") or [])]
        summary_out = str(data.get("summary") or "")
        return SentimentReport(score=score, drivers=drivers, summary=summary_out)
    except Exception as e:
        logger.debug("Sentiment JSON parse failed, falling back: %s", e)
        # Fallback heuristic
        return SentimentReport(score=0.0, drivers=["insufficient data"], summary="Limited signals; defaulting to neutral sentiment.")


