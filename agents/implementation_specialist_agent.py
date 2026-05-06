"""
Implementation Specialist Agent
Translates mathematical deconstructions and research goals into executable code.
Expert in: Scientific computing, simulation engines, and algorithm implementation.
"""

import json
import os
from typing import Any

import structlog
import yaml

from .base_agent import BaseAgent
from .reasoning import ReasoningChain, ReasoningStep
from .schemas import ImplementationGoal

logger = structlog.get_logger(__name__)

# Load prompt template once at module level
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")

def _load_prompt() -> dict:
    path = os.path.join(_PROMPT_DIR, "implementation_specialist.yaml")
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning("Implementation Specialist prompt template not found, using inline prompts")
        return {}

_PROMPT_TEMPLATE = _load_prompt()

class ImplementationSpecialistAgent(BaseAgent):
    """
    Implementation Specialist builds the research artifacts.
    Focused on translating theoretical math into practical software implementations.
    """

    ROLE = "Implementation_Specialist"

    @property
    def system_prompt(self) -> str:
        return _PROMPT_TEMPLATE.get("system", "") or (
            "You are the Implementation Specialist of SARANG Research Swarm.\n"
            "You translate scientific theory and mathematics into production-grade code.\n\n"
            "Your objectives are:\n"
            "- Implement core algorithms based on mathematical derivations\n"
            "- Develop simulation environments for research validation\n"
            "- Optimize code for performance and scientific accuracy\n"
            "- Ensure implementations are modular and well-documented\n\n"
            "You produce complete, runnable implementations in structured JSON format.\n"
        )

    async def run(
        self,
        math_deconstruction: dict[str, Any] | None = None,
        goal: str | None = None,
        context: Any | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Implement the software components based on mathematical requirements."""
        logger.info("Implementation Specialist: Generating research code")
        if context:
            await self.emit(
                context,
                "Translating mathematical foundations into executable algorithms...",
            )

        # Build the reasoning chain for scientific implementation
        chain = ReasoningChain(
            steps=[
                ReasoningStep(
                    name="blueprint",
                    prompt_template="Design the software blueprint for this math: {input}",
                    temperature=0.2,
                ),
                ReasoningStep(
                    name="implement",
                    prompt_template="Generate the core implementation code based on: {blueprint_output}",
                    temperature=0.2,
                ),
                ReasoningStep(
                    name="optimize",
                    prompt_template="Refine the implementation for scientific accuracy and performance: {implement_output}",
                    temperature=0.1,
                ),
            ],
            output_schema=ImplementationGoal,
            max_validation_retries=2,
        )

        async def on_step(step_name: str, preview: str):
            labels = {
                "blueprint": "Drafting implementation architecture...",
                "implement": "Writing core algorithmic logic...",
                "optimize": "Optimizing for research performance...",
            }
            if context:
                await self.emit(context, labels.get(step_name, f"Implementation Step: {step_name}"))

        try:
            implementation = await chain.execute(
                call_llm=self.call_llm,
                on_step=on_step,
                input=json.dumps(math_deconstruction or {}) if math_deconstruction else (goal or "No goal provided"),
            )
        except Exception as e:
            logger.error("Implementation reasoning chain failed", error=str(e))
            implementation = {"error": str(e), "status": "failed"}

        if context:
            await self.emit(
                context,
                "Implementation complete. Research artifacts generated.",
                level="success",
            )

        return implementation
