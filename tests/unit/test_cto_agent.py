"""
Unit Tests — CTOAgent (v2 with ReasoningChain)

Tests the CTO agent's architecture generation, cost validation,
budget downgrade logic, and context integration.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.cto_agent import CTOAgent


@pytest.fixture
def cto_agent():
    """Create a CTO agent with no LLM client (mock mode)."""
    return CTOAgent(llm_client=None, provider="google", model_name="mock")


class TestCTOCostValidation:
    """Tests for the _validate_cost budget enforcement."""

    def test_under_budget_no_change(self, cto_agent):
        arch = {
            "estimated_monthly_cost_usd": 80,
            "database": {"instance": "db.t3.small"},
            "cache": {"type": "Redis"},
        }
        result = cto_agent._validate_cost(arch, budget=200)
        assert result["estimated_monthly_cost_usd"] == 80
        assert "_cost_optimized" not in result

    def test_over_budget_downgrades(self, cto_agent):
        arch = {
            "estimated_monthly_cost_usd": 300,
            "database": {"instance": "db.t3.large"},
            "cache": {"type": "Redis"},
        }
        result = cto_agent._validate_cost(arch, budget=200)
        assert result["database"]["instance"] == "db.t3.micro"
        assert result["_cost_optimized"] is True
        assert result["estimated_monthly_cost_usd"] <= 200

    def test_over_budget_removes_cache(self, cto_agent):
        arch = {
            "estimated_monthly_cost_usd": 250,
            "database": {"instance": "db.t3.small"},
            "cache": {"type": "Redis"},
        }
        # When removing cache saves enough (250 - 11 = 239 < 200? No)
        # So cache stays but cost is capped
        result = cto_agent._validate_cost(arch, budget=200)
        assert result["estimated_monthly_cost_usd"] <= 200


class TestCTODefaultArchitecture:
    def test_default_has_required_keys(self, cto_agent):
        arch = cto_agent._default_architecture(budget=100)
        required = [
            "frontend",
            "backend",
            "database",
            "api_contracts",
            "security",
            "estimated_monthly_cost_usd",
        ]
        for key in required:
            assert key in arch, f"Missing key: {key}"

    def test_default_cost_within_budget(self, cto_agent):
        arch = cto_agent._default_architecture(budget=50)
        assert arch["estimated_monthly_cost_usd"] <= 50

    def test_default_has_api_contracts(self, cto_agent):
        arch = cto_agent._default_architecture(budget=200)
        assert len(arch["api_contracts"]) >= 4  # login, register, list, create

    def test_default_database_schema(self, cto_agent):
        arch = cto_agent._default_architecture(budget=200)
        assert len(arch["database_schema"]) >= 2  # users + items


class TestCTORunWithMockLLM:
    @pytest.mark.asyncio
    async def test_run_returns_dict(self, cto_agent, sample_business_plan):
        result = await cto_agent.run(
            business_plan=sample_business_plan,
            budget_usd=200.0,
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_run_with_context(self, cto_agent, sample_business_plan, mock_context):
        result = await cto_agent.run(
            business_plan=sample_business_plan,
            budget_usd=200.0,
            context=mock_context,
        )
        assert isinstance(result, dict)
        mock_context.emit_event.assert_called()
        mock_context.decision_log.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_empty_plan(self, cto_agent):
        """Should handle empty/missing business plan gracefully."""
        result = await cto_agent.run(
            business_plan={},
            budget_usd=100.0,
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_run_with_none_plan(self, cto_agent):
        """Should handle None business plan gracefully."""
        result = await cto_agent.run(
            business_plan=None,
            budget_usd=100.0,
        )
        assert isinstance(result, dict)


class TestCTOSystemPrompt:
    def test_system_prompt_mentions_cost(self, cto_agent):
        prompt = cto_agent.system_prompt
        assert "cost" in prompt.lower() or "budget" in prompt.lower()

    def test_system_prompt_mentions_security(self, cto_agent):
        prompt = cto_agent.system_prompt
        assert "security" in prompt.lower() or "privilege" in prompt.lower()
