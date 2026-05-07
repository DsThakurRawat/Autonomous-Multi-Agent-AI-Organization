"""
Model Registry - Single source of truth for default agent model preferences.

All SARANG research agents default to Gemini for local development.
The system supports switching agents to other providers dynamically
via the settings API.
"""

from typing import TypedDict


class ModelConfig(TypedDict):
    provider: str  # "google" | "openai" | "anthropic" | "bedrock"
    model: str     # exact model ID for the provider's API


# -- Agent Defaults --------------------------------------------------------
# Local development defaults to Google Gemini (free tier).
# Production deployments can override per-agent via environment or settings API.
AGENT_MODEL_DEFAULTS: dict[str, ModelConfig] = {
    "Research_Intelligence": {
        "provider": "google",
        "model": "gemini-2.5-flash",
    },
    "Math_Architect": {
        "provider": "google",
        "model": "gemini-2.5-flash",
    },
    "Implementation_Specialist": {
        "provider": "google",
        "model": "gemini-2.5-flash",
    },
    "Peer_Reviewer": {
        "provider": "google",
        "model": "gemini-2.5-flash",
    },
    "Reproducibility_Engineer": {
        "provider": "google",
        "model": "gemini-2.5-flash",
    },
    "Visual_Insights": {
        "provider": "google",
        "model": "gemini-2.5-flash",
    },
    "Compute_Monitor": {
        "provider": "google",
        "model": "gemini-2.5-flash",
    },
}


def get_default(agent_role: str) -> ModelConfig:
    """Return the default ModelConfig for a given agent role.
    Falls back to Gemini for unknown roles.
    """
    return AGENT_MODEL_DEFAULTS.get(
        agent_role,
        {"provider": "google", "model": "gemini-2.0-flash"},
    )
