"""
Agent Output Schemas — Pydantic V2 models for structured LLM output.

Instead of free-form ``json.loads(raw)`` with no validation, every agent
output is now parsed through a strict schema. If validation fails, the
error message is fed back into the LLM for a retry.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ── CEO Agent Schemas ────────────────────────────────────────────────


class FeaturePriority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class MVPFeature(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    priority: FeaturePriority
    description: str = Field(..., min_length=10)


class Milestone(BaseModel):
    phase: str
    duration_days: int = Field(..., ge=1, le=365)
    deliverables: list[str] = Field(..., min_length=1)


class Risk(BaseModel):
    risk: str
    impact: Literal["High", "Medium", "Low"]
    mitigation: str


class BusinessPlan(BaseModel):
    """Structured output for the CEO agent."""

    vision: str = Field(..., min_length=10, max_length=300)
    target_users: str = Field(..., min_length=5)
    problem_statement: str = Field(..., min_length=10)
    mvp_features: list[MVPFeature] = Field(..., min_length=1)
    milestones: list[Milestone] = Field(..., min_length=1)
    risk_assessment: list[Risk] = Field(default_factory=list)
    success_metrics: list[str] = Field(..., min_length=1)
    revenue_model: str
    estimated_users_year1: int = Field(default=100, ge=0)
    go_to_market: str = ""


# ── CTO Agent Schemas ────────────────────────────────────────────────


class TechChoice(BaseModel):
    framework: str
    language: str
    rationale: str = ""


class DatabaseColumn(BaseModel):
    name: str
    type: str
    constraints: str = ""


class DatabaseTable(BaseModel):
    table_name: str
    columns: list[DatabaseColumn] = Field(..., min_length=1)


class APIEndpoint(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str
    description: str = ""
    auth_required: bool = True


class SecurityConfig(BaseModel):
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    rate_limit_rpm: int = Field(default=60, ge=1)
    encryption_at_rest: bool = True
    waf_enabled: bool = False


class ServiceCost(BaseModel):
    service: str
    monthly_usd: float = Field(..., ge=0)


class Architecture(BaseModel):
    """Structured output for the CTO agent."""

    frontend: TechChoice
    backend: TechChoice
    database: TechChoice
    cache: TechChoice | None = None
    database_schema: list[DatabaseTable] = Field(default_factory=list)
    api_contracts: list[APIEndpoint] = Field(default_factory=list)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    estimated_monthly_cost_usd: float = Field(default=0.0, ge=0)
    cost_breakdown: list[ServiceCost] = Field(default_factory=list)
    scaling_policy: str = ""
    disaster_recovery: str = ""


# ── Finance Agent Schemas ────────────────────────────────────────────


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class BudgetAlert(BaseModel):
    severity: AlertSeverity
    message: str


class OptimizationRecommendation(BaseModel):
    category: str
    recommendation: str
    estimated_savings_usd: float = Field(default=0, ge=0)


class FinancialReport(BaseModel):
    """Structured output for the Finance agent."""

    total_budget_usd: float = Field(..., ge=0)
    total_spent_usd: float = Field(default=0, ge=0)
    remaining_usd: float = Field(default=0)
    utilization_pct: float = Field(default=0, ge=0, le=100)
    cost_breakdown: list[ServiceCost] = Field(default_factory=list)
    optimization_recommendations: list[OptimizationRecommendation] = Field(
        default_factory=list
    )
    alerts: list[BudgetAlert] = Field(default_factory=list)
    roi_analysis: str = ""


# ── QA Agent Schemas ─────────────────────────────────────────────────


class TestCase(BaseModel):
    name: str
    test_type: Literal["unit", "integration", "e2e", "security"]
    file_path: str
    description: str = ""


class QAReport(BaseModel):
    """Structured output for the QA agent."""

    tests_generated: list[TestCase] = Field(default_factory=list)
    total_tests: int = Field(default=0, ge=0)
    security_scan_passed: bool = True
    security_issues: list[str] = Field(default_factory=list)
    coverage_estimate_pct: float = Field(default=0, ge=0, le=100)
# ── SARANG Research Schemas ───────────────────────────────────────────


class ResearchHypothesis(BaseModel):
    statement: str = Field(..., min_length=10)
    confidence: float = Field(..., ge=0, le=1)
    validation_method: str


class MathRequirement(BaseModel):
    concept: str
    formalism: str  # e.g. "Linear Algebra", "Information Theory"
    critical_equations: list[str] = Field(default_factory=list)


class ImplementationGoal(BaseModel):
    module: str
    language: str = "python"
    requirements: list[str] = Field(..., min_length=1)


class DeconstructionPlan(BaseModel):
    """Structured output for the Lead Researcher agent."""

    summary: str = Field(..., min_length=50, description="Conversational summary of the research deconstruction")
    hypotheses: list[ResearchHypothesis] = Field(..., min_length=1)
    math_requirements: list[MathRequirement] = Field(..., min_length=1)
    implementation_goals: list[ImplementationGoal] = Field(..., min_length=1)
    estimated_complexity: Literal["Low", "Medium", "High", "Critical"]
    novelty_score: float = Field(..., ge=0, le=10)
    reproducibility_risks: list[str] = Field(default_factory=list)
