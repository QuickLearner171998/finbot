import logging
from typing import Optional

from llm import llm
from schemas import RiskAssessment, DecisionPlan, TechnicalReport, NewsReport
from prompts import RISK_PROMPT_TEMPLATE, RISK_SYSTEM_MESSAGE


logger = logging.getLogger("finbot.advisors.risk")


def assess_risk(company_name: str, plan: DecisionPlan, technical: TechnicalReport, news: Optional[NewsReport] = None) -> RiskAssessment:
    news_summary = (news.summary if news else '')[:800]
    prompt = RISK_PROMPT_TEMPLATE.format(
        company_name=company_name,
        plan=plan.model_dump(),
        technical=technical.model_dump(),
        news_summary=news_summary
    )
    try:
        text = llm.reason(prompt, system=RISK_SYSTEM_MESSAGE, response_format={"type": "json_object"})
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


