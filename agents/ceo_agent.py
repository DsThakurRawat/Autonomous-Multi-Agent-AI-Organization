"""
CEO Agent - Chief Executive Officer
Converts a business idea into a structured business plan using
multi-turn chain-of-thought reasoning and Pydantic-validated output.
"""

import json
import os
from typing import Any

import structlog
import yaml

from .base_agent import BaseAgent
from .reasoning import ReasoningChain, ReasoningStep
from .schemas import BusinessPlan

logger = structlog.get_logger(__name__)

# Load prompt template once at module level
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def _load_prompt() -> dict:
    path = os.path.join(_PROMPT_DIR, "ceo_strategy.yaml")
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning("CEO prompt template not found, using inline prompts")
        return {}


_PROMPT_TEMPLATE = _load_prompt()


class CEOAgent(BaseAgent):
    """
    The CEO agent is the first agent in the pipeline.
    It receives a raw business idea and produces a structured business plan
    that all other agents will use as their north star.

    v2: Uses multi-turn ReasoningChain for deeper analysis and
    Pydantic BusinessPlan schema for validated output.
    """

    ROLE = "CEO"

    @property
    def system_prompt(self) -> str:
        return _PROMPT_TEMPLATE.get("system", "") or (
            "You are the CEO of an autonomous AI software company.\n"
            "Your job is to analyze a business idea and produce a clear, actionable business plan.\n\n"
            "You think in terms of:\n"
            "- Market opportunity and user value\n"
            "- MVP scope (minimum valuable product, not minimum viable)\n"
            "- Priorities and trade-offs\n"
            "- Risk identification and mitigation\n"
            "- Success metrics\n\n"
            "You are pragmatic and budget-conscious.\n"
            "You always output valid JSON matching the required schema.\n"
            "Never over-engineer. Ship fast, iterate.\n"
        )

    async def run(
        self,
        business_idea: str = "",
        budget_usd: float = 200.0,
        context: Any | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Analyze business idea and produce a structured business plan.

        Uses a 4-step reasoning chain:
          1. Analyze — Decompose the idea into market/scope/risk signals
          2. Generate — Produce the full business plan
          3. Critique — Self-evaluate for weaknesses
          4. Refine — Address weaknesses in a revised plan
        """
        logger.info("CEO Agent: Analyzing business idea", idea=business_idea[:80])

        if context:
            await self.emit(
                context,
                "Analyzing market opportunity and defining MVP scope...",
            )

        # Build the reasoning chain from YAML template or inline fallback
        cot = _PROMPT_TEMPLATE.get("chain_of_thought", {})
        chain = ReasoningChain(
            steps=[
                ReasoningStep(
                    name="analyze",
                    prompt_template=cot.get("analyze", self._fallback_analyze_prompt()),
                    temperature=0.3,
                ),
                ReasoningStep(
                    name="generate",
                    prompt_template=cot.get("generate", self._fallback_generate_prompt()),
                    temperature=0.4,
                ),
                ReasoningStep(
                    name="critique",
                    prompt_template=cot.get("critique", self._fallback_critique_prompt()),
                    temperature=0.1,
                ),
                ReasoningStep(
                    name="refine",
                    prompt_template=cot.get("refine", self._fallback_refine_prompt()),
                    temperature=0.3,
                ),
            ],
            output_schema=BusinessPlan,
            max_validation_retries=2,
        )

        # Progress callback for real-time TUI updates
        async def on_step(step_name: str, preview: str):
            step_labels = {
                "analyze": "Analyzing market & constraints...",
                "generate": "Drafting business plan...",
                "critique": "Self-evaluating plan quality...",
                "refine": "Refining based on critique...",
            }
            if context:
                await self.emit(
                    context,
                    step_labels.get(step_name, f"Step: {step_name}"),
                )

        try:
            plan = await chain.execute(
                call_llm=self.call_llm,
                on_step=on_step,
                business_idea=business_idea,
                budget_usd=budget_usd,
            )
        except Exception as e:
            logger.warning(
                "CEO reasoning chain failed, using fallback",
                error=str(e),
            )
            plan = self._extract_plan_fallback(business_idea)

        if context:
            await self.emit(
                context,
                f"MVP Strategy Drafted:\nVision: {plan.get('vision')}\n"
                f"Target: {plan.get('target_users')}\n"
                f"Features: {len(plan.get('mvp_features', []))} core tasks.",
                level="success",
            )

        # Log decision for audit trail
        if context:
            context.decision_log.log(
                agent_role=self.ROLE,
                decision_type="strategy",
                description="Business plan created via multi-turn reasoning chain",
                rationale=f"Analyzed: {business_idea[:60]}",
                input_context={"business_idea": business_idea, "budget": budget_usd},
                output=plan,
                confidence=0.9,
                tags=["strategy", "mvp", "reasoning_chain"],
            )

        if not isinstance(plan, dict):
            logger.warning(
                "CEO: LLM response was not a dict, using fallback", type=type(plan)
            )
            plan = self._extract_plan_fallback(business_idea)

        # Normalize features (handle LLMs that return strings instead of dicts)
        if "mvp_features" in plan and isinstance(plan["mvp_features"], list):
            valid_features = []
            for f in plan["mvp_features"]:
                if isinstance(f, str):
                    valid_features.append(
                        {"name": f, "priority": "P1", "description": f}
                    )
                elif isinstance(f, dict):
                    valid_features.append(f)
            plan["mvp_features"] = valid_features

        logger.info(
            "CEO: Business plan complete",
            features=len(plan.get("mvp_features", [])),
            milestones=len(plan.get("milestones", [])),
        )
        return plan

    # ── Fallback prompts (used when YAML template is missing) ────────

    @staticmethod
    def _fallback_analyze_prompt() -> str:
        return (
            "Analyze this business idea step by step:\n\n"
            "Business Idea: {business_idea}\n"
            "Budget Constraint: ${budget_usd} USD/month\n\n"
            "Think through:\n"
            "1. Who is the target user?\n"
            "2. What existing solutions exist?\n"
            "3. What is the minimum feature set to prove value?\n"
            "4. Top 3 risks?\n\n"
            'Return JSON with keys: target_analysis, competitive_landscape, '
            'minimum_viable_scope, critical_risks'
        )

    @staticmethod
    def _fallback_generate_prompt() -> str:
        return (
            "Based on your analysis:\n{analyze_output}\n\n"
            "Produce the full business plan as JSON with keys: "
            "vision, target_users, problem_statement, mvp_features, "
            "milestones, risk_assessment, success_metrics, revenue_model, "
            "estimated_users_year1, go_to_market"
        )

    @staticmethod
    def _fallback_critique_prompt() -> str:
        return (
            "Review this business plan for weaknesses:\n{generate_output}\n\n"
            "Score: market_viability, scope_realism, revenue_clarity (1-10 each).\n"
            'Return JSON: {{"scores": {{}}, "weaknesses": [], "improvements": []}}'
        )

    @staticmethod
    def _fallback_refine_prompt() -> str:
        return (
            "Your plan had these weaknesses:\n{critique_output}\n\n"
            "Original plan:\n{generate_output}\n\n"
            "Produce a REVISED plan fixing every weakness. Return valid JSON only."
        )

    # ── Safe fallback plan ──────────────────────────────────────────

    def _extract_plan_fallback(self, idea: str) -> dict[str, Any]:
        return {
            "vision": f"A platform to {idea}",
            "target_users": "Professionals and SMBs",
            "problem_statement": f"Currently there is no automated solution for {idea}",
            "mvp_features": [
                {
                    "name": "User Authentication",
                    "priority": "P0",
                    "description": "Secure login/register with JWT tokens",
                },
                {
                    "name": "Core Dashboard",
                    "priority": "P0",
                    "description": "Main user interface with key metrics",
                },
                {
                    "name": "Data Management",
                    "priority": "P1",
                    "description": "CRUD operations for core entities",
                },
                {
                    "name": "Notifications",
                    "priority": "P2",
                    "description": "Email/in-app alerts for key events",
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
