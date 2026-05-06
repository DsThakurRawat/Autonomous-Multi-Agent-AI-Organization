"""
Visual Insights Agent
Translates complex research data and architecture into high-fidelity visualizations.
Expert in: Data visualization, pedagogical UI, and scientific charting.
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
    path = os.path.join(_PROMPT_DIR, "visual_insights.yaml")
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning("Visual Insights prompt template not found, using inline prompts")
        return {}

_PROMPT_TEMPLATE = _load_prompt()

class VisualInsightsAgent(BaseAgent):
    """
    Visual Insights agent creates the UI/UX for scientific exploration.
    Focused on making complex data intuitive and pedagogically clear.
    """

    ROLE = "Visual_Insights"

    @property
    def system_prompt(self) -> str:
        return _PROMPT_TEMPLATE.get("system", "") or (
            "You are the Visual Insights Specialist of SARANG Research Swarm.\n"
            "You translate complex scientific data into stunning, intuitive visualizations.\n\n"
            "Your objectives are:\n"
            "- Design pedagogical UI components for research exploration\n"
            "- Generate high-fidelity data charts and architectural diagrams\n"
            "- Optimize the user experience for scientific rigor and clarity\n"
            "- Ensure all visualizations are interactive and insights-driven\n\n"
            "You produce UI specifications and visualization code in structured JSON format.\n"
        )

    async def run(
        self,
        research_data: dict[str, Any] | None = None,
        context: Any | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate visualizations for research data."""
        logger.info("Visual Insights: Designing visualizations")
        if context:
            await self.emit(
                context,
                "Designing high-fidelity visualizations for the research insights...",
            )

        # Build the reasoning chain for scientific visualization
        chain = ReasoningChain(
            steps=[
                ReasoningStep(
                    name="map_data",
                    prompt_template="Map the research data to visual metaphors and charts for: {input}",
                    temperature=0.2,
                ),
                ReasoningStep(
                    name="design_ui",
                    prompt_template="Design the pedagogical UI components based on: {map_data_output}",
                    temperature=0.2,
                ),
                ReasoningStep(
                    name="optimize_ux",
                    prompt_template="Refine the visual insights for clarity and rigor: {design_ui_output}",
                    temperature=0.1,
                ),
            ],
            output_schema=None,
            max_validation_retries=2,
        )

        async def on_step(step_name: str, preview: str):
            labels = {
                "map_data": "Mapping data to visual metrics...",
                "design_ui": "Drafting UI/UX components...",
                "optimize_ux": "Optimizing for pedagogical clarity...",
            }
            if context:
                await self.emit(context, labels.get(step_name, f"Visual Step: {step_name}"))

        try:
            visuals = await chain.execute(
                call_llm=self.call_llm,
                on_step=on_step,
                input=json.dumps(research_data or {}),
            )
        except Exception as e:
            logger.error("Visual insights reasoning chain failed", error=str(e))
            visuals = {"error": str(e), "status": "failed"}

        if context:
            await self.emit(
                context,
                "Visualizations designed. Research insights now intuitive.",
                level="success",
            )

        return visuals
