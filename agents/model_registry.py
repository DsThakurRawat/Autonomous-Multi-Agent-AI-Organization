"""
Model Registry — Single source of truth for default agent model preferences.

When a user has NOT configured custom agent preferences in the Settings panel,
the Go Orchestrator falls back to these defaults when building the Kafka TaskMessage.
The Python AgentMicroservice also reads these as its ultimate fallback if the
Kafka payload arrives without an llm_config block.

Prompting strategy references (for improving system prompts per agent):
  CEO  / GPT-4o:      https://platform.openai.com/docs/guides/prompt-engineering
  CTO  / Gemini:      https://ai.google.dev/gemini-api/docs/prompting-strategies
  Eng  / Claude:      https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview
"""

from typing import TypedDict


class ModelConfig(TypedDict):
    provider: str  # "openai" | "anthropic" | "google"
    model: str  # exact model ID for the provider's API


# ── Agent Defaults ────────────────────────────────────────────────────────────
AGENT_MODEL_DEFAULTS: dict[str, ModelConfig] = {
    # CEO — Strategic reasoning, structured JSON output
    # Best at: business plans, cost decisions, structured role delegation
    "CEO": {
        "provider": "openai",
        "model": "gpt-4o",
    },
    # CTO / Architect — Long-context system design
    # Best at: architecture blueprints, tech stack decisions, diagramming
    "CTO": {
        "provider": "google",
        "model": "gemini-2.5-pro-exp-03-25",
    },
    # Engineer (Backend) — Real, runnable code with minimal hallucinations
    # Best at: Python/Go APIs, database schemas, tests
    "Engineer_Backend": {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-latest",
    },
    # Engineer (Frontend) — React/TypeScript/CSS code generation
    # Best at: component code, responsive layouts
    "Engineer_Frontend": {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-latest",
    },
    # QA — Test writing and bug analysis
    # Best at: test coverage, edge case detection, bug reports
    "QA": {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-latest",
    },
    # DevOps — YAML, Dockerfile, CI/CD generation
    # Use cheaper Haiku — tasks are mechanical and don't need full Sonnet
    "DevOps": {
        "provider": "anthropic",
        "model": "claude-3-haiku-20240307",
    },
    # Finance — Cost analysis and budget reporting
    # Use gpt-4o-mini — numeric reasoning at lower cost
    "Finance": {
        "provider": "openai",
        "model": "gpt-4o-mini",
    },
}


def get_default(agent_role: str) -> ModelConfig:
    """Return the default ModelConfig for a given agent role.
    Falls back to Gemini for unknown roles.
    """
    return AGENT_MODEL_DEFAULTS.get(
        agent_role,
        {"provider": "google", "model": "gemini-2.5-pro-exp-03-25"},
    )
