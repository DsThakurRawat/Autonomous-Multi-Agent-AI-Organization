"""
Math Architect Agent
Deconstructs complex research papers into their core mathematical components.
Analyzes derivations, identifies theorems, and validates proof logic.
"""

import json
import os
from typing import Any

import structlog
import yaml

from .base_agent import BaseAgent
from .reasoning import ReasoningChain, ReasoningStep
from .schemas import MathRequirement

logger = structlog.get_logger(__name__)

# Load prompt template once at module level
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")

def _load_prompt() -> dict:
    path = os.path.join(_PROMPT_DIR, "math_architect.yaml")
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning("Math Architect prompt template not found, using inline prompts")
        return {}

_PROMPT_TEMPLATE = _load_prompt()

class MathArchitectAgent(BaseAgent):
    """
    Math Architect deconstructs the mathematical foundation of research.
    Expert in: First-principles derivation, proof validation, and complexity analysis.
    """

    ROLE = "Math_Architect"

    @property
    def system_prompt(self) -> str:
        return _PROMPT_TEMPLATE.get("system", "") or (
            "You are the Math Architect of SARANG Research Swarm.\n"
            "You deconstruct scientific papers into first-principles mathematics.\n\n"
            "Your objectives are:\n"
            "- Extract core equations and derivations\n"
            "- Validate mathematical proofs and logical steps\n"
            "- Identify underlying theorems and axioms\n"
            "- Analyze computational complexity and bottlenecks\n\n"
            "You produce rigorous mathematical deconstructions in structured JSON format.\n"
        )

    async def run(
        self,
        hypothesis: str | None = None,
        paper_text: str | None = None,
        context: Any | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Analyze the mathematical foundation of a research paper or hypothesis."""
        logger.info("Math Architect: Deconstructing mathematics")
        if context:
            await self.emit(
                context,
                "Analyzing mathematical derivations and proof structures...",
            )

        # Build the reasoning chain for scientific math deconstruction
        chain = ReasoningChain(
            steps=[
                ReasoningStep(
                    name="identify",
                    prompt_template="Identify the core mathematical equations and theorems in: {input}",
                    temperature=0.1,
                ),
                ReasoningStep(
                    name="derive",
                    prompt_template="Deconstruct the derivation steps and logical flow from: {identify_output}",
                    temperature=0.2,
                ),
                ReasoningStep(
                    name="validate",
                    prompt_template="Critique the mathematical rigor and check for SPOFs (Logical Failures) in: {derive_output}",
                    temperature=0.1,
                ),
            ],
            output_schema=MathRequirement,
            max_validation_retries=2,
        )

        async def on_step(step_name: str, preview: str):
            labels = {
                "identify": "Identifying core theorems and variables...",
                "derive": "Mapping the derivation flow...",
                "validate": "Validating mathematical rigor and proofs...",
            }
            if context:
                await self.emit(context, labels.get(step_name, f"Math Step: {step_name}"))

        try:
            deconstruction = await chain.execute(
                call_llm=self.call_llm,
                on_step=on_step,
                input=paper_text or hypothesis or "No input provided",
            )
        except Exception as e:
            logger.error("Math reasoning chain failed", error=str(e))
            deconstruction = {"error": str(e), "status": "failed"}

        if context:
            await self.emit(
                context,
                "Mathematical deconstruction complete. Foundations validated.",
                level="success",
            )

        return deconstruction
