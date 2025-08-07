import logging
from llm import llm
from schemas import SectorMacroReport


def analyze_sector_macro(company_name: str) -> SectorMacroReport:
    logger = logging.getLogger("finbot.advisors.sector_macro")
    logger.debug("Sector/Macro: summarizing for %s", company_name)
    prompt = (
        "In simple English, explain sector trends and macro context in India relevant to this company. "
        "Mention policy/regulation if pertinent. Keep it short and practical.\n"
        f"Company: {company_name}"
    )
    summary = llm.summarize(prompt, system="You are a macro analyst for Indian markets.")
    report = SectorMacroReport(summary=summary)
    logger.debug("Sector/Macro: summary_len=%d", len(summary or ""))
    return report
