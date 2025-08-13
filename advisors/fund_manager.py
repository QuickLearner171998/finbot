import logging
from typing import Optional

from llm import llm
from schemas import FundManagerDecision, DecisionPlan, RiskAssessment
from prompts import FUND_MANAGER_PROMPT_TEMPLATE, FUND_MANAGER_SYSTEM_MESSAGE


logger = logging.getLogger("finbot.advisors.fund_manager")


def approve_plan(company_name: str, plan: DecisionPlan, risk: Optional[RiskAssessment] = None) -> FundManagerDecision:
    risk_assessment = risk.model_dump() if risk else {}
    prompt = FUND_MANAGER_PROMPT_TEMPLATE.format(
        company_name=company_name,
        plan=plan.model_dump(),
        risk_assessment=risk_assessment
    )
    try:
        text = llm.reason(prompt, system=FUND_MANAGER_SYSTEM_MESSAGE, response_format={"type": "json_object"})
        import json
        data = json.loads(text)
        approved = bool(data.get("approved", False))
        notes = str(data.get("notes") or "")
        adjustments = {str(k): str(v) for k, v in (data.get("adjustments") or {}).items()}
        return FundManagerDecision(approved=approved, notes=notes, adjustments=adjustments)
    except Exception as e:
        logger.debug("Fund manager decision parse failed: %s", e)
        return FundManagerDecision(approved=False, notes="Insufficient clarity; defer.", adjustments={})


