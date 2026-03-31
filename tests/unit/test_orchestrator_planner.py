"""
Unit Tests — OrchestratorEngine
Tests initialization, agent registration, event subscription, and status API.
"""

import pytest

from orchestrator.planner import (
    AgentExecutionContext,
    ExecutionEvent,
    OrchestratorEngine,
)


class TestExecutionEvent:
    def test_to_dict(self):
        event = ExecutionEvent(
            event_type="task_started",
            agent_role="CEO",
            message="Starting strategy",
            data={"key": "value"},
            level="info",
        )
        d = event.to_dict()
        assert d["type"] == "task_started"
        assert d["agent"] == "CEO"
        assert d["message"] == "Starting strategy"
        assert d["data"]["key"] == "value"
        assert d["level"] == "info"
        assert "id" in d
        assert "timestamp" in d

    def test_default_level_is_info(self):
        event = ExecutionEvent("test", "CTO", "hello")
        assert event.level == "info"

    def test_default_data_is_empty_dict(self):
        event = ExecutionEvent("test", "CTO", "hello")
        assert event.data == {}


class TestOrchestratorEngine:
    @pytest.fixture
    def engine(self):
        return OrchestratorEngine(budget_usd=100.0, output_dir="/tmp/test_output")

    def test_init(self, engine):
        assert engine.budget_usd == 100.0
        assert engine.output_dir == "/tmp/test_output"
        assert engine._agent_registry == {}
        assert engine._event_subscribers == []
        assert engine._active_projects == {}

    def test_register_agent(self, engine):
        mock_agent = object()
        engine.register_agent("CEO", mock_agent)
        assert "CEO" in engine._agent_registry
        assert engine._agent_registry["CEO"] is mock_agent

    def test_register_multiple_agents(self, engine):
        engine.register_agent("CEO", "ceo_agent")
        engine.register_agent("CTO", "cto_agent")
        engine.register_agent("QA", "qa_agent")
        assert len(engine._agent_registry) == 3

    def test_register_overwrites(self, engine):
        engine.register_agent("CEO", "agent_v1")
        engine.register_agent("CEO", "agent_v2")
        assert engine._agent_registry["CEO"] == "agent_v2"

    def test_subscribe_events(self, engine):
        callback = lambda e: None  # noqa: E731
        engine.subscribe_events(callback)
        assert callback in engine._event_subscribers

    def test_get_project_status_nonexistent(self, engine):
        result = engine.get_project_status("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_emit_calls_subscribers(self, engine):
        received = []

        async def handler(event):
            received.append(event)

        engine.subscribe_events(handler)
        event = ExecutionEvent("test", "CEO", "hello")
        await engine._emit(event)
        assert len(received) == 1
        assert received[0] is event

    @pytest.mark.asyncio
    async def test_emit_handles_failing_subscriber(self, engine):
        """A failing subscriber should not crash the emit loop."""

        async def bad_handler(event):
            raise RuntimeError("boom")

        received = []

        async def good_handler(event):
            received.append(event)

        engine.subscribe_events(bad_handler)
        engine.subscribe_events(good_handler)

        event = ExecutionEvent("test", "CEO", "hello")
        await engine._emit(event)  # Should not raise
        assert len(received) == 1  # Good handler still received it

    def test_fallback_business_plan(self, engine):
        plan = engine._generate_fallback_business_plan("AI-powered task manager")
        assert "AI-powered task manager" in plan["vision"]
        assert len(plan["mvp_features"]) == 3
        assert len(plan["milestones"]) == 3

    def test_fallback_architecture(self, engine):
        arch = engine._generate_fallback_architecture()
        assert "PostgreSQL" in arch["database"]
        assert arch["estimated_monthly_cost_usd"] == 120

    def test_fallback_task_output_backend(self, engine):
        from orchestrator.task_graph import Task

        task = Task(name="Build API", description="...", agent_role="Engineer_Backend")
        output = engine._generate_fallback_task_output(task)
        assert output["status"] == "baseline_mock"
        assert "api_code" in output

    def test_fallback_task_output_frontend(self, engine):
        from orchestrator.task_graph import Task

        task = Task(name="Build UI", description="...", agent_role="Engineer_Frontend")
        output = engine._generate_fallback_task_output(task)
        assert "ui_components" in output

    def test_fallback_task_output_qa(self, engine):
        from orchestrator.task_graph import Task

        task = Task(name="Run Tests", description="...", agent_role="QA")
        output = engine._generate_fallback_task_output(task)
        assert "test_report" in output

    def test_fallback_task_output_devops(self, engine):
        from orchestrator.task_graph import Task

        task = Task(name="Deploy", description="...", agent_role="DevOps")
        output = engine._generate_fallback_task_output(task)
        assert "infra_code" in output

    def test_fallback_task_output_unknown(self, engine):
        from orchestrator.task_graph import Task

        task = Task(name="Misc", description="...", agent_role="Finance")
        output = engine._generate_fallback_task_output(task)
        assert output["status"] == "baseline_mock"
        assert "message" in output


class TestAgentExecutionContext:
    def test_construction(self):
        ctx = AgentExecutionContext(
            project_id="proj-123",
            task=None,
            memory="mock_memory",
            decision_log="mock_log",
            cost_ledger="mock_ledger",
            artifacts="mock_artifacts",
            event_emitter=lambda e: None,
        )
        assert ctx.project_id == "proj-123"
        assert ctx.task is None
        assert ctx.memory == "mock_memory"
