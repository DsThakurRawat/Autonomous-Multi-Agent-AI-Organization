"""
Cost Ledger
Real-time AWS cost tracking and budget governance.
Finance agent reads/writes here; all agents can query budget availability.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CostEntry:
    def __init__(
        self,
        service: str,
        operation: str,
        amount_usd: float,
        agent_role: str,
        metadata: dict[str, Any] | None = None,
    ):
        self.service = service  # AWS service name
        self.operation = operation  # e.g., "ECS RunTask", "S3 PutObject"
        self.amount_usd = amount_usd
        self.agent_role = agent_role
        self.metadata = metadata or {}
        self.timestamp = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "operation": self.operation,
            "amount_usd": self.amount_usd,
            "agent_role": self.agent_role,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class CostLedger:
    """
    Budget governance and cost tracking system.
    Enforces spending limits and provides optimization signals.
    """

    def __init__(self, project_id: str, budget_usd: float = 200.0):
        self.project_id = project_id
        self.budget_usd = budget_usd
        self._entries: list[CostEntry] = []
        self.alert_threshold_pct: float = 0.80  # Alert at 80% spend
        self.on_budget_exceeded: Callable[[float, float], None] | None = None
        logger.info("CostLedger initialized", project_id=project_id, budget=budget_usd)

    def record(
        self,
        service: str,
        operation: str,
        amount_usd: float,
        agent_role: str,
        metadata: dict[str, Any] | None = None,
    ):
        """Record a cost event."""
        entry = CostEntry(service, operation, amount_usd, agent_role, metadata)
        self._entries.append(entry)

        total = self.total_spent()
        logger.info(
            "Cost recorded",
            service=service,
            amount=amount_usd,
            total_spent=total,
            budget=self.budget_usd,
        )

        # Trigger alerts
        if total > self.budget_usd:
            logger.warning("BUDGET EXCEEDED", total=total, budget=self.budget_usd)
            if self.on_budget_exceeded:
                self.on_budget_exceeded(total, self.budget_usd)
        elif total / self.budget_usd >= self.alert_threshold_pct:
            logger.warning(
                "Budget threshold reached", pct=round(total / self.budget_usd * 100, 1)
            )

    def total_spent(self) -> float:
        return round(sum(e.amount_usd for e in self._entries), 4)

    def remaining_budget(self) -> float:
        return round(self.budget_usd - self.total_spent(), 4)

    def can_spend(self, amount: float) -> bool:
        return self.remaining_budget() >= amount

    def utilization_pct(self) -> float:
        return round((self.total_spent() / self.budget_usd) * 100, 2)

    def by_service(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for e in self._entries:
            result[e.service] = round(result.get(e.service, 0) + e.amount_usd, 4)
        return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))

    def by_agent(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for e in self._entries:
            result[e.agent_role] = round(result.get(e.agent_role, 0) + e.amount_usd, 4)
        return result

    def monthly_projection(self) -> float:
        """Naive linear projection based on current spend rate, requiring a threshold elapsed time to be accurate."""
        if not self._entries:
            return 0.0
        elapsed_hours = (datetime.now(UTC) - self._entries[0].timestamp).total_seconds() / 3600

        # Don't linearly project costs if the project has run for less than 1 hour, to avoid extreme edge cases (Issue #17)
        if elapsed_hours < 1.0:
            return 0.0

        hourly_rate = self.total_spent() / elapsed_hours
        return round(hourly_rate * 24 * 30, 2)

    def get_optimization_hints(self) -> list[str]:
        """Generate cost optimization suggestions."""
        hints = []
        by_svc = self.by_service()

        if by_svc.get("ECS", 0) > 50:
            hints.append("Consider reducing ECS task CPU/memory allocation")
        if by_svc.get("RDS", 0) > 30:
            hints.append("Switch RDS to db.t3.micro or use Aurora Serverless v2")
        if self.monthly_projection() > self.budget_usd:
            hints.append(
                f"Monthly projection ${self.monthly_projection()} exceeds budget. "
                "Consider Reserved Instances or Savings Plans."
            )
        if self.utilization_pct() > 90:
            hints.append("High budget utilization - pause non-critical services")

        return hints

    def report(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "budget_usd": self.budget_usd,
            "total_spent": self.total_spent(),
            "remaining": self.remaining_budget(),
            "utilization_pct": self.utilization_pct(),
            "monthly_projection": self.monthly_projection(),
            "by_service": self.by_service(),
            "by_agent": self.by_agent(),
            "optimization_hints": self.get_optimization_hints(),
            "entry_count": len(self._entries),
        }
