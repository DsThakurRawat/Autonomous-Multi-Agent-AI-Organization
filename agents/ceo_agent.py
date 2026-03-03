"""
CEO Agent — Chief Executive Officer
Converts a business idea into a structured business plan with
vision, MVP scope, milestones, risk assessment, and success metrics.
"""

import json
from typing import Any, Dict
import structlog
from .base_agent import BaseAgent

logger = structlog.get_logger(__name__)


class CEOAgent(BaseAgent):
    """
    The CEO agent is the first agent in the pipeline.
    It receives a raw business idea and produces a structured business plan
    that all other agents will use as their north star.
    """

    ROLE = "CEO"

    @property
    def system_prompt(self) -> str:
        return """You are the CEO of an autonomous AI software company.
Your job is to analyze a business idea and produce a clear, actionable business plan.

You think in terms of:
- Market opportunity and user value
- MVP scope (minimum valuable product, not minimum viable)
- Priorities and trade-offs
- Risk identification and mitigation
- Success metrics

You are pragmatic and budget-conscious.
You always output valid JSON matching the required schema.
Never over-engineer. Ship fast, iterate.
"""

    async def run(
        self,
        business_idea: str = "",
        budget_usd: float = 200.0,
        context: Any = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Analyze business idea and produce a structured business plan.
        """
        logger.info("CEO Agent: Analyzing business idea", idea=business_idea[:80])

        if context:
            await context.emit_event(
                type(
                    "E",
                    (),
                    {
                        "to_dict": lambda s: {
                            "type": "agent_thinking",
                            "agent": "CEO",
                            "message": "Analyzing market opportunity and defining MVP scope...",
                            "level": "info",
                        }
                    },
                )()
            )

        prompt = f"""
Analyze this business idea and produce a comprehensive business plan.

Business Idea: {business_idea}
Budget Constraint: ${budget_usd} USD/month

Return a JSON object with EXACTLY this structure:
{{
  "vision": "One sentence describing the product",
  "target_users": "Who benefits from this",
  "problem_statement": "What pain does it solve",
  "mvp_features": [
    {{"name": "Feature", "priority": "P0/P1/P2", "description": "..."}}
  ],
  "milestones": [
    {{"phase": "Phase name", "duration_days": 1, "deliverables": ["..."]}}
  ],
  "risk_assessment": [
    {{"risk": "Risk name", "impact": "High/Medium/Low", "mitigation": "..."}}
  ],
  "success_metrics": ["Metric 1", "Metric 2"],
  "revenue_model": "How it makes money",
  "estimated_users_year1": 1000,
  "go_to_market": "Strategy for user acquisition"
}}
"""
        raw_response = await self.call_llm(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            response_format="json_object",
        )

        try:
            plan = json.loads(raw_response)
        except json.JSONDecodeError:
            logger.warning("CEO: JSON parse failed, using structured extraction")
            plan = self._extract_plan_fallback(business_idea)

        # Self-critique to validate completeness
        plan = await self.self_critique(plan)

        if context:
            context.decision_log.log(
                agent_role=self.ROLE,
                decision_type="strategy",
                description="Business plan created",
                rationale=f"Analyzed: {business_idea[:60]}",
                input_context={"business_idea": business_idea, "budget": budget_usd},
                output=plan,
                confidence=0.9,
                tags=["strategy", "mvp"],
            )

        logger.info(
            "CEO: Business plan complete",
            features=len(plan.get("mvp_features", [])),
            milestones=len(plan.get("milestones", [])),
        )
        return plan

    def _extract_plan_fallback(self, idea: str) -> Dict[str, Any]:
        return {
            "vision": f"A platform to {idea}",
            "target_users": "Professionals and SMBs",
            "problem_statement": f"Currently there is no automated solution for {idea}",
            "mvp_features": [
                {
                    "name": "User Authentication",
                    "priority": "P0",
                    "description": "Secure login/register",
                },
                {
                    "name": "Core Dashboard",
                    "priority": "P0",
                    "description": "Main user interface",
                },
                {
                    "name": "Data Management",
                    "priority": "P1",
                    "description": "CRUD operations",
                },
                {
                    "name": "Notifications",
                    "priority": "P2",
                    "description": "Email/in-app alerts",
                },
            ],
            "milestones": [
                {
                    "phase": "Architecture",
                    "duration_days": 1,
                    "deliverables": ["System design", "DB schema"],
                },
                {
                    "phase": "Backend",
                    "duration_days": 2,
                    "deliverables": ["API", "Auth", "DB models"],
                },
                {
                    "phase": "Frontend",
                    "duration_days": 2,
                    "deliverables": ["UI", "API integration"],
                },
                {
                    "phase": "QA + Deploy",
                    "duration_days": 1,
                    "deliverables": ["Tests", "AWS deployment"],
                },
            ],
            "risk_assessment": [
                {
                    "risk": "Cost overrun",
                    "impact": "High",
                    "mitigation": "Monitor with Finance agent",
                },
                {
                    "risk": "Scope creep",
                    "impact": "Medium",
                    "mitigation": "Strict MVP boundaries",
                },
            ],
            "success_metrics": ["100+ MAU", "< 500ms response time", "99.9% uptime"],
            "revenue_model": "Freemium SaaS",
            "estimated_users_year1": 500,
            "go_to_market": "Product Hunt launch + LinkedIn outreach",
        }
