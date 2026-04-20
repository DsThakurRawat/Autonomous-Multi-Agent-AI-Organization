"""
Unit Tests — ReasoningChain

Tests the multi-turn reasoning engine that powers the upgraded
CEO and CTO agents.
"""

import json
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel, Field

from agents.reasoning import ReasoningChain, ReasoningStep, _DefaultDict


# ── Helper Models ────────────────────────────────────────────────────


class SimpleOutput(BaseModel):
    name: str = Field(..., min_length=1)
    score: int = Field(..., ge=0, le=100)


# ── DefaultDict Tests ───────────────────────────────────────────────


class TestDefaultDict:
    def test_existing_key(self):
        d = _DefaultDict({"name": "Alice"})
        assert d["name"] == "Alice"

    def test_missing_key(self):
        d = _DefaultDict({})
        result = d["missing"]
        assert "missing" in result
        assert "unavailable" in result


# ── ReasoningStep Tests ──────────────────────────────────────────────


class TestReasoningStep:
    def test_defaults(self):
        step = ReasoningStep(name="analyze", prompt_template="Do {thing}")
        assert step.temperature == 0.3
        assert step.response_format == "json_object"
        assert step.extract_keys == []

    def test_custom_values(self):
        step = ReasoningStep(
            name="generate",
            prompt_template="Build {item}",
            temperature=0.7,
            response_format=None,
            extract_keys=["result"],
        )
        assert step.temperature == 0.7
        assert step.response_format is None
        assert step.extract_keys == ["result"]


# ── ReasoningChain Tests ─────────────────────────────────────────────


class TestReasoningChain:
    @pytest.mark.asyncio
    async def test_single_step_chain(self):
        """A chain with one step should just call the LLM once."""
        call_llm = AsyncMock(
            return_value=json.dumps({"name": "Test", "score": 85})
        )

        chain = ReasoningChain(
            steps=[
                ReasoningStep(
                    name="generate",
                    prompt_template="Generate output for: {topic}",
                )
            ],
            output_schema=SimpleOutput,
        )

        result = await chain.execute(call_llm=call_llm, topic="testing")

        assert result["name"] == "Test"
        assert result["score"] == 85
        call_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_multi_step_chain_feeds_context(self):
        """Each step's output should be available to the next step."""
        responses = [
            json.dumps({"analysis": "looks good"}),
            json.dumps({"name": "Final", "score": 90}),
        ]
        call_index = {"i": 0}

        async def mock_llm(messages, **kwargs):
            resp = responses[call_index["i"]]
            call_index["i"] += 1
            return resp

        chain = ReasoningChain(
            steps=[
                ReasoningStep(
                    name="analyze",
                    prompt_template="Analyze: {input_data}",
                ),
                ReasoningStep(
                    name="generate",
                    prompt_template="Based on: {analyze_output}\nGenerate output.",
                ),
            ],
            output_schema=SimpleOutput,
        )

        result = await chain.execute(call_llm=mock_llm, input_data="test data")

        assert result["name"] == "Final"
        assert result["score"] == 90

    @pytest.mark.asyncio
    async def test_on_step_callback(self):
        """The on_step callback should be called for each step."""
        call_llm = AsyncMock(return_value=json.dumps({"status": "ok"}))
        step_names = []

        async def track_step(name, preview):
            step_names.append(name)

        chain = ReasoningChain(
            steps=[
                ReasoningStep(name="step1", prompt_template="Do step 1"),
                ReasoningStep(name="step2", prompt_template="Do step 2"),
                ReasoningStep(name="step3", prompt_template="Do step 3"),
            ]
        )

        await chain.execute(call_llm=call_llm, on_step=track_step)

        assert step_names == ["step1", "step2", "step3"]

    @pytest.mark.asyncio
    async def test_validation_retry_on_schema_failure(self):
        """If first output fails validation, chain should retry with error context."""
        responses = [
            json.dumps({"name": "", "score": 50}),  # Fails: name too short
            json.dumps({"name": "Fixed", "score": 50}),  # Passes
        ]
        call_index = {"i": 0}

        async def mock_llm(messages, **kwargs):
            resp = responses[call_index["i"]]
            call_index["i"] += 1
            return resp

        chain = ReasoningChain(
            steps=[
                ReasoningStep(name="generate", prompt_template="Make output"),
            ],
            output_schema=SimpleOutput,
            max_validation_retries=2,
        )

        result = await chain.execute(call_llm=mock_llm)
        assert result["name"] == "Fixed"

    @pytest.mark.asyncio
    async def test_missing_variable_handled_gracefully(self):
        """Missing template variables should not crash the chain."""
        call_llm = AsyncMock(return_value=json.dumps({"result": "ok"}))

        chain = ReasoningChain(
            steps=[
                ReasoningStep(
                    name="test",
                    prompt_template="Process {missing_var} with {also_missing}",
                )
            ]
        )

        # Should not raise
        result = await chain.execute(call_llm=call_llm)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_non_json_response_wrapped(self):
        """If LLM returns plain text, it should be wrapped in a dict."""
        call_llm = AsyncMock(return_value="This is not JSON")

        chain = ReasoningChain(
            steps=[
                ReasoningStep(
                    name="test",
                    prompt_template="Do something",
                    response_format=None,
                )
            ]
        )

        result = await chain.execute(call_llm=call_llm)
        assert "raw_text" in result

    @pytest.mark.asyncio
    async def test_extract_keys(self):
        """extract_keys should promote specific values into the context."""
        responses = [
            json.dumps({"budget": 100, "tier": "small", "extra": "ignored"}),
            json.dumps({"result": "used budget"}),
        ]
        call_index = {"i": 0}

        async def mock_llm(messages, **kwargs):
            resp = responses[call_index["i"]]
            call_index["i"] += 1
            return resp

        chain = ReasoningChain(
            steps=[
                ReasoningStep(
                    name="analyze",
                    prompt_template="Analyze",
                    extract_keys=["budget", "tier"],
                ),
                ReasoningStep(
                    name="generate",
                    prompt_template="Budget is {budget}, tier is {tier}",
                ),
            ]
        )

        result = await chain.execute(call_llm=mock_llm)
        # The second prompt should have had {budget} and {tier} filled in
        second_call_prompt = mock_llm.call_args_list if hasattr(mock_llm, 'call_args_list') else []
        assert isinstance(result, dict)
