"""
Compute Monitor Agent
Optimizes and tracks computational resources, token usage, and research efficiency.
Expert in: Resource allocation, cost-performance optimization, and system telemetry.
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
    path = os.path.join(_PROMPT_DIR, "compute_monitor.yaml")
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning("Compute Monitor prompt template not found, using inline prompts")
        return {}

_PROMPT_TEMPLATE = _load_prompt()

class ComputeMonitorAgent(BaseAgent):
    """
    Compute Monitor optimizes the swarm's computational efficiency.
    Tracks usage and ensures high-fidelity research stays within resource bounds.
    """

    ROLE = "Compute_Monitor"

    @property
    def system_prompt(self) -> str:
        return _PROMPT_TEMPLATE.get("system", "") or (
            "You are the Compute Monitor of SARANG Research Swarm.\n"
            "You optimize computational resource allocation and research efficiency.\n\n"
            "Your objectives are:\n"
            "- Track and analyze LLM token usage and computational costs\n"
            "- Optimize resource allocation for complex scientific tasks\n"
            "- Monitor system telemetry and identify performance bottlenecks\n"
            "- Ensure the research swarm remains high-performance and cost-efficient\n\n"
            "You produce resource optimization reports and telemetry logs in JSON format.\n"
        )

    async def run(
        self,
        mission_parameters: dict[str, Any] | None = None,
        context: Any | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Optimize resource allocation for a research mission."""
        logger.info("Compute Monitor: Optimizing resources")
        if context:
            await self.emit(
                context,
                "Analyzing computational requirements and optimizing resource allocation...",
            )

        # Build the reasoning chain for scientific compute monitoring
        chain = ReasoningChain(
            steps=[
                ReasoningStep(
                    name="profile",
                    prompt_template="Profile the computational requirements for the mission: {input}",
                    temperature=0.1,
                ),
                ReasoningStep(
                    name="optimize",
                    prompt_template="Draft a resource optimization plan based on: {profile_output}",
                    temperature=0.2,
                ),
                ReasoningStep(
                    name="monitor",
                    prompt_template="Define telemetry checkpoints and bounds for: {optimize_output}",
                    temperature=0.1,
                ),
            ],
            output_schema=None,
            max_validation_retries=2,
        )

        async def on_step(step_name: str, preview: str):
            labels = {
                "profile": "Profiling computational requirements...",
                "optimize": "Drafting resource optimization plan...",
                "monitor": "Setting telemetry bounds and alerts...",
            }
            if context:
                await self.emit(context, labels.get(step_name, f"Compute Step: {step_name}"))

        try:
            optimization = await chain.execute(
                call_llm=self.call_llm,
                on_step=on_step,
                input=json.dumps(mission_parameters or {}),
            )
        except Exception as e:
            logger.error("Compute monitoring reasoning chain failed", error=str(e))
            optimization = {"error": str(e), "status": "failed"}

        if context:
            await self.emit(
                context,
                "Resource allocation optimized. Swarm performance maximized.",
                level="success",
            )

        return optimization
