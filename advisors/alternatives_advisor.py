import logging
from typing import List
from llm import llm
from schemas import AlternativeCandidate


def analyze_alternatives(company_name: str) -> List[AlternativeCandidate]:
    logger = logging.getLogger("finbot.advisors.alternatives")
    logger.debug("Alternatives: generating for %s", company_name)
    prompt = (
        "Suggest 3-5 alternative Indian stocks that could be better for long-term investors than the given company. "
        "Prefer same sector and high-quality large/mid caps. Provide a one-line reason for each. "
        "Return as JSON array with objects containing 'name' and 'reason' fields.\n"
        f"Company: {company_name}"
    )
    text = llm.summarize(
        prompt, 
        system="You are a conservative long-term stock picker in India. Return ONLY JSON array with objects containing 'name' and 'reason' fields.", 
        response_format={"type": "json_object"}
    )
    
    import json
    try:
        data = json.loads(text)
        candidates = []
        if isinstance(data, list):
            for item in data:
                name = item.get('name', '').strip()
                reason = item.get('reason', '').strip()
                if name:
                    candidates.append(AlternativeCandidate(name=name, reason=reason))
        else:
            # Handle case where response might be an object with an array field
            alternatives = data.get('alternatives', [])
            if alternatives and isinstance(alternatives, list):
                for item in alternatives:
                    name = item.get('name', '').strip()
                    reason = item.get('reason', '').strip()
                    if name:
                        candidates.append(AlternativeCandidate(name=name, reason=reason))
    except Exception as e:
        logger.error(f"Failed to parse alternatives JSON: {e}")
        candidates = []
        
    logger.debug("Alternatives: candidates=%d", len(candidates))
    return candidates[:5]
