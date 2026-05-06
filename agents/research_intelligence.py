"""
Research Intelligence Core
Converts research goals into structured scientific deconstruction plans.
Expert in: Hypothesis generation, mathematical requirements, and implementation blueprinting.
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
    path = os.path.join(_PROMPT_DIR, "research_intelligence.yaml")
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning("Research Intelligence prompt template not found, using inline prompts")
        return {}

_PROMPT_TEMPLATE = _load_prompt()

class ResearchIntelligence(BaseAgent):
    """
    Research Intelligence is the central orchestrator of the SARANG swarm.
    It receives a goal and produces a rigorous scientific plan.
    """

    ROLE = "Research_Intelligence"

    @property
    def system_prompt(self) -> str:
        return _PROMPT_TEMPLATE.get("system", "") or (
            "You are the Research Intelligence Core of SARANG, an autonomous AI laboratory.\n"
            "You provide mathematically rigorous deconstructions of complex goals.\n\n"
            "You think in terms of:\n"
            "- Scientific significance and novelty\n"
            "- Mathematical foundations and first principles\n"
            "- Implementation feasibility and reproducibility\n"
            "When responding conversationally, be warm, professional, and intellectually stimulating.\n"
        )

    async def run(
        self,
        research_goal: str = "",
        context: Any | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Analyze research goal and produce a structured deconstruction plan."""
        logger.info("Research Intelligence: Analyzing goal", goal=research_goal[:80])

        if context:
            await self.emit(context, "Analyzing scientific significance and defining deconstruction scope...")

        # Build the reasoning chain for scientific deconstruction
        chain = ReasoningChain(
            steps=[
                ReasoningStep(
                    name="analyze",
                    prompt_template=self._fallback_analyze_prompt(),
                    temperature=0.1,
                ),
                ReasoningStep(
                    name="generate",
                    prompt_template=self._fallback_generate_prompt(),
                    temperature=0.2,
                ),
                ReasoningStep(
                    name="refine",
                    prompt_template=self._fallback_refine_prompt(),
                    temperature=0.1,
                ),
            ],
            output_schema=DeconstructionPlan,
            max_validation_retries=2,
        )

        async def on_step(step_name: str, preview: str):
            labels = {
                "analyze": "Analyzing core scientific questions...",
                "generate": "Drafting mathematical requirements...",
                "refine": "Refining research implementation plan...",
            }
            if context:
                await self.emit(context, labels.get(step_name, f"Step: {step_name}"))

        try:
            plan = await chain.execute(
                call_llm=self.call_llm,
                on_step=on_step,
                research_goal=research_goal,
            )
        except Exception as e:
            logger.error("Research reasoning chain failed", error=str(e))
            plan = self._extract_plan_fallback(research_goal)

        if context:
            await self.emit(
                context,
                f"Research Mission Deconstructed: {plan.get('summary', 'Plan ready')}",
                level="success",
            )

        return plan

    def _fallback_analyze_prompt(self) -> str:
        return (
            "Analyze this research goal step by step:\n\n"
            "Research Goal: {research_goal}\n"
            "Identify the core scientific question and required mathematical foundations.\n"
            "Return JSON: {{\"scientific_question\": \"\", \"math_foundations\": []}}"
        )

    def _fallback_generate_prompt(self) -> str:
        return (
            "Based on: {analyze_output}\n"
            "Produce a Research Deconstruction Plan.\n"
            "Include: summary, hypotheses, math_requirements, implementation_goals.\n"
            "Return valid JSON matching DeconstructionPlan schema."
        )

    def _fallback_refine_prompt(self) -> str:
        return (
            "Refine the following plan for scientific rigor and reproducibility:\n"
            "{generate_output}\n"
            "Ensure all mathematical requirements are clearly defined."
        )

    def _extract_plan_fallback(self, goal: str) -> dict[str, Any]:
        return {
            "summary": f"Scientific deconstruction of: {goal}",
            "hypotheses": [{"statement": "Base hypothesis for verification", "confidence": 0.8}],
            "math_requirements": [{"concept": "First Principles Analysis", "formalism": "TBD"}],
            "implementation_goals": [{"module": "verification_engine", "requirements": "Python 3.11+"}],
            "estimated_complexity": "Medium",
            "novelty_score": 5,
        }
