from llm import llm
from schemas import SectorMacroReport


def analyze_sector_macro(company_name: str) -> SectorMacroReport:
    prompt = (
        "In simple English, explain sector trends and macro context in India relevant to this company. "
        "Mention policy/regulation if pertinent. Keep it short and practical.\n"
        f"Company: {company_name}"
    )
    summary = llm.summarize(prompt, system="You are a macro analyst for Indian markets.")
    return SectorMacroReport(summary=summary)
