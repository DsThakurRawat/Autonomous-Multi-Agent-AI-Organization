"""
Peer Reviewer Agent
Scrutinizes research hypotheses, mathematical proofs, and code implementations.
Expert in: Scientific rigor, adversarial critique, and methodology validation.
"""

import json
import os
from typing import Any

import structlog
import yaml

from .base_agent import BaseAgent
from .reasoning import ReasoningChain, ReasoningStep

logger = structlog.get_logger(__name__)

# Load prompt template once at module level
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")

def _load_prompt() -> dict:
    path = os.path.join(_PROMPT_DIR, "peer_reviewer.yaml")
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning("Peer Reviewer prompt template not found, using inline prompts")
        return {}

_PROMPT_TEMPLATE = _load_prompt()

class PeerReviewerAgent(BaseAgent):
    """
    Peer Reviewer scrutinizes every step of the research process.
    Provides adversarial critique to ensure absolute scientific rigor.
    """

    ROLE = "Peer_Reviewer"

    @property
    def system_prompt(self) -> str:
        return _PROMPT_TEMPLATE.get("system", "") or (
            "You are the Peer Reviewer of SARANG Research Swarm.\n"
            "You provide rigorous, adversarial critique of scientific work.\n\n"
            "Your objectives are:\n"
            "- Identify logical fallacies and methodology gaps\n"
            "- Challenge mathematical assumptions and proofs\n"
            "- Critique implementation accuracy and edge cases\n"
            "- Ensure results are presented with pedagogical clarity\n\n"
            "You produce detailed critique reports in structured JSON format.\n"
        )

    async def run(
        self,
        research_artifact: dict[str, Any] | None = None,
        context: Any | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Critique a research artifact for scientific rigor."""
        logger.info("Peer Reviewer: Scrutinizing artifact")
        if context:
            await self.emit(
                context,
                "Commencing adversarial peer review of the research artifact...",
            )

        # Build the reasoning chain for scientific peer review
        chain = ReasoningChain(
            steps=[
                ReasoningStep(
                    name="scrutinize",
                    prompt_template="Identify potential logical gaps or methodology errors in: {input}",
                    temperature=0.1,
                ),
                ReasoningStep(
                    name="critique",
                    prompt_template="Draft a detailed adversarial critique based on: {scrutinize_output}",
                    temperature=0.2,
                ),
                ReasoningStep(
                    name="recommend",
                    prompt_template="Suggest rigorous improvements and validation steps for: {critique_output}",
                    temperature=0.2,
                ),
            ],
            output_schema=None,
            max_validation_retries=2,
        )

        async def on_step(step_name: str, preview: str):
            labels = {
                "scrutinize": "Scrutinizing logic and methodology...",
                "critique": "Drafting adversarial critique...",
                "recommend": "Formulating rigorous improvements...",
            }
            if context:
                await self.emit(context, labels.get(step_name, f"Review Step: {step_name}"))

        try:
            review = await chain.execute(
                call_llm=self.call_llm,
                on_step=on_step,
                input=json.dumps(research_artifact or {}),
            )
        except Exception as e:
            logger.error("Peer review reasoning chain failed", error=str(e))
            review = {"error": str(e), "status": "failed"}

        if context:
            await self.emit(
                context,
                "Peer review complete. Scientific rigor validated.",
                level="success",
            )

        return review
