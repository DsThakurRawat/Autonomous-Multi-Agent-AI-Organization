"""
Production-Grade Tests — Cost Ledger & Budget Governance
Real-life scenarios: budget enforcement, multi-agent spend tracking,
cost projection, optimization hints, and callback triggers.
"""

import pytest

from orchestrator.memory.cost_ledger import CostEntry, CostLedger


class TestCostEntrySerialisation:
    def test_to_dict_has_all_fields(self):
        entry = CostEntry(
            service="ECS",
            operation="RunTask",
            amount_usd=1.50,
            agent_role="DevOps",
            metadata={"cluster": "prod"},
        )
        d = entry.to_dict()
        assert d["service"] == "ECS"
        assert d["operation"] == "RunTask"
        assert d["amount_usd"] == 1.50
        assert d["agent_role"] == "DevOps"
        assert d["metadata"]["cluster"] == "prod"
        assert "timestamp" in d


class TestBudgetEnforcement:
    """Production scenario: agents must not exceed project budget."""

    @pytest.fixture
    def ledger(self):
        return CostLedger(project_id="proj-budget-test", budget_usd=100.0)

    def test_can_spend_within_budget(self, ledger):
        ledger.record("ECS", "RunTask", 40.0, "DevOps")
        assert ledger.can_spend(50.0) is True

    def test_cannot_spend_beyond_budget(self, ledger):
        ledger.record("ECS", "RunTask", 80.0, "DevOps")
        assert ledger.can_spend(25.0) is False

    def test_remaining_budget_decreases(self, ledger):
        assert ledger.remaining_budget() == 100.0
        ledger.record("S3", "PutObject", 10.0, "Engineer_Backend")
        assert ledger.remaining_budget() == 90.0

    def test_budget_callback_fires_on_exceed(self, ledger):
        fired = []
        ledger.on_budget_exceeded = lambda total, budget: fired.append((total, budget))
        ledger.record("ECS", "RunTask", 60.0, "DevOps")
        assert len(fired) == 0  # Still within budget
        ledger.record("RDS", "CreateInstance", 50.0, "DevOps")
        assert len(fired) == 1  # Now exceeded
        assert fired[0][0] == 110.0
        assert fired[0][1] == 100.0

    def test_zero_budget_blocks_everything(self):
        ledger = CostLedger(project_id="proj-zero", budget_usd=0.0)
        assert ledger.can_spend(0.01) is False


class TestMultiAgentSpendTracking:
    """Production scenario: 7 agents spending concurrently must be tracked per-agent."""

    @pytest.fixture
    def ledger(self):
        return CostLedger(project_id="proj-multi", budget_usd=500.0)

    def test_by_agent_tracks_all_roles(self, ledger):
        ledger.record("Bedrock", "InvokeModel", 0.05, "CEO")
        ledger.record("Bedrock", "InvokeModel", 0.08, "CTO")
        ledger.record("Bedrock", "InvokeModel", 0.12, "Engineer_Backend")
        ledger.record("Bedrock", "InvokeModel", 0.10, "Engineer_Frontend")
        ledger.record("Bedrock", "InvokeModel", 0.07, "QA")
        ledger.record("ECS", "RunTask", 2.50, "DevOps")
        ledger.record("Bedrock", "InvokeModel", 0.03, "Finance")

        by_agent = ledger.by_agent()
        assert len(by_agent) == 7
        assert by_agent["DevOps"] == 2.50  # Highest spender

    def test_by_service_aggregates_correctly(self, ledger):
        ledger.record("Bedrock", "InvokeModel", 0.05, "CEO")
        ledger.record("Bedrock", "InvokeModel", 0.08, "CTO")
        ledger.record("ECS", "RunTask", 2.50, "DevOps")
        ledger.record("S3", "PutObject", 0.01, "Engineer_Backend")

        by_svc = ledger.by_service()
        assert by_svc["Bedrock"] == 0.13
        # Services sorted descending by cost
        services = list(by_svc.keys())
        assert services[0] == "ECS"


class TestUtilisationAndReport:
    def test_utilization_pct_accurate(self):
        ledger = CostLedger(project_id="proj-util", budget_usd=200.0)
        ledger.record("ECS", "RunTask", 50.0, "DevOps")
        assert ledger.utilization_pct() == 25.0

    def test_full_report_structure(self):
        ledger = CostLedger(project_id="proj-report", budget_usd=200.0)
        ledger.record("ECS", "RunTask", 50.0, "DevOps")
        report = ledger.report()
        required_keys = {
            "project_id",
            "budget_usd",
            "total_spent",
            "remaining",
            "utilization_pct",
            "monthly_projection",
            "by_service",
            "by_agent",
            "optimization_hints",
            "entry_count",
        }
        assert required_keys.issubset(report.keys())
        assert report["entry_count"] == 1

    def test_empty_ledger_report(self):
        ledger = CostLedger(project_id="proj-empty", budget_usd=100.0)
        report = ledger.report()
        assert report["total_spent"] == 0.0
        assert report["remaining"] == 100.0
        assert report["monthly_projection"] == 0.0

    def test_optimization_hints_ecs_over_50(self):
        ledger = CostLedger(project_id="proj-hints", budget_usd=500.0)
        ledger.record("ECS", "RunTask", 55.0, "DevOps")
        hints = ledger.get_optimization_hints()
        assert any("ECS" in h for h in hints)

    def test_optimization_hints_rds_over_30(self):
        ledger = CostLedger(project_id="proj-hints2", budget_usd=500.0)
        ledger.record("RDS", "CreateInstance", 35.0, "DevOps")
        hints = ledger.get_optimization_hints()
        assert any("RDS" in h or "Aurora" in h for h in hints)

    def test_high_utilization_hint(self):
        ledger = CostLedger(project_id="proj-high", budget_usd=100.0)
        ledger.record("ECS", "RunTask", 95.0, "DevOps")
        hints = ledger.get_optimization_hints()
        assert any("utilization" in h.lower() or "pause" in h.lower() for h in hints)


class TestFloatingPointPrecision:
    """Production scenario: many small LLM API calls must not accumulate rounding errors."""

    def test_many_small_costs_precise(self):
        ledger = CostLedger(project_id="proj-precision", budget_usd=10.0)
        # Simulate 200 LLM API calls at $0.005 each
        for _ in range(200):
            ledger.record("Bedrock", "InvokeModel", 0.005, "CEO")
        assert ledger.total_spent() == pytest.approx(1.0, abs=0.01)
        assert ledger.remaining_budget() == pytest.approx(9.0, abs=0.01)
