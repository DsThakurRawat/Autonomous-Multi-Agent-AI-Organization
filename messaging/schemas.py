"""
Kafka Message Schemas
Pydantic models for all message types flowing through the Kafka bus.
Every message carries a trace_id for distributed tracing correlation.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MessagePriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskMessage(BaseModel):
    """
    Dispatched by Orchestrator → Kafka → Agent.
    Represents a single unit of work for a specific agent.
    """

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    task_name: str
    task_type: str  # e.g. "strategy", "architecture", "code_gen"
    agent_role: str  # e.g. "CEO", "CTO"
    project_id: str
    input_data: Dict[str, Any] = {}
    priority: MessagePriority = MessagePriority.MEDIUM
    deadline_ms: Optional[int] = None  # Unix timestamp in ms
    max_retries: int = 3
    retry_count: int = 0
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_kafka_payload(self) -> bytes:
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_kafka_payload(cls, payload: bytes) -> "TaskMessage":
        return cls.model_validate_json(payload)


class ResultMessage(BaseModel):
    """
    Published by Agent → Kafka → Orchestrator.
    Contains the outcome of a completed (or failed) task.
    """

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    task_name: str
    agent_role: str
    project_id: str
    status: str  # "completed" | "failed" | "retrying"
    output_data: Dict[str, Any] = {}
    error_message: Optional[str] = None
    duration_ms: int = 0
    cost_usd: float = 0.0
    tokens_used: int = 0
    model_used: Optional[str] = None
    trace_id: str = ""
    span_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    completed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_kafka_payload(self) -> bytes:
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_kafka_payload(cls, payload: bytes) -> "ResultMessage":
        return cls.model_validate_json(payload)


class EventMessage(BaseModel):
    """
    Published by any component → Kafka → API Gateway → WebSocket → UI.
    Represents a lifecycle event visible on the dashboard.
    """

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str  # "phase_start" | "task_completed" | "error" etc.
    agent_role: str
    project_id: str
    message: str
    data: Dict[str, Any] = {}
    level: str = "info"  # "info" | "success" | "warning" | "error"
    trace_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_kafka_payload(self) -> bytes:
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_kafka_payload(cls, payload: bytes) -> "EventMessage":
        return cls.model_validate_json(payload)

    def to_ws_dict(self) -> Dict[str, Any]:
        """WebSocket-friendly dict for frontend consumption."""
        return {
            "id": self.event_id,
            "type": self.event_type,
            "agent": self.agent_role,
            "project": self.project_id,
            "message": self.message,
            "data": self.data,
            "level": self.level,
            "timestamp": self.timestamp,
        }


class ErrorMessage(BaseModel):
    """
    Published on catastrophic failures for centralized error tracking.
    """

    error_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: Optional[str] = None
    agent_role: str
    project_id: str
    error_type: str  # "llm_failure" | "tool_error" | "timeout" etc.
    message: str
    stack_trace: Optional[str] = None
    retry_count: int = 0
    is_fatal: bool = False
    trace_id: str = ""
    occurred_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_kafka_payload(self) -> bytes:
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_kafka_payload(cls, payload: bytes) -> "ErrorMessage":
        return cls.model_validate_json(payload)


class MetricMessage(BaseModel):
    """
    Telemetry events published for real-time cost and performance tracking.
    """

    metric_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_role: str
    project_id: str
    metric_name: str  # e.g. "llm_tokens_used", "task_duration_ms"
    value: float
    unit: str  # "tokens" | "ms" | "usd" | "count"
    labels: Dict[str, str] = {}
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_kafka_payload(self) -> bytes:
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_kafka_payload(cls, payload: bytes) -> "MetricMessage":
        return cls.model_validate_json(payload)


class MoERouteRequest(BaseModel):
    """Request sent to the MoE Router for expert selection."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    task_id: str
    task_type: str
    task_name: str
    task_embedding: Optional[List[float]] = None  # Pre-computed if available
    input_context: str = ""  # Truncated context for routing
    required_skills: List[str] = []
    priority: MessagePriority = MessagePriority.MEDIUM
    ensemble_mode: bool = False  # Request multiple experts
    trace_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_kafka_payload(self) -> bytes:
        return self.model_dump_json().encode("utf-8")


class MoERouteDecision(BaseModel):
    """Decision output from the MoE Router."""

    request_id: str
    selected_expert: str  # Agent role
    fallback_experts: List[str] = []
    routing_score: float
    routing_reason: str  # Human-readable explanation
    ensemble_mode: bool = False
    confidence: float  # 0.0 - 1.0
    routed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_kafka_payload(self) -> bytes:
        return self.model_dump_json().encode("utf-8")
