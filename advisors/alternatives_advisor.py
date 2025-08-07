from typing import List
from llm import llm
from schemas import AlternativesReport, AlternativeCandidate


def analyze_alternatives(company_name: str) -> AlternativesReport:
    prompt = (
        "Suggest 3-5 alternative Indian stocks that could be better for long-term investors than the given company. "
        "Prefer same sector and high-quality large/mid caps. Provide a one-line reason for each. Return as bullets.\n"
        f"Company: {company_name}"
    )
    text = llm.summarize(prompt, system="You are a conservative long-term stock picker in India.")
    candidates: List[AlternativeCandidate] = []
    for line in text.splitlines():
        if line.strip().startswith("-"):
            parts = line.strip("- ").split(":", 1)
            name = parts[0].strip()
            reason = parts[1].strip() if len(parts) > 1 else ""
            candidates.append(AlternativeCandidate(name=name, reason=reason))
    return AlternativesReport(candidates=candidates[:5])
