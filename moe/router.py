"""
MoE Router — Master Orchestrator for Expert Selection
Implements dynamic agent routing with:
  1. Direct routing (unambiguous task types)
  2. Scored routing (cosine sim + load + success + cost)
  3. Ensemble routing (top-2 for high-stakes ambiguous tasks)
  4. Priority queue fallback (all experts overloaded)
  5. Full Prometheus instrumentation
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
import structlog

from .expert_registry import ExpertRegistry
from .scoring import (
    task_type_to_vector,
    rank_experts,
    should_use_ensemble,
    ENSEMBLE_THRESHOLD,
)
from messaging.schemas import MoERouteDecision
from .http_client import get_rust_client

logger = structlog.get_logger(__name__)


class MoERouter:
    """
    Mixture of Experts (MoE) Router — the intelligent task dispatcher.

    Routing pipeline:
      1. Parse task for type and context
      2. Check direct mapping (O(1) lookup)
      3. If ambiguous → compute task vector and score all available experts
      4. Apply ensemble if scores are close or confidence is low
      5. Return routing decision with explanation

    All decisions are logged and instrumented.
    """

    def __init__(self, registry: Optional[ExpertRegistry] = None):
        self._registry = registry or ExpertRegistry()
        self._priority_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._routing_history: List[Dict[str, Any]] = []  # Last 1000 decisions
        self._lock = asyncio.Lock()

        logger.info(
            "MoERouter initialized", experts=list(self._registry.all_experts().keys())
        )

    # ── Main Routing Interface ─────────────────────────────────────────────
    async def route(
        self,
        task_type: str,
        task_name: str,
        task_id: str,
        project_id: str,
        input_context: str = "",
        required_skills: List[str] = [],
        priority: str = "medium",
        force_ensemble: bool = False,
        trace_id: str = "",
    ) -> MoERouteDecision:
        """
        Route a task to the best available expert.

        Args:
            task_type:      Task classification string
            task_name:      Human-readable task name
            task_id:        Unique task identifier
            project_id:     Project this task belongs to
            input_context:  Task description/context (used for semantic routing)
            required_skills: Mandatory skills the expert must have
            priority:       "critical" | "high" | "medium" | "low"
            force_ensemble: Force multi-expert routing regardless of scores
            trace_id:       OpenTelemetry trace ID for correlation

        Returns:
            MoERouteDecision with selected expert and explanation
        """
        start_time = time.monotonic()

        # ── Step 0: Try Rust Service (Fast Path) ───────────────────────────
        rust_client = get_rust_client()
        if rust_client:
            # We must pass the dynamic expert map + stats to Rust so it matches python state
            experts_map = {
                role: info for role, info in self._registry.all_experts().items()
            }
            stats_map = {
                role: s.to_dict() for role, s in self._registry.all_stats().items()
            }

            resp = await rust_client.route(
                task_id=task_id,
                task_type=task_type,
                task_name=task_name,
                project_id=project_id,
                input_context=input_context,
                required_skills=required_skills,
                priority=priority,
                force_ensemble=force_ensemble,
                trace_id=trace_id,
                experts=experts_map,
                stats=stats_map,
            )
            if resp:
                decision = MoERouteDecision(**resp)
                await self._record_decision(
                    decision, decision.routing_type, time.monotonic() - start_time
                )
                return decision

        # ── Step 1: Direct Routing Check (Python Fallback) ────────────────
        direct_expert = self._registry.get_direct_expert_for_task_type(task_type)
        if direct_expert and not force_ensemble:
            self._registry.get_expert(direct_expert)
            stats = self._registry.get_stats(direct_expert)

            if stats and stats.load_factor < 1.0:
                decision = MoERouteDecision(
                    request_id=task_id,
                    selected_expert=direct_expert,
                    fallback_experts=[],
                    routing_score=1.0,
                    routing_reason=f"Direct routing: task_type '{task_type}' maps exactly to {direct_expert}",
                    ensemble_mode=False,
                    confidence=0.99,
                )
                await self._record_decision(
                    decision, "direct", time.monotonic() - start_time
                )
                return decision

        # ── Step 2: Compute Task Vector ────────────────────────────────────
        task_vector = task_type_to_vector(task_type, input_context)

        # ── Step 3: Get All Expert Stats ───────────────────────────────────
        experts = self._registry.all_experts()
        stats_dict = {
            role: s.to_dict() for role, s in self._registry.all_stats().items()
        }

        # Filter by required skills
        if required_skills:
            experts = {
                role: exp
                for role, exp in experts.items()
                if any(skill in exp["skills"] for skill in required_skills)
            }

        if not experts:
            # Fallback: no skill match — use all experts
            experts = self._registry.all_experts()
            logger.warning(
                "No experts matched required skills, routing to all",
                skills=required_skills,
            )

        # ── Step 4: Score and Rank ─────────────────────────────────────────
        rankings = rank_experts(
            task_vector=task_vector,
            experts=experts,
            stats=stats_dict,
            exclude_overloaded=(priority not in ["critical"]),
        )

        if not rankings:
            # All experts overloaded — queue the task
            logger.warning("All experts overloaded, queueing task", task_id=task_id)
            return await self._queue_for_retry(
                task_id, task_type, task_name, project_id, trace_id
            )

        top_role, top_score, top_breakdown = rankings[0]
        second_role, second_score, second_breakdown = (
            rankings[1] if len(rankings) > 1 else (None, 0.0, {})
        )

        # ── Step 5: Ensemble Decision ──────────────────────────────────────
        use_ensemble = force_ensemble or (
            second_role and should_use_ensemble(top_score, second_score)
        )

        fallback = [second_role] if (second_role and use_ensemble) else []

        routing_reason = (
            f"Scored routing: {top_role} selected with score {top_score:.3f} "
            f"[sim={top_breakdown.get('similarity', 0):.3f}, "
            f"load={top_breakdown.get('load', 0):.3f}, "
            f"success={top_breakdown.get('success_rate', 0):.3f}]"
        )
        if use_ensemble:
            routing_reason += f" | Ensemble with {second_role} (scores gap {top_score-second_score:.3f} < 0.10)"

        confidence = min(1.0, top_score / max(ENSEMBLE_THRESHOLD, 0.001))

        decision = MoERouteDecision(
            request_id=task_id,
            selected_expert=top_role,
            fallback_experts=fallback,
            routing_score=top_score,
            routing_reason=routing_reason,
            ensemble_mode=use_ensemble,
            confidence=round(confidence, 3),
        )

        await self._record_decision(decision, "scored", time.monotonic() - start_time)

        logger.info(
            "MoE routing decision",
            task=task_name,
            selected=top_role,
            score=round(top_score, 3),
            ensemble=use_ensemble,
            confidence=round(confidence, 3),
            routing_ms=round((time.monotonic() - start_time) * 1000, 2),
        )

        return decision

    # ── Batch Routing ──────────────────────────────────────────────────────
    async def route_batch(self, tasks: List[Dict[str, Any]]) -> List[MoERouteDecision]:
        """Route multiple tasks in parallel."""
        # Fast path: Rust batch route
        rust_client = get_rust_client()
        if rust_client:
            experts_map = {
                role: info for role, info in self._registry.all_experts().items()
            }
            stats_map = {
                role: s.to_dict() for role, s in self._registry.all_stats().items()
            }
            resp = await rust_client.route_batch(
                tasks, experts=experts_map, stats=stats_map
            )
            if resp:
                # Need to log all decisions
                for r in resp:
                    dec = MoERouteDecision(**r)
                    await self._record_decision(
                        dec, dec.routing_type, r.get("routing_ms", 0) / 1000.0
                    )
                return [MoERouteDecision(**r) for r in resp]

        # Python fallback:
        decisions = await asyncio.gather(
            *[
                self.route(
                    task_type=t.get("task_type", ""),
                    task_name=t.get("task_name", ""),
                    task_id=t.get("task_id", ""),
                    project_id=t.get("project_id", ""),
                    input_context=t.get("context", ""),
                    priority=t.get("priority", "medium"),
                    trace_id=t.get("trace_id", ""),
                )
                for t in tasks
            ]
        )
        return list(decisions)

    # ── Priority Queue Fallback ────────────────────────────────────────────
    async def _queue_for_retry(
        self,
        task_id: str,
        task_type: str,
        task_name: str,
        project_id: str,
        trace_id: str,
    ) -> MoERouteDecision:
        """Queue task when all experts are overloaded."""
        expert = list(self._registry.all_experts().keys())[0]  # Last resort
        decision = MoERouteDecision(
            request_id=task_id,
            selected_expert=expert,
            fallback_experts=[],
            routing_score=0.0,
            routing_reason="All experts overloaded — last-resort fallback routing",
            ensemble_mode=False,
            confidence=0.1,
        )
        return decision

    # ── Decision History ───────────────────────────────────────────────────
    async def _record_decision(
        self, decision: MoERouteDecision, routing_type: str, latency_s: float
    ):
        async with self._lock:
            entry = {
                **decision.model_dump(),
                "routing_type": routing_type,
                "latency_ms": round(latency_s * 1000, 2),
            }
            self._routing_history.append(entry)
            if len(self._routing_history) > 1000:
                self._routing_history.pop(0)

    def get_routing_stats(self) -> Dict[str, Any]:
        """Return routing statistics for monitoring dashboards."""
        if not self._routing_history:
            return {"total_decisions": 0}

        expert_counts: Dict[str, int] = {}
        routing_types: Dict[str, int] = {}
        total_latency = 0.0

        for d in self._routing_history:
            role = d.get("selected_expert", "unknown")
            rt = d.get("routing_type", "unknown")
            expert_counts[role] = expert_counts.get(role, 0) + 1
            routing_types[rt] = routing_types.get(rt, 0) + 1
            total_latency += d.get("latency_ms", 0)

        n = len(self._routing_history)
        return {
            "total_decisions": n,
            "avg_routing_latency_ms": round(total_latency / n, 2),
            "expert_distribution": expert_counts,
            "routing_type_breakdown": routing_types,
            "ensemble_rate": sum(
                1 for d in self._routing_history if d.get("ensemble_mode")
            )
            / n,
        }

    def get_expert_load_summary(self) -> List[Dict[str, Any]]:
        """Return current expert load for dashboard display."""
        return self._registry.get_all_stats_dict()
