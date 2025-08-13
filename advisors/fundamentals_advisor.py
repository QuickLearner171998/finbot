import logging
from typing import Dict, List

from schemas import FundamentalsReport
from tools.fundamentals import get_basic_fundamentals
from llm import llm

logger = logging.getLogger("finbot.advisors.fundamentals")


def analyze_fundamentals(symbol: str, company_name: str) -> FundamentalsReport:
    logger.debug("Fundamentals: fetching metrics for %s", symbol)
    raw: Dict[str, float] = get_basic_fundamentals(symbol)
    prompt = (
        "Given these basic metrics for an Indian stock, produce a long-term fundamentals snapshot: "
        "key positives, key concerns, and a 0-100 score (long-term quality/valuation).\n"
        f"Company: {company_name} ({symbol})\n"
        f"Metrics JSON: {raw}\n"
        "Return a JSON with three keys: 'score' (a number between 0-100), 'pros' (a list of strings), "
        "and 'cons' (a list of strings). The score should reflect your assessment of the company's long-term prospects."
    )
    text = llm.summarize(prompt, system="You are an equity analyst for India markets. Return ONLY JSON with keys: score, pros, cons.", response_format={"type": "json_object"})
    logger.debug("Fundamentals: received summary length=%d", len(text or ""))
    # Parse the JSON response from LLM
    import json
    try:
        # Try to parse the JSON response
        result = json.loads(text)
        if 'score' not in result:
            logger.error("LLM response missing 'score' field")
            raise ValueError("Missing score in LLM response")
        
        score = max(0.0, min(100.0, float(result['score'])))
        pros = result.get('pros', [])
        cons = result.get('cons', [])
    except (json.JSONDecodeError, ValueError) as e:
        # Log the error and raise it to notify that score couldn't be computed
        logger.error(f"Failed to parse LLM response: {e}\nResponse was: {text[:200]}...")
        raise ValueError(f"Could not compute fundamentals score: {e}")
    report = FundamentalsReport(metrics=raw, pros=pros, cons=cons, score=score, notes=text)
    logger.debug("Fundamentals: metrics=%d pros=%d cons=%d score=%.1f", len(raw or {}), len(pros), len(cons), score)
    return report
