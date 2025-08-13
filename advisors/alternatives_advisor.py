import logging
from typing import List
from llm import llm
from schemas import AlternativeCandidate
from prompts import ALTERNATIVES_PROMPT_TEMPLATE, ALTERNATIVES_SYSTEM_MESSAGE


def analyze_alternatives(company_name: str) -> List[AlternativeCandidate]:
    logger = logging.getLogger("finbot.advisors.alternatives")
    logger.debug("Alternatives: generating for %s", company_name)
    prompt = ALTERNATIVES_PROMPT_TEMPLATE.format(
        company_name=company_name
    )
    text = llm.summarize(
        prompt, 
        system=ALTERNATIVES_SYSTEM_MESSAGE, 
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
