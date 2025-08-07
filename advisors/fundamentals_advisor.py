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
        "Return a short bullet list of pros, cons, and a score."
    )
    text = llm.summarize(prompt, system="You are an equity analyst for India markets.")
    logger.debug("Fundamentals: received summary length=%d", len(text or ""))
    # Lightweight parse: look for score; if not found, default 60
    score = 60.0
    pros: List[str] = []
    cons: List[str] = []
    for line in text.splitlines():
        low = line.lower()
        if "score" in low:
            try:
                nums = [float(x) for x in line.replace("%", "").split() if x.replace('.', '', 1).isdigit()]
                if nums:
                    score = max(0.0, min(100.0, nums[0]))
            except Exception:
                pass
        elif line.strip().startswith("-"):
            if any(k in low for k in ["risk", "concern", "watch", "negative"]):
                cons.append(line.strip("- "))
            else:
                pros.append(line.strip("- "))
    report = FundamentalsReport(metrics=raw, pros=pros, cons=cons, score=score, notes=text)
    logger.debug("Fundamentals: metrics=%d pros=%d cons=%d score=%.1f", len(raw or {}), len(pros), len(cons), score)
    return report
