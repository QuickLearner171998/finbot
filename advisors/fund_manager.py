import logging
from typing import Optional

from llm import llm
from schemas import FundManagerDecision, DecisionPlan, RiskAssessment


logger = logging.getLogger("finbot.advisors.fund_manager")


def approve_plan(company_name: str, plan: DecisionPlan, risk: Optional[RiskAssessment] = None) -> FundManagerDecision:
    prompt = (
        "You are the fund manager. Decide to approve or reject the plan. "
        "If rejecting, suggest adjustments. Output JSON with: approved (bool), notes (string), adjustments (object).\n"
        f"Company: {company_name}\n"
        f"Plan: {plan.model_dump()}\n"
        f"Risk assessment: {(risk.model_dump() if risk else {})}"
    )
    try:
        text = llm.reason(prompt, system="Return ONLY JSON with keys: approved, notes, adjustments.", response_format={"type": "json_object"})
        import json
        data = json.loads(text)
        approved = bool(data.get("approved", False))
        notes = str(data.get("notes") or "")
        adjustments = {str(k): str(v) for k, v in (data.get("adjustments") or {}).items()}
        return FundManagerDecision(approved=approved, notes=notes, adjustments=adjustments)
    except Exception as e:
        logger.debug("Fund manager decision parse failed: %s", e)
        return FundManagerDecision(approved=False, notes="Insufficient clarity; defer.", adjustments={})


