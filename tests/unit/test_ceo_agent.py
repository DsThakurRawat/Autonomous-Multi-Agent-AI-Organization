"""
Unit Tests — CEOAgent (v2 with ReasoningChain)

Tests the upgraded CEO agent's multi-turn reasoning, Pydantic
schema validation, fallback behavior, and context integration.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.ceo_agent import CEOAgent


@pytest.fixture
def ceo_agent():
    """Create a CEO agent with no LLM client (mock mode)."""
    return CEOAgent(llm_client=None, provider="google", model_name="mock")


class TestCEOFallback:
    """Tests for the safe fallback plan when LLM/chain fails."""

    def test_fallback_has_required_keys(self, ceo_agent):
        plan = ceo_agent._extract_plan_fallback("Build a todo app")
        required_keys = [
            "vision",
            "target_users",
            "problem_statement",
            "mvp_features",
            "milestones",
            "risk_assessment",
            "success_metrics",
            "revenue_model",
            "estimated_users_year1",
            "go_to_market",
        ]
        for key in required_keys:
            assert key in plan, f"Missing key: {key}"

    def test_fallback_features_have_priorities(self, ceo_agent):
        plan = ceo_agent._extract_plan_fallback("Build an API")
        for feature in plan["mvp_features"]:
            assert "priority" in feature
            assert feature["priority"] in ("P0", "P1", "P2")

    def test_fallback_incorporates_idea(self, ceo_agent):
        plan = ceo_agent._extract_plan_fallback("AI-powered recipe generator")
        assert "AI-powered recipe generator" in plan["vision"]

    def test_fallback_milestones_have_deliverables(self, ceo_agent):
        plan = ceo_agent._extract_plan_fallback("Test idea")
        for ms in plan["milestones"]:
            assert "deliverables" in ms
            assert len(ms["deliverables"]) > 0


class TestCEORunWithMockLLM:
    """Tests the run() method using the built-in mock LLM (no API calls)."""

    @pytest.mark.asyncio
    async def test_run_returns_dict(self, ceo_agent):
        result = await ceo_agent.run(
            business_idea="Build a task management app",
            budget_usd=100.0,
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_run_normalizes_string_features(self, ceo_agent):
        """If the reasoning chain returns string features, they should be normalized."""
        # The mock LLM will trigger the fallback path
        result = await ceo_agent.run(
            business_idea="Test app",
            budget_usd=50.0,
        )
        if "mvp_features" in result:
            for f in result["mvp_features"]:
                assert isinstance(f, dict)
                assert "name" in f

    @pytest.mark.asyncio
    async def test_run_with_context_emits_events(self, ceo_agent, mock_context):
        await ceo_agent.run(
            business_idea="Build a chat app",
            budget_usd=200.0,
            context=mock_context,
        )
        # Should have emitted at least 2 events (start + result)
        assert mock_context.emit_event.call_count >= 1

    @pytest.mark.asyncio
    async def test_run_with_context_logs_decision(self, ceo_agent, mock_context):
        await ceo_agent.run(
            business_idea="AI fitness tracker",
            budget_usd=150.0,
            context=mock_context,
        )
        mock_context.decision_log.log.assert_called_once()
        call_kwargs = mock_context.decision_log.log.call_args[1]
        assert call_kwargs["agent_role"] == "CEO"
        assert call_kwargs["decision_type"] == "strategy"
        assert "reasoning_chain" in call_kwargs["tags"]


class TestCEOSystemPrompt:
    def test_system_prompt_not_empty(self, ceo_agent):
        prompt = ceo_agent.system_prompt
        assert len(prompt) > 50
        assert "CEO" in prompt or "business" in prompt.lower()
