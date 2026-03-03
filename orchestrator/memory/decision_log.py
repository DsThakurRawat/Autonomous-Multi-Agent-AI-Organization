"""
Decision Log
Immutable audit trail of every agent decision.
Used for explainability, rollback, and continuous improvement.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
import structlog

logger = structlog.get_logger(__name__)


class DecisionRecord:
    """A single decision made by an agent."""

    def __init__(
        self,
        agent_role: str,
        decision_type: str,  # architecture, code, deploy, risk, cost
        description: str,
        rationale: str,
        input_context: Dict[str, Any],
        output: Dict[str, Any],
        confidence: float = 1.0,
        alternatives_considered: List[str] = None,
        tags: List[str] = None,
    ):
        self.id = str(uuid.uuid4())
        self.agent_role = agent_role
        self.decision_type = decision_type
        self.description = description
        self.rationale = rationale
        self.input_context = input_context
        self.output = output
        self.confidence = confidence
        self.alternatives_considered = alternatives_considered or []
        self.tags = tags or []
        self.timestamp = datetime.utcnow()
        self.superseded_by: Optional[str] = None  # ID of newer decision

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_role": self.agent_role,
            "decision_type": self.decision_type,
            "description": self.description,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "alternatives": self.alternatives_considered,
            "tags": self.tags,
            "timestamp": self.timestamp.isoformat(),
            "superseded_by": self.superseded_by,
            "output_summary": {k: str(v)[:200] for k, v in self.output.items()},
        }


class DecisionLog:
    """
    Append-only log of all agent decisions.
    Provides query interface for timeline, filtering, and rollback planning.
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self._records: List[DecisionRecord] = []
        logger.info("DecisionLog initialized", project_id=project_id)

    def log(
        self,
        agent_role: str,
        decision_type: str,
        description: str,
        rationale: str,
        input_context: Dict[str, Any],
        output: Dict[str, Any],
        confidence: float = 1.0,
        alternatives: List[str] = None,
        tags: List[str] = None,
    ) -> str:
        """Log a new decision and return its ID."""
        record = DecisionRecord(
            agent_role=agent_role,
            decision_type=decision_type,
            description=description,
            rationale=rationale,
            input_context=input_context,
            output=output,
            confidence=confidence,
            alternatives_considered=alternatives or [],
            tags=tags or [],
        )
        self._records.append(record)
        logger.info(
            "Decision logged",
            decision_id=record.id,
            agent=agent_role,
            type=decision_type,
            description=description[:80],
        )
        return record.id

    def get_by_agent(self, agent_role: str) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._records if r.agent_role == agent_role]

    def get_by_type(self, decision_type: str) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._records if r.decision_type == decision_type]

    def get_timeline(self) -> List[Dict[str, Any]]:
        """Return all decisions sorted by time."""
        return [r.to_dict() for r in sorted(self._records, key=lambda x: x.timestamp)]

    def get_low_confidence_decisions(
        self, threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Surface decisions that might need human review."""
        return [
            r.to_dict()
            for r in self._records
            if r.confidence < threshold and not r.superseded_by
        ]

    def supersede(self, old_id: str, new_id: str):
        """Mark a decision as replaced by a newer one."""
        for r in self._records:
            if r.id == old_id:
                r.superseded_by = new_id
                break

    def summary(self) -> Dict[str, Any]:
        agent_counts: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}
        for r in self._records:
            agent_counts[r.agent_role] = agent_counts.get(r.agent_role, 0) + 1
            type_counts[r.decision_type] = type_counts.get(r.decision_type, 0) + 1

        return {
            "total_decisions": len(self._records),
            "by_agent": agent_counts,
            "by_type": type_counts,
            "low_confidence_count": len(self.get_low_confidence_decisions()),
            "avg_confidence": (
                sum(r.confidence for r in self._records) / len(self._records)
                if self._records
                else 0.0
            ),
        }
