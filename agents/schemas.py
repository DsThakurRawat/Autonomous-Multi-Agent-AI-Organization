"""
Agent Output Schemas — Pydantic V2 models for structured LLM output.

Instead of free-form ``json.loads(raw)`` with no validation, every agent
output is now parsed through a strict schema. If validation fails, the
error message is fed back into the LLM for a retry.

This module defines the SARANG Research Swarm schemas only.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── SARANG Research Schemas ───────────────────────────────────────────


class ResearchHypothesis(BaseModel):
    statement: str = Field(..., min_length=10)
    confidence: float = Field(..., ge=0, le=1)
    validation_method: str = ""


class MathRequirement(BaseModel):
    concept: str
    formalism: str  # e.g. "Linear Algebra", "Information Theory"
    critical_equations: list[str] = Field(default_factory=list)


class ImplementationGoal(BaseModel):
    module: str
    language: str = "python"
    requirements: list[str] = Field(default_factory=list)


class MathDeconstruction(BaseModel):
    """Structured output for the Math Architect agent."""
    core_theorems: list[str] = Field(default_factory=list)
    derivation_steps: list[str] = Field(default_factory=list)
    math_requirements: list[MathRequirement] = Field(default_factory=list)
    complexity_analysis: str = ""
    validation_status: str = "pending"


class ImplementationBlueprint(BaseModel):
    """Structured output for the Implementation Specialist agent."""
    modules: list[ImplementationGoal] = Field(default_factory=list)
    architecture_notes: str = ""
    code_snippets: list[str] = Field(default_factory=list)
    testing_strategy: str = ""


class DeconstructionPlan(BaseModel):
    """Structured output for the Research Intelligence agent."""

    summary: str = Field(..., min_length=10, description="Conversational summary of the research deconstruction")
    hypotheses: list[ResearchHypothesis] = Field(default_factory=list)
    math_requirements: list[MathRequirement] = Field(default_factory=list)
    implementation_goals: list[ImplementationGoal] = Field(default_factory=list)
    estimated_complexity: Literal["Low", "Medium", "High", "Critical"] = "Medium"
    novelty_score: float = Field(default=5.0, ge=0, le=10)
    reproducibility_risks: list[str] = Field(default_factory=list)
