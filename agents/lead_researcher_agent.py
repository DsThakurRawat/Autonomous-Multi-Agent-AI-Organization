"""
Lead Researcher Agent - Strategy & Synthesis
Converts a research goal into a structured deconstruction plan using
multi-turn chain-of-thought reasoning.
"""

import json
import os
from typing import Any

import structlog
import yaml

from .base_agent import BaseAgent
from .reasoning import ReasoningChain, ReasoningStep
from .schemas import DeconstructionPlan

logger = structlog.get_logger(__name__)

# Load prompt template once at module level
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def _load_prompt() -> dict:
    path = os.path.join(_PROMPT_DIR, "lead_researcher.yaml")
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning("Lead Researcher prompt template not found, using inline prompts")
        return {}


_PROMPT_TEMPLATE = _load_prompt()


class LeadResearcherAgent(BaseAgent):
    """
    The Lead Researcher agent is the first agent in the research pipeline.
    It receives a research goal and produces a structured deconstruction plan.
    """

    ROLE = "Lead_Researcher"

    @property
    def system_prompt(self) -> str:
        return _PROMPT_TEMPLATE.get("system", "") or (
            "You are the Lead Researcher and Principal Investigator of SARANG, an autonomous scientific research lab.\n"
            "Your mission is to serve two primary audiences:\n"
            "1. PROFESSIONAL RESEARCHERS: Provide high-fidelity, mathematically rigorous deconstructions of complex goals.\n"
            "2. STUDENTS: Act as a patient mentor, breaking down complex concepts into first principles and explaining the 'why' behind scientific breakthroughs.\n\n"
            "You think in terms of:\n"
            "- Scientific significance and novelty (for researchers)\n"
            "- Conceptual clarity and pedagogical progression (for students)\n"
            "- Mathematical foundations and hypotheses\n"
            "- Implementation feasibility and reproducibility\n"
            "- Potential bottlenecks in validation\n\n"
            "When responding conversationally, be warm, professional, and intellectually stimulating. "
            "You always aim for clarity without compromising on rigor.\n"
        )

    async def run(
        self,
        research_goal: str = "",
        budget_usd: float = 200.0,
        context: Any | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Analyze research goal and produce a structured deconstruction plan.
        """
        logger.info("Lead Researcher: Analyzing research goal", goal=research_goal[:80])

        if context:
            await self.emit(
                context,
                "Analyzing scientific significance and defining deconstruction scope...",
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
            output_schema=DeconstructionPlan,
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
                research_goal=research_goal,
                budget_usd=budget_usd,
            )
        except Exception as e:
            logger.warning(
                "Lead Researcher reasoning chain failed, using fallback",
                error=str(e),
            )
            plan = self._extract_plan_fallback(research_goal)

        if context:
            await self.emit(
                context,
                f"Research Mission Deconstructed:\n{plan.get('summary')}\n"
                f"Hypotheses: {len(plan.get('hypotheses', []))} identified.\n"
                f"Complexity: {plan.get('estimated_complexity')}",
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
            "Analyze this research goal step by step:\n\n"
            "Research Goal: {research_goal}\n"
            "Constraints: High scientific rigor, reproducibility priority.\n\n"
            "Think through:\n"
            "1. What is the core scientific question?\n"
            "2. What mathematical foundations are required?\n"
            "3. What are the top 3 implementation challenges?\n"
            "4. How can we validate the novelty?\n\n"
            'Return JSON with keys: scientific_question, math_foundations, '
            'implementation_challenges, novelty_indicators'
        )

    @staticmethod
    def _fallback_generate_prompt() -> str:
        return (
            "Based on your analysis:\n{analyze_output}\n\n"
            "Produce a comprehensive Research Deconstruction Plan.\n"
            "IMPORTANT: The 'summary' field should be a conversational, Claude-style explanation (100-200 words) "
            "of how we will tackle this research mission.\n\n"
            "Return JSON with keys: "
            "summary, hypotheses (list of {statement, confidence, validation_method}), "
            "math_requirements (list of {concept, formalism, critical_equations}), "
            "implementation_goals (list of {module, language, requirements}), "
            "estimated_complexity (Low/Medium/High/Critical), novelty_score (0-10), "
            "reproducibility_risks (list)"
        )

    @staticmethod
    def _fallback_critique_prompt() -> str:
        return (
            "Review this research plan for scientific rigor:\n{generate_output}\n\n"
            "Score: math_rigor, implementation_feasibility, novelty_confidence (1-10 each).\n"
            'Return JSON: {{"scores": {{}}, "weaknesses": [], "improvements": []}}'
        )

    @staticmethod
    def _fallback_refine_prompt() -> str:
        return (
            "Your plan had these weaknesses:\n{critique_output}\n\n"
            "Original plan:\n{generate_output}\n\n"
            "Produce a REVISED scientific plan fixing every weakness. Return valid JSON only."
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
