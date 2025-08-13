import logging
from llm import llm
from schemas import SectorMacroReport
from prompts import SECTOR_MACRO_PROMPT_TEMPLATE, SECTOR_MACRO_SYSTEM_MESSAGE


def analyze_sector_macro(company_name: str) -> SectorMacroReport:
    logger = logging.getLogger("finbot.advisors.sector_macro")
    logger.debug("Sector/Macro: summarizing for %s", company_name)
    prompt = SECTOR_MACRO_PROMPT_TEMPLATE.format(
        company_name=company_name
    )
    summary = llm.summarize(prompt, system=SECTOR_MACRO_SYSTEM_MESSAGE)
    report = SectorMacroReport(summary=summary)
    logger.debug("Sector/Macro: summary_len=%d", len(summary or ""))
    return report
