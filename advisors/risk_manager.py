import logging
from typing import Optional

from llm import llm
from schemas import RiskAssessment, DecisionPlan, TechnicalReport, NewsReport


logger = logging.getLogger("finbot.advisors.risk")


def assess_risk(company_name: str, plan: DecisionPlan, technical: TechnicalReport, news: Optional[NewsReport] = None) -> RiskAssessment:
    prompt = (
        "You are a risk manager. Review the plan and identify risks and constraints. "
        "Output JSON with keys: overall_risk (low|medium|high), issues (list), constraints (object of policy->note), veto (bool).\n"
        f"Company: {company_name}\n"
        f"Plan: {plan.model_dump()}\n"
        f"Technical: {technical.model_dump()}\n"
        f"News: {(news.summary if news else '')[:800]}"
    )
    try:
        text = llm.reason(prompt, system="Return ONLY JSON with keys: overall_risk, issues, constraints, veto.", response_format={"type": "json_object"})
        import json
        data = json.loads(text)
        overall = str(data.get("overall_risk") or "medium")
        issues = [str(x) for x in (data.get("issues") or [])]
        constraints = {str(k): str(v) for k, v in (data.get("constraints") or {}).items()}
        veto = bool(data.get("veto", False))
        return RiskAssessment(overall_risk=overall, issues=issues, constraints=constraints, veto=veto)
    except Exception as e:
        logger.debug("Risk JSON parse failed: %s", e)
        return RiskAssessment(overall_risk="medium", issues=["insufficient data"], constraints={}, veto=False)


