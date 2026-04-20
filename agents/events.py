"""
Agent Events — Typed event system for agent-to-orchestrator communication.

Replaces the anonymous `type("E", (), {"to_dict": ...})()` pattern with
a proper dataclass that is type-safe, IDE-friendly, and testable.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class AgentEvent:
    """Typed event emitted by agents during execution.

    This is the single event type used for all agent→orchestrator communication.
    The orchestrator's event subscribers (TUI, WebSocket, logging) receive these.
    """

    event_type: str  # "thinking", "tool_call", "artifact", "progress", "error"
    agent_role: str
    message: str
    level: str = "info"  # "info", "success", "warning", "error"
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.event_type,
            "agent": self.agent_role,
            "message": self.message,
            "level": self.level,
            "data": self.data,
            "timestamp": self.timestamp,
        }
