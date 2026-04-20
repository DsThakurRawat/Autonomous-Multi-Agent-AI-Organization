"""
Multi-Turn Reasoning Chains for Agent Intelligence.

Instead of single-shot "prompt → parse → return", complex agents can now
use a ReasoningChain to break their work into multiple deliberation turns:

  1. Analyze  — Understand constraints and requirements
  2. Generate — Produce the primary output
  3. Critique — Self-evaluate for weaknesses
  4. Refine   — Revise output addressing the critique

Each turn is an LLM call whose output is fed into the next turn's context,
building a chain-of-thought that produces significantly higher-quality results.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

import structlog
from pydantic import BaseModel, ValidationError

logger = structlog.get_logger(__name__)


@dataclass
class ReasoningStep:
    """A single turn in a reasoning chain."""

    name: str
    prompt_template: str  # f-string with {variables}
    temperature: float = 0.3
    response_format: str | None = "json_object"
    # Optional: extract specific keys from the response for downstream steps
    extract_keys: list[str] = field(default_factory=list)


class ReasoningChain:
    """Orchestrates a multi-turn reasoning pipeline.

    Usage::

        chain = ReasoningChain(
            steps=[
                ReasoningStep(
                    name="analyze",
                    prompt_template="Analyze these requirements: {requirements}",
                ),
                ReasoningStep(
                    name="design",
                    prompt_template="Given your analysis: {analyze_output}\\nDesign the architecture.",
                ),
                ReasoningStep(
                    name="critique",
                    prompt_template="Find 3 weaknesses in: {design_output}",
                    temperature=0.1,
                ),
                ReasoningStep(
                    name="refine",
                    prompt_template="Revise your design addressing: {critique_output}",
                ),
            ],
            output_schema=Architecture,
        )

        result = await chain.execute(call_llm_fn, requirements="Build an API...")
    """

    def __init__(
        self,
        steps: list[ReasoningStep],
        output_schema: type[BaseModel] | None = None,
        max_validation_retries: int = 2,
    ):
        self.steps = steps
        self.output_schema = output_schema
        self.max_validation_retries = max_validation_retries

    async def execute(
        self,
        call_llm: Callable[..., Awaitable[str]],
        on_step: Callable[[str, str], Awaitable[None]] | None = None,
        **initial_context: Any,
    ) -> dict[str, Any]:
        """Run all reasoning steps sequentially.

        Args:
            call_llm: The agent's ``call_llm`` method (async).
            on_step: Optional callback ``(step_name, output_preview)`` for
                     real-time UI updates.
            **initial_context: Variables available to the first step's template.

        Returns:
            The final step's parsed output (validated against ``output_schema``
            if provided).
        """
        context: dict[str, Any] = dict(initial_context)
        final_output: dict[str, Any] = {}

        for i, step in enumerate(self.steps):
            logger.info(
                "reasoning_chain.step_start",
                step=step.name,
                index=i + 1,
                total=len(self.steps),
            )

            # Build the prompt by injecting context variables
            try:
                prompt = step.prompt_template.format(**context)
            except KeyError as e:
                logger.warning(
                    "reasoning_chain.missing_variable",
                    step=step.name,
                    variable=str(e),
                )
                # Fill missing variable with a placeholder
                prompt = step.prompt_template.format_map(
                    _DefaultDict(context)
                )

            raw = await call_llm(
                messages=[{"role": "user", "content": prompt}],
                temperature=step.temperature,
                response_format=step.response_format,
            )

            # Parse JSON response
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
            except json.JSONDecodeError:
                parsed = {"raw_text": raw}

            # Store output for downstream steps
            context[f"{step.name}_output"] = (
                json.dumps(parsed, indent=2)
                if isinstance(parsed, dict)
                else str(parsed)
            )
            # Extract specific keys if configured
            if step.extract_keys and isinstance(parsed, dict):
                for key in step.extract_keys:
                    if key in parsed:
                        context[key] = parsed[key]

            final_output = parsed if isinstance(parsed, dict) else {"result": parsed}

            if on_step:
                preview = context[f"{step.name}_output"][:200]
                await on_step(step.name, preview)

        # Validate final output against schema
        if self.output_schema is not None:
            final_output = await self._validate_with_retry(
                call_llm, final_output
            )

        return final_output

    async def _validate_with_retry(
        self,
        call_llm: Callable[..., Awaitable[str]],
        output: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate output against the Pydantic schema.

        On failure, feed the validation error back to the LLM and retry.
        """
        assert self.output_schema is not None

        for attempt in range(self.max_validation_retries + 1):
            try:
                validated = self.output_schema.model_validate(output)
                return validated.model_dump()
            except ValidationError as e:
                if attempt >= self.max_validation_retries:
                    logger.warning(
                        "reasoning_chain.validation_failed_final",
                        errors=str(e),
                    )
                    # Return raw output rather than crashing
                    return output

                logger.info(
                    "reasoning_chain.validation_retry",
                    attempt=attempt + 1,
                    errors=str(e),
                )

                fix_prompt = (
                    f"Your previous output failed validation with these errors:\n"
                    f"{e}\n\n"
                    f"Original output:\n{json.dumps(output, indent=2)[:3000]}\n\n"
                    f"Fix the output to conform to the schema. Return valid JSON only."
                )

                raw = await call_llm(
                    messages=[{"role": "user", "content": fix_prompt}],
                    temperature=0.1,
                    response_format="json_object",
                )

                try:
                    output = json.loads(raw)
                except json.JSONDecodeError:
                    pass  # Try validation again with the old output

        return output


class _DefaultDict(dict):
    """Dict subclass that returns ``'{key}'`` for missing keys instead of raising."""

    def __missing__(self, key: str) -> str:
        return f"{{unavailable: {key}}}"
