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
    provider: str  # "openai" | "anthropic" | "google" | "bedrock"
    model: str  # exact model ID for the provider's API


# ── Agent Defaults ────────────────────────────────────────────────────────────
# NOTE: As part of the Amazon Nova integration, all default models are routed
# to Amazon Bedrock. The system orchestration still supports switching individual
# agents to Google (Gemini), Anthropic (Claude), or OpenAI (GPT) for specific tasks
# dynamically via the settings API.
AGENT_MODEL_DEFAULTS: dict[str, ModelConfig] = {
    # CEO — Strategic reasoning, structured JSON output
    "CEO": {
        "provider": "bedrock",
        "model": "amazon.nova-lite-v1:0",
    },
    # CTO / Architect — Long-context system design and research
    "CTO": {
        "provider": "bedrock",
        "model": "amazon.nova-lite-v1:0",
    },
    # Engineer (Backend) — Real, runnable code with minimal hallucinations
    "Engineer_Backend": {
        "provider": "bedrock",
        "model": "amazon.nova-lite-v1:0",
    },
    # Engineer (Frontend) — UI generation and React components
    "Engineer_Frontend": {
        "provider": "bedrock",
        "model": "amazon.nova-lite-v1:0",
    },
    # QA — Test writing and bug analysis
    "QA": {
        "provider": "bedrock",
        "model": "amazon.nova-lite-v1:0",
    },
    # DevOps — YAML, Dockerfile, CI/CD generation
    "DevOps": {
        "provider": "bedrock",
        "model": "amazon.nova-lite-v1:0",
    },
    # Finance — Cost analysis and budget reporting
    "Finance": {
        "provider": "bedrock",
        "model": "amazon.nova-micro-v1:0",
    },
}


def get_default(agent_role: str) -> ModelConfig:
    """Return the default ModelConfig for a given agent role.
    Falls back to Gemini for unknown roles.
    """
    return AGENT_MODEL_DEFAULTS.get(
        agent_role,
        {"provider": "bedrock", "model": "amazon.nova-lite-v1:0"},
    )
