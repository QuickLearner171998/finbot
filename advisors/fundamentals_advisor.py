import logging
from typing import Dict, List

from schemas import FundamentalsReport
from tools.fundamentals import get_basic_fundamentals
from llm import llm
from prompts import FUNDAMENTALS_PROMPT_TEMPLATE, FUNDAMENTALS_SYSTEM_MESSAGE

logger = logging.getLogger("finbot.advisors.fundamentals")


def analyze_fundamentals(symbol: str, company_name: str) -> FundamentalsReport:
    logger.debug("Fundamentals: fetching metrics for %s", symbol)
    raw: Dict[str, float] = get_basic_fundamentals(symbol)
    prompt = FUNDAMENTALS_PROMPT_TEMPLATE.format(
        company_name=company_name,
        symbol=symbol,
        metrics=raw
    )
    text = llm.summarize(prompt, system=FUNDAMENTALS_SYSTEM_MESSAGE, response_format={"type": "json_object"})
    logger.debug("Fundamentals: received summary length=%d", len(text or ""))
    # Parse the JSON response from LLM
    import json
    try:
        # Try to parse the JSON response
        result = json.loads(text)
        
        # Handle score with more graceful fallbacks
        if 'score' in result:
            try:
                score_val = result['score']
                if isinstance(score_val, str):
                    # Try to convert string to float
                    score_val = score_val.strip()
                    if score_val.endswith('%'):
                        score_val = score_val.rstrip('%')
                    score = float(score_val)
                else:
                    score = float(score_val)
            except (ValueError, TypeError):
                logger.warning("Could not parse score as float, using default")
                score = 50.0  # Default to neutral score
        else:
            logger.warning("LLM response missing 'score' field, using default")
            score = 50.0  # Default to neutral score
            
        # Ensure score is in valid range
        score = max(0.0, min(100.0, score))
        
        # Handle pros and cons with graceful fallbacks
        pros_val = result.get('pros')
        if isinstance(pros_val, list):
            pros = [str(item) for item in pros_val]
        elif pros_val is not None:
            # If it's a string, try to split it
            if isinstance(pros_val, str):
                pros = [pros_val]
            else:
                pros = [str(pros_val)]
        else:
            pros = []
            
        cons_val = result.get('cons')
        if isinstance(cons_val, list):
            cons = [str(item) for item in cons_val]
        elif cons_val is not None:
            # If it's a string, try to split it
            if isinstance(cons_val, str):
                cons = [cons_val]
            else:
                cons = [str(cons_val)]
        else:
            cons = []
            
    except json.JSONDecodeError as e:
        # Log the error but provide fallback values instead of raising
        logger.error(f"Failed to parse LLM response: {e}\nResponse was: {text[:200]}...")
        score = 50.0  # Default to neutral score
        pros = ["Data unavailable"]
        cons = ["Data unavailable"]
    report = FundamentalsReport(metrics=raw, pros=pros, cons=cons, score=score, notes=text)
    logger.debug("Fundamentals: metrics=%d pros=%d cons=%d score=%.1f", len(raw or {}), len(pros), len(cons), score)
    return report
