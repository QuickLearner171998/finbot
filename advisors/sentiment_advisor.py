import logging
from typing import Optional

from llm import llm
from schemas import SentimentReport, NewsReport
from prompts import SENTIMENT_PROMPT_TEMPLATE, SENTIMENT_SYSTEM_MESSAGE


logger = logging.getLogger("finbot.advisors.sentiment")


def analyze_sentiment(company_name: str, news: Optional[NewsReport] = None, symbol: Optional[str] = None) -> SentimentReport:
    summary = (news.summary if news else "") or ""
    symbol_text = f'({symbol})' if symbol else ''
    prompt = SENTIMENT_PROMPT_TEMPLATE.format(
        company_name=company_name,
        symbol_text=symbol_text,
        news_summary=summary[:1200]
    )
    try:
        text = llm.reason(prompt, system=SENTIMENT_SYSTEM_MESSAGE, response_format={"type": "json_object"})
        import json
        data = json.loads(text)
        
        # Handle score with graceful fallbacks
        try:
            score_val = data.get("score", 0.0)
            if isinstance(score_val, str):
                # Try to convert string to float
                score = float(score_val)
            else:
                score = float(score_val)
        except (ValueError, TypeError):
            logger.warning("Could not parse sentiment score as float, using default")
            score = 0.0  # Default to neutral
            
        # Ensure score is in valid range
        score = max(-1.0, min(1.0, score))
        
        # Handle drivers with graceful fallbacks
        drivers_val = data.get("drivers")
        if isinstance(drivers_val, list):
            drivers = [str(x) for x in drivers_val]
        elif drivers_val is not None:
            # If it's a string, use it as a single driver
            if isinstance(drivers_val, str):
                drivers = [drivers_val]
            else:
                drivers = [str(drivers_val)]
        else:
            drivers = ["No clear sentiment drivers"]
            
        # Handle summary with graceful fallbacks
        summary_val = data.get("summary")
        if summary_val is not None:
            summary_out = str(summary_val)
        else:
            summary_out = "Sentiment analysis based on limited information."
        return SentimentReport(score=score, drivers=drivers, summary=summary_out)
    except Exception as e:
        logger.debug("Sentiment JSON parse failed, falling back: %s", e)
        # Fallback heuristic
        return SentimentReport(score=0.0, drivers=["insufficient data"], summary="Limited signals; defaulting to neutral sentiment.")


