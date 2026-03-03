"""
MoE Scoring Engine
Computes composite routing scores using:
  - Cosine similarity between task embedding and expert capability vector
  - Load factor (inverse: prefer less-loaded experts)
  - Historical success rate
  - Relative cost efficiency
"""

import math
from typing import Dict, List, Tuple
import structlog

logger = structlog.get_logger(__name__)

# ── Scoring Weights ────────────────────────────────────────────────────────
WEIGHT_SIMILARITY = 0.40  # Capability match (most important)
WEIGHT_LOAD = 0.25  # Available capacity
WEIGHT_SUCCESS = 0.20  # Historical reliability
WEIGHT_COST = 0.15  # Cost efficiency

# Confidence threshold — below this, trigger ensemble mode
ENSEMBLE_THRESHOLD = 0.70


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.
    Returns value in [0.0, 1.0]. Returns 0.0 if either vector is zero.
    """
    if len(vec_a) != len(vec_b):
        min_len = min(len(vec_a), len(vec_b))
        vec_a = vec_a[:min_len]
        vec_b = vec_b[:min_len]

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a**2 for a in vec_a))
    mag_b = math.sqrt(sum(b**2 for b in vec_b))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return max(0.0, min(1.0, dot_product / (mag_a * mag_b)))


def task_type_to_vector(task_type: str, context: str = "") -> List[float]:
    """
    Convert a task type name to an 8-dimensional routing vector.
    Dimensions: [strategy, architecture, backend_code, frontend_code,
                 testing, devops, cost_optimization, security]
    """
    task_type_lower = task_type.lower()
    context_lower = context.lower() if context else ""

    # Base vector (all zeros)
    v = [0.0] * 8

    # Strategy dimension [0]
    if any(
        k in task_type_lower
        for k in ["strategy", "plan", "vision", "market", "mvp", "business"]
    ):
        v[0] = 0.9
    if any(k in context_lower for k in ["strategy", "market", "business"]):
        v[0] = max(v[0], 0.5)

    # Architecture dimension [1]
    if any(
        k in task_type_lower
        for k in ["architect", "design", "schema", "tech_stack", "system"]
    ):
        v[1] = 0.9
    if any(k in context_lower for k in ["architect", "api", "database"]):
        v[1] = max(v[1], 0.5)

    # Backend code dimension [2]
    if any(
        k in task_type_lower
        for k in ["backend", "api", "fastapi", "database", "orm", "auth"]
    ):
        v[2] = 0.9
    if any(k in context_lower for k in ["python", "fastapi", "sqlalchemy", "postgres"]):
        v[2] = max(v[2], 0.6)

    # Frontend code dimension [3]
    if any(
        k in task_type_lower
        for k in ["frontend", "ui", "react", "nextjs", "component", "page"]
    ):
        v[3] = 0.9
    if any(k in context_lower for k in ["typescript", "next.js", "tailwind", "css"]):
        v[3] = max(v[3], 0.6)

    # Testing dimension [4]
    if any(
        k in task_type_lower
        for k in ["test", "qa", "security_scan", "coverage", "validation"]
    ):
        v[4] = 0.9
    if any(k in context_lower for k in ["pytest", "unittest", "bandit", "security"]):
        v[4] = max(v[4], 0.6)

    # DevOps dimension [5]
    if any(
        k in task_type_lower
        for k in ["devops", "deploy", "terraform", "docker", "kubernetes", "ci_cd"]
    ):
        v[5] = 0.9
    if any(k in context_lower for k in ["aws", "ecs", "k8s", "helm", "infra"]):
        v[5] = max(v[5], 0.6)

    # Cost optimization dimension [6]
    if any(
        k in task_type_lower
        for k in ["cost", "finance", "budget", "price", "optimization"]
    ):
        v[6] = 0.9
    if any(k in context_lower for k in ["cost", "budget", "spend", "usd", "savings"]):
        v[6] = max(v[6], 0.5)

    # Security dimension [7]
    if any(
        k in task_type_lower for k in ["security", "iam", "auth", "permission", "audit"]
    ):
        v[7] = 0.9
    if any(
        k in context_lower
        for k in ["vulnerability", "injection", "xss", "csrf", "secret"]
    ):
        v[7] = max(v[7], 0.5)

    # If vector is all zeros (unknown task), use uniform distribution
    if sum(v) == 0:
        v = [0.125] * 8

    return v


def compute_expert_score(
    task_vector: List[float],
    expert_vector: List[float],
    load_factor: float,  # 0.0 (idle) → 1.0 (full)
    success_rate: float,  # 0.0 → 1.0
    avg_cost_usd: float,  # Per-task USD cost
    max_cost_usd: float = 0.10,  # Reference max for normalization
) -> Tuple[float, Dict[str, float]]:
    """
    Compute the composite routing score for an expert.

    Returns:
        (composite_score, score_breakdown_dict)
    """
    sim_score = cosine_similarity(task_vector, expert_vector)
    load_score = 1.0 - load_factor  # Prefer low load
    cost_factor = min(1.0, avg_cost_usd / max(max_cost_usd, 0.001))
    cost_score = 1.0 - cost_factor  # Prefer cheaper

    composite = (
        WEIGHT_SIMILARITY * sim_score
        + WEIGHT_LOAD * load_score
        + WEIGHT_SUCCESS * success_rate
        + WEIGHT_COST * cost_score
    )

    breakdown = {
        "similarity": round(sim_score, 4),
        "load": round(load_score, 4),
        "success_rate": round(success_rate, 4),
        "cost": round(cost_score, 4),
        "composite": round(composite, 4),
    }

    return composite, breakdown


def rank_experts(
    task_vector: List[float],
    experts: Dict[str, Dict],  # role → {vector, avg_cost, ...}
    stats: Dict[str, Dict],  # role → {load_factor, success_rate, avg_cost}
    exclude_overloaded: bool = True,
) -> List[Tuple[str, float, Dict]]:
    """
    Rank all experts by composite score for the given task.

    Returns:
        Sorted list of (role, score, breakdown) in descending order.
    """
    rankings = []

    for role, expert in experts.items():
        stat = stats.get(role, {})
        load_factor = stat.get("load_factor", 0.0)
        success_rate = stat.get("success_rate", 1.0)
        avg_cost = stat.get("avg_cost_usd", 0.05)

        # Skip overloaded experts (load ≥ 100%)
        if exclude_overloaded and load_factor >= 1.0:
            logger.debug("Expert overloaded, skipping", expert=role)
            continue

        score, breakdown = compute_expert_score(
            task_vector=task_vector,
            expert_vector=expert["vector"],
            load_factor=load_factor,
            success_rate=success_rate,
            avg_cost_usd=avg_cost,
        )

        rankings.append((role, score, breakdown))

    # Sort by composite score descending
    rankings.sort(key=lambda x: x[1], reverse=True)
    return rankings


def should_use_ensemble(top_score: float, second_score: float) -> bool:
    """
    Returns True if the top two experts are close enough to warrant ensemble.
    Triggered when: top_score < ENSEMBLE_THRESHOLD or gap < 0.1.
    """
    gap = top_score - second_score
    return top_score < ENSEMBLE_THRESHOLD or gap < 0.10
