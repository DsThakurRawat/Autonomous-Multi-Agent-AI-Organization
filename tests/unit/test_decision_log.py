"""
Production-Grade Tests — Decision Log (Audit Trail)
Real-life scenarios: immutable audit, confidence-based review flagging,
decision supersession, agent-level filtering, and timeline ordering.
"""

import pytest

from orchestrator.memory.decision_log import DecisionLog, DecisionRecord


class TestDecisionRecord:
    def test_serialisation_round_trip(self):
        rec = DecisionRecord(
            agent_role="CTO",
            decision_type="architecture",
            description="Selected PostgreSQL over MongoDB",
            rationale="Relational data model fits CRUD workloads",
            input_context={"business_plan": "e-commerce platform"},
            output={"database": "PostgreSQL", "backup": "automated"},
            confidence=0.92,
            alternatives_considered=["MongoDB", "DynamoDB"],
            tags=["database", "architecture"],
        )
        d = rec.to_dict()
        assert d["agent_role"] == "CTO"
        assert d["confidence"] == 0.92
        assert "MongoDB" in d["alternatives"]
        assert "database" in d["tags"]
        assert d["superseded_by"] is None

    def test_output_summary_truncates_long_values(self):
        rec = DecisionRecord(
            agent_role="Engineer_Backend",
            decision_type="code",
            description="Generated API code",
            rationale="FastAPI standard",
            input_context={},
            output={"code": "x" * 500},  # Very long value
        )
        d = rec.to_dict()
        assert len(d["output_summary"]["code"]) <= 200


class TestDecisionLogAuditTrail:
    """Production scenario: audit trail must be queryable by agent, type, and time."""

    @pytest.fixture
    def log(self):
        dl = DecisionLog(project_id="proj-audit")
        # Simulate a real project lifecycle
        dl.log(
            "CEO",
            "strategy",
            "Defined MVP features for SaaS platform",
            "Market analysis shows demand for AI-powered analytics",
            {"idea": "AI analytics SaaS"},
            {"mvp_features": ["dashboard", "alerts", "API"]},
            confidence=0.85,
            tags=["strategy", "mvp"],
        )
        dl.log(
            "CTO",
            "architecture",
            "Selected React + FastAPI + PostgreSQL stack",
            "Team expertise and cost optimization",
            {"mvp_features": ["dashboard", "alerts"]},
            {"frontend": "React", "backend": "FastAPI", "db": "PostgreSQL"},
            confidence=0.92,
            alternatives=["Vue + Django", "Next.js + Go"],
            tags=["architecture", "techstack"],
        )
        dl.log(
            "Engineer_Backend",
            "code",
            "Generated CRUD API endpoints",
            "Standard REST patterns for data models",
            {"architecture": {"backend": "FastAPI"}},
            {"endpoints": ["/users", "/projects", "/tasks"]},
            confidence=0.88,
        )
        dl.log(
            "QA",
            "testing",
            "Security scan passed with 0 critical findings",
            "Bandit + OWASP ZAP scan",
            {"code": "..."},
            {"critical": 0, "high": 1, "medium": 3},
            confidence=0.95,
            tags=["security", "qa"],
        )
        dl.log(
            "DevOps",
            "deploy",
            "Deployed to ECS with ALB and HTTPS",
            "Production-grade deployment with health checks",
            {"docker_image": "app:latest"},
            {"url": "https://app.example.com", "health": "ok"},
            confidence=0.90,
        )
        return dl

    def test_total_decisions(self, log):
        assert log.summary()["total_decisions"] == 5

    def test_filter_by_agent(self, log):
        cto_decisions = log.get_by_agent("CTO")
        assert len(cto_decisions) == 1
        assert cto_decisions[0]["decision_type"] == "architecture"

    def test_filter_by_type(self, log):
        code_decisions = log.get_by_type("code")
        assert len(code_decisions) == 1
        assert code_decisions[0]["agent_role"] == "Engineer_Backend"

    def test_timeline_is_chronologically_sorted(self, log):
        timeline = log.get_timeline()
        timestamps = [t["timestamp"] for t in timeline]
        assert timestamps == sorted(timestamps)

    def test_summary_counts_by_agent(self, log):
        summary = log.summary()
        assert summary["by_agent"]["CEO"] == 1
        assert summary["by_agent"]["CTO"] == 1
        assert summary["by_agent"]["DevOps"] == 1

    def test_summary_counts_by_type(self, log):
        summary = log.summary()
        assert summary["by_type"]["strategy"] == 1
        assert summary["by_type"]["architecture"] == 1
        assert summary["by_type"]["deploy"] == 1

    def test_avg_confidence(self, log):
        # (0.85 + 0.92 + 0.88 + 0.95 + 0.90) / 5 = 0.90
        assert log.summary()["avg_confidence"] == pytest.approx(0.90, abs=0.01)


class TestLowConfidenceReview:
    """Production scenario: decisions below 0.7 confidence should be flagged for human review."""

    def test_low_confidence_flagged(self):
        dl = DecisionLog(project_id="proj-review")
        dl.log(
            "CEO",
            "strategy",
            "Chose untested market segment",
            "Limited data available",
            {},
            {"segment": "quantum-computing-saas"},
            confidence=0.45,
        )
        dl.log(
            "CTO",
            "architecture",
            "Standard MERN stack",
            "Well-proven pattern",
            {},
            {},
            confidence=0.95,
        )
        flagged = dl.get_low_confidence_decisions(threshold=0.7)
        assert len(flagged) == 1
        assert flagged[0]["agent_role"] == "CEO"

    def test_superseded_not_flagged(self):
        dl = DecisionLog(project_id="proj-supersede")
        old_id = dl.log(
            "CEO", "strategy", "Bad plan", "Uncertain", {}, {}, confidence=0.3
        )
        new_id = dl.log(
            "CEO", "strategy", "Better plan", "More data", {}, {}, confidence=0.9
        )
        dl.supersede(old_id, new_id)
        flagged = dl.get_low_confidence_decisions(threshold=0.7)
        assert len(flagged) == 0  # Old one is superseded


class TestDecisionSupersession:
    """Production scenario: architecture pivots must supersede old decisions."""

    def test_supersede_marks_old_decision(self):
        dl = DecisionLog(project_id="proj-pivot")
        old_id = dl.log(
            "CTO",
            "architecture",
            "Selected MongoDB",
            "NoSQL for flexibility",
            {},
            {"db": "MongoDB"},
        )
        new_id = dl.log(
            "CTO",
            "architecture",
            "Switched to PostgreSQL",
            "Need ACID transactions for payments",
            {},
            {"db": "PostgreSQL"},
        )
        dl.supersede(old_id, new_id)

        timeline = dl.get_timeline()
        old_dec = next(d for d in timeline if d["id"] == old_id)
        assert old_dec["superseded_by"] == new_id

    def test_empty_log_summary(self):
        dl = DecisionLog(project_id="proj-empty")
        s = dl.summary()
        assert s["total_decisions"] == 0
        assert s["avg_confidence"] == 0.0
        assert s["low_confidence_count"] == 0
