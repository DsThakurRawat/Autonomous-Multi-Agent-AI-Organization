"""
Unit Tests — AgentEvent & Pydantic Output Schemas

Tests the new typed event system and structured output schemas
introduced by the hardening plan.
"""

import json

import pytest
from pydantic import ValidationError

from agents.events import AgentEvent
from agents.schemas import (
    Architecture,
    BusinessPlan,
    FeaturePriority,
    FinancialReport,
    MVPFeature,
    Milestone,
    QAReport,
    Risk,
    TechChoice,
)


# ── AgentEvent Tests ─────────────────────────────────────────────────


class TestAgentEvent:
    def test_construction_defaults(self):
        e = AgentEvent(
            event_type="thinking",
            agent_role="CEO",
            message="Analyzing...",
        )
        assert e.level == "info"
        assert e.data == {}
        assert e.timestamp  # Should be auto-populated

    def test_to_dict_structure(self):
        e = AgentEvent(
            event_type="tool_call",
            agent_role="Backend",
            message="Running file_edit",
            level="success",
            data={"file": "app.py"},
        )
        d = e.to_dict()
        assert d["type"] == "tool_call"
        assert d["agent"] == "Backend"
        assert d["message"] == "Running file_edit"
        assert d["level"] == "success"
        assert d["data"]["file"] == "app.py"
        assert "timestamp" in d

    def test_custom_data_preserved(self):
        e = AgentEvent(
            event_type="artifact",
            agent_role="DevOps",
            message="Generated Terraform",
            data={"files": ["main.tf", "vpc.tf"], "line_count": 450},
        )
        assert len(e.data["files"]) == 2
        assert e.data["line_count"] == 450


# ── BusinessPlan Schema Tests ────────────────────────────────────────


class TestBusinessPlanSchema:
    def test_valid_plan(self):
        plan = BusinessPlan(
            vision="AI-powered meal planning for busy professionals",
            target_users="Working professionals aged 25-45",
            problem_statement="Meal planning takes 2+ hours per week",
            mvp_features=[
                MVPFeature(
                    name="Quiz",
                    priority=FeaturePriority.P0,
                    description="Onboarding quiz for preferences",
                )
            ],
            milestones=[
                Milestone(
                    phase="MVP", duration_days=30, deliverables=["Core API"]
                )
            ],
            success_metrics=["500 users in month 1"],
            revenue_model="Freemium SaaS",
        )
        assert plan.vision.startswith("AI-powered")
        assert plan.mvp_features[0].priority == FeaturePriority.P0

    def test_vision_too_short(self):
        with pytest.raises(ValidationError, match="vision"):
            BusinessPlan(
                vision="Short",
                target_users="Users",
                problem_statement="Problem desc",
                mvp_features=[
                    MVPFeature(
                        name="F1",
                        priority="P0",
                        description="A feature description",
                    )
                ],
                milestones=[
                    Milestone(phase="M1", duration_days=1, deliverables=["X"])
                ],
                success_metrics=["Metric"],
                revenue_model="Free",
            )

    def test_empty_features_rejected(self):
        with pytest.raises(ValidationError):
            BusinessPlan(
                vision="A long enough vision statement for validation",
                target_users="Users",
                problem_statement="Problem desc here",
                mvp_features=[],  # Empty!
                milestones=[
                    Milestone(phase="M1", duration_days=1, deliverables=["X"])
                ],
                success_metrics=["Metric"],
                revenue_model="Free",
            )

    def test_invalid_priority_rejected(self):
        with pytest.raises(ValidationError):
            MVPFeature(
                name="Feature",
                priority="P9",  # Invalid
                description="A feature description",
            )

    def test_milestone_zero_days_rejected(self):
        with pytest.raises(ValidationError):
            Milestone(phase="M1", duration_days=0, deliverables=["X"])

    def test_risk_invalid_impact_rejected(self):
        with pytest.raises(ValidationError):
            Risk(risk="Something", impact="Extreme", mitigation="Fix it")

    def test_serialization_roundtrip(self):
        plan = BusinessPlan(
            vision="A platform to automate code reviews",
            target_users="Engineering teams",
            problem_statement="Code reviews take too long and miss bugs",
            mvp_features=[
                MVPFeature(
                    name="Auto Review",
                    priority="P0",
                    description="Automated code review suggestions",
                )
            ],
            milestones=[
                Milestone(phase="Alpha", duration_days=14, deliverables=["MVP"])
            ],
            success_metrics=["100 reviews/day"],
            revenue_model="Per-seat SaaS",
            estimated_users_year1=1000,
        )
        # Serialize and deserialize
        data = plan.model_dump()
        reconstructed = BusinessPlan.model_validate(data)
        assert reconstructed.vision == plan.vision
        assert reconstructed.estimated_users_year1 == 1000


# ── Architecture Schema Tests ────────────────────────────────────────


class TestArchitectureSchema:
    def test_valid_architecture(self):
        arch = Architecture(
            frontend=TechChoice(
                framework="Next.js 14",
                language="TypeScript",
                rationale="SSR for SEO",
            ),
            backend=TechChoice(
                framework="FastAPI",
                language="Python 3.12",
                rationale="Async I/O",
            ),
            database=TechChoice(
                framework="PostgreSQL 15",
                language="SQL",
                rationale="ACID for transactions",
            ),
            estimated_monthly_cost_usd=85.0,
        )
        assert arch.frontend.framework == "Next.js 14"
        assert arch.estimated_monthly_cost_usd == 85.0
        assert arch.security.encryption_at_rest is True  # Default

    def test_negative_cost_rejected(self):
        with pytest.raises(ValidationError):
            Architecture(
                frontend=TechChoice(framework="X", language="Y"),
                backend=TechChoice(framework="X", language="Y"),
                database=TechChoice(framework="X", language="Y"),
                estimated_monthly_cost_usd=-10.0,
            )

    def test_optional_cache(self):
        arch = Architecture(
            frontend=TechChoice(framework="React", language="JS"),
            backend=TechChoice(framework="Express", language="JS"),
            database=TechChoice(framework="MongoDB", language="JS"),
            cache=None,
        )
        assert arch.cache is None


# ── Financial Report Schema Tests ────────────────────────────────────


class TestFinancialReportSchema:
    def test_valid_report(self):
        report = FinancialReport(
            total_budget_usd=200.0,
            total_spent_usd=85.0,
            remaining_usd=115.0,
            utilization_pct=42.5,
        )
        assert report.remaining_usd == 115.0

    def test_utilization_over_100_rejected(self):
        with pytest.raises(ValidationError):
            FinancialReport(
                total_budget_usd=200.0,
                utilization_pct=150.0,  # Over 100
            )


# ── QA Report Schema Tests ──────────────────────────────────────────


class TestQAReportSchema:
    def test_valid_report(self):
        report = QAReport(
            total_tests=15,
            coverage_estimate_pct=78.5,
            security_scan_passed=True,
        )
        assert report.total_tests == 15

    def test_coverage_bounds(self):
        with pytest.raises(ValidationError):
            QAReport(coverage_estimate_pct=-5.0)
        with pytest.raises(ValidationError):
            QAReport(coverage_estimate_pct=105.0)
