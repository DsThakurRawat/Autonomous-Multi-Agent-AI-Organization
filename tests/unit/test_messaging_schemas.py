"""
Unit Tests — Messaging Schemas (Pydantic roundtrip)

Tests serialization/deserialization of the core Kafka message schemas
to ensure they survive the publish→consume cycle without data loss.
"""

import json

import pytest

from messaging.schemas import (
    TaskMessage,
    ResultMessage,
    EventMessage,
    ErrorMessage,
    MetricMessage,
    MessagePriority,
)


class TestTaskMessage:
    def test_construction_with_defaults(self):
        msg = TaskMessage(
            task_id="task-001",
            task_name="Generate business plan",
            project_id="proj-001",
            task_type="strategy",
            agent_role="CEO",
            input_data={"instruction": "Build the API"},
        )
        assert msg.task_id == "task-001"
        assert msg.agent_role == "CEO"
        assert msg.priority == MessagePriority.MEDIUM
        assert msg.retry_count == 0

    def test_serialization_roundtrip(self):
        msg = TaskMessage(
            task_id="task-002",
            task_name="Design architecture",
            project_id="proj-002",
            task_type="architecture",
            agent_role="CTO",
            input_data={"business_plan": {"vision": "test"}},
            priority=MessagePriority.HIGH,
        )
        # Serialize to JSON (as Kafka would)
        json_str = msg.model_dump_json()
        # Deserialize back
        restored = TaskMessage.model_validate_json(json_str)
        assert restored.task_id == msg.task_id
        assert restored.agent_role == msg.agent_role
        assert restored.input_data == msg.input_data
        assert restored.priority == MessagePriority.HIGH

    def test_kafka_payload_roundtrip(self):
        msg = TaskMessage(
            task_id="task-003",
            task_name="Code generation",
            project_id="proj-003",
            task_type="code_gen",
            agent_role="Backend",
            input_data={"features": [{"name": "Auth", "priority": "P0"}]},
        )
        payload = msg.to_kafka_payload()
        assert isinstance(payload, bytes)
        restored = TaskMessage.from_kafka_payload(payload)
        assert restored.task_id == "task-003"
        assert len(restored.input_data["features"]) == 1

    def test_trace_id_auto_generated(self):
        msg = TaskMessage(
            task_id="t", task_name="n", project_id="p",
            task_type="t", agent_role="a",
        )
        assert msg.trace_id  # Should be non-empty UUID
        assert msg.span_id


class TestResultMessage:
    def test_success_result(self):
        msg = ResultMessage(
            task_id="task-001",
            task_name="Generate code",
            project_id="proj-001",
            agent_role="Backend",
            status="completed",
            output_data={"files_created": ["app.py", "models.py"]},
        )
        assert msg.status == "completed"
        assert "app.py" in msg.output_data["files_created"]

    def test_failure_result(self):
        msg = ResultMessage(
            task_id="task-001",
            task_name="Generate code",
            project_id="proj-001",
            agent_role="Backend",
            status="failed",
            output_data={},
            error_message="LLM call timed out",
        )
        assert msg.status == "failed"
        assert msg.error_message == "LLM call timed out"

    def test_kafka_roundtrip(self):
        msg = ResultMessage(
            task_id="task-004",
            task_name="Run QA",
            project_id="proj-004",
            agent_role="QA",
            status="completed",
            output_data={"tests_passed": 42, "coverage": 85.5},
            cost_usd=0.05,
            tokens_used=1500,
        )
        payload = msg.to_kafka_payload()
        restored = ResultMessage.from_kafka_payload(payload)
        assert restored.output_data["tests_passed"] == 42
        assert restored.cost_usd == 0.05
        assert restored.tokens_used == 1500


class TestEventMessage:
    def test_construction(self):
        msg = EventMessage(
            event_type="phase_start",
            agent_role="CTO",
            project_id="proj-001",
            message="Starting architecture phase",
        )
        assert msg.level == "info"
        assert msg.data == {}

    def test_to_ws_dict(self):
        msg = EventMessage(
            event_type="task_completed",
            agent_role="Backend",
            project_id="proj-001",
            message="Code generation complete",
            level="success",
            data={"files": 12},
        )
        ws = msg.to_ws_dict()
        assert ws["type"] == "task_completed"
        assert ws["agent"] == "Backend"
        assert ws["level"] == "success"
        assert ws["data"]["files"] == 12

    def test_kafka_roundtrip(self):
        msg = EventMessage(
            event_type="error",
            agent_role="DevOps",
            project_id="proj-002",
            message="Terraform failed",
            level="error",
        )
        payload = msg.to_kafka_payload()
        restored = EventMessage.from_kafka_payload(payload)
        assert restored.event_type == "error"
        assert restored.level == "error"


class TestErrorMessage:
    def test_construction(self):
        msg = ErrorMessage(
            agent_role="QA",
            project_id="proj-001",
            error_type="tool_error",
            message="Docker sandbox unavailable",
        )
        assert msg.is_fatal is False
        assert msg.retry_count == 0

    def test_fatal_error(self):
        msg = ErrorMessage(
            agent_role="CEO",
            project_id="proj-001",
            error_type="llm_failure",
            message="API key invalid",
            is_fatal=True,
        )
        assert msg.is_fatal is True


class TestMetricMessage:
    def test_construction(self):
        msg = MetricMessage(
            agent_role="CTO",
            project_id="proj-001",
            metric_name="llm_tokens_used",
            value=1500.0,
            unit="tokens",
        )
        assert msg.value == 1500.0
        assert msg.unit == "tokens"

    def test_kafka_roundtrip(self):
        msg = MetricMessage(
            agent_role="Finance",
            project_id="proj-001",
            metric_name="task_duration_ms",
            value=3200.0,
            unit="ms",
            labels={"model": "gemini-pro"},
        )
        payload = msg.to_kafka_payload()
        restored = MetricMessage.from_kafka_payload(payload)
        assert restored.value == 3200.0
        assert restored.labels["model"] == "gemini-pro"
