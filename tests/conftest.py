"""
Shared test fixtures for the SARANG test suite.

Provides reusable mock objects, agent factories, and workspace helpers
that eliminate boilerplate across unit and integration tests.
"""

import asyncio
import json
import os
import tempfile
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.events import AgentEvent


# ── Mock LLM Client ─────────────────────────────────────────────────


class MockLLMClient:
    """Deterministic LLM client that returns preconfigured JSON responses.

    Usage::

        client = MockLLMClient(responses=[
            '{"vision": "test", ...}',  # First call returns this
            '{"scores": {...}}',        # Second call returns this
        ])
    """

    def __init__(self, responses: list[str] | None = None):
        self.responses = responses or []
        self._call_index = 0
        self.call_history: list[dict] = []

    def next_response(self) -> str:
        if self._call_index < len(self.responses):
            resp = self.responses[self._call_index]
            self._call_index += 1
            return resp
        # Default fallback
        return json.dumps({"status": "mock_default", "agent": "mock"})


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def mock_llm_responses():
    """Factory fixture: returns a MockLLMClient with the given responses.

    Usage::

        def test_something(mock_llm_responses):
            client = mock_llm_responses(['{"key": "val"}'])
    """

    def _factory(responses: list[str]) -> MockLLMClient:
        return MockLLMClient(responses=responses)

    return _factory


@pytest.fixture
def mock_context():
    """Returns a mock execution context with emit_event, decision_log, artifacts, and memory."""
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


@pytest.fixture
def tmp_workspace(tmp_path):
    """Creates a temporary workspace directory for tool tests.

    Returns the path as a string. Files can be created inside it.
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return str(workspace)


@pytest.fixture
def sample_business_plan():
    """Returns a realistic business plan dict for CTO/Backend agent tests."""
    return {
        "vision": "AI-powered meal planning for busy professionals",
        "target_users": "Working professionals aged 25-45",
        "problem_statement": "Meal planning takes 2+ hours per week",
        "mvp_features": [
            {
                "name": "Preference Quiz",
                "priority": "P0",
                "description": "5-question onboarding for dietary preferences",
            },
            {
                "name": "AI Meal Plan Generator",
                "priority": "P0",
                "description": "Generate 7-day meal plan using LLM",
            },
            {
                "name": "Grocery List Export",
                "priority": "P1",
                "description": "Auto-generate shopping list from weekly plan",
            },
        ],
        "milestones": [
            {
                "phase": "Architecture",
                "duration_days": 1,
                "deliverables": ["System design", "DB schema"],
            },
            {
                "phase": "Backend",
                "duration_days": 3,
                "deliverables": ["API", "Auth", "DB models"],
            },
        ],
        "risk_assessment": [
            {
                "risk": "LLM cost overrun",
                "impact": "High",
                "mitigation": "Token budget cap per request",
            }
        ],
        "success_metrics": ["500 meal plans in month 1", "40% week-2 retention"],
        "revenue_model": "Freemium: free 1 plan/week, $9.99/month unlimited",
        "estimated_users_year1": 5000,
        "go_to_market": "Product Hunt launch + LinkedIn content",
    }
