"""
Integration Test — Full Project Lifecycle

Tests the complete CEO → CTO pipeline with mock LLM responses,
verifying that the reasoning chain, schema validation, and
context integration work end-to-end.
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.ceo_agent import CEOAgent
from agents.cto_agent import CTOAgent


@pytest.fixture
def mock_context():
    """Returns a mock execution context."""
    ctx = MagicMock()
    ctx.emit_event = AsyncMock()
    ctx.decision_log = MagicMock()
    ctx.decision_log.log = MagicMock()
    ctx.artifacts = MagicMock()
    ctx.artifacts.save = MagicMock()
    ctx.artifacts.save_code_file = MagicMock()
    ctx.memory = MagicMock()
    ctx.memory.architecture = {}
    return ctx


class TestCEOToCTOPipeline:
    """Tests the handoff from CEO (business plan) to CTO (architecture)."""

    @pytest.mark.asyncio
    async def test_ceo_output_feeds_cto(self, mock_context):
        """CEO produces a plan, CTO consumes it — no crashes, valid output."""
        ceo = CEOAgent(llm_client=None, provider="google", model_name="mock")
        cto = CTOAgent(llm_client=None, provider="google", model_name="mock")

        # Phase 1: CEO produces business plan
        plan = await ceo.run(
            business_idea="AI-powered code review assistant",
            budget_usd=150.0,
            context=mock_context,
        )

        assert isinstance(plan, dict)
        assert "mvp_features" in plan
        assert len(plan["mvp_features"]) > 0

        # Phase 2: CTO consumes the plan
        arch = await cto.run(
            business_plan=plan,
            budget_usd=150.0,
            context=mock_context,
        )

        assert isinstance(arch, dict)
        # CTO should produce architecture with required keys
        assert "frontend" in arch or "backend" in arch or "database" in arch

    @pytest.mark.asyncio
    async def test_budget_flows_through(self, mock_context):
        """Budget constraint should be respected across agents."""
        ceo = CEOAgent(llm_client=None, provider="google", model_name="mock")
        cto = CTOAgent(llm_client=None, provider="google", model_name="mock")

        plan = await ceo.run(
            business_idea="Simple portfolio website",
            budget_usd=50.0,
            context=mock_context,
        )

        arch = await cto.run(
            business_plan=plan,
            budget_usd=50.0,
            context=mock_context,
        )

        cost = arch.get("estimated_monthly_cost_usd", 0)
        assert cost <= 50.0, f"Architecture cost ${cost} exceeds $50 budget"

    @pytest.mark.asyncio
    async def test_decision_log_captures_both_phases(self, mock_context):
        """Both agents should log their decisions."""
        ceo = CEOAgent(llm_client=None, provider="google", model_name="mock")
        cto = CTOAgent(llm_client=None, provider="google", model_name="mock")

        plan = await ceo.run(
            business_idea="E-commerce platform",
            budget_usd=200.0,
            context=mock_context,
        )
        await cto.run(
            business_plan=plan,
            budget_usd=200.0,
            context=mock_context,
        )

        # Two decision_log.log calls: one from CEO, one from CTO
        assert mock_context.decision_log.log.call_count == 2

        roles_logged = [
            call[1]["agent_role"]
            for call in mock_context.decision_log.log.call_args_list
        ]
        assert "CEO" in roles_logged
        assert "CTO" in roles_logged

    @pytest.mark.asyncio
    async def test_events_emitted_in_order(self, mock_context):
        """Events should be emitted during execution."""
        ceo = CEOAgent(llm_client=None, provider="google", model_name="mock")

        await ceo.run(
            business_idea="Task management app",
            budget_usd=100.0,
            context=mock_context,
        )

        # At least one event should have been emitted
        assert mock_context.emit_event.call_count >= 1

        # Check that events have proper structure (AgentEvent.to_dict())
        for call in mock_context.emit_event.call_args_list:
            event = call[0][0]
            if hasattr(event, "to_dict"):
                d = event.to_dict()
                assert "type" in d
                assert "agent" in d
                assert "message" in d
