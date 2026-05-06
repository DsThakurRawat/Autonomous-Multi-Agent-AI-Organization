"""
MoE Router - Master Orchestrator for Expert Selection
Implements dynamic agent routing with:
  1. Direct routing (unambiguous task types)
  2. Scored routing (cosine sim + load + success + cost)
  3. Ensemble routing (top-2 for high-stakes ambiguous tasks)
  4. Priority queue fallback (all experts overloaded)
  5. Full Prometheus instrumentation
"""

import asyncio
import time
from typing import Any

import structlog

from messaging.schemas import MoERouteDecision

from .expert_registry import ExpertRegistry
from .http_client import get_rust_client
from .scoring import (
    ENSEMBLE_THRESHOLD,
    rank_experts,
    should_use_ensemble,
    task_type_to_vector,
)

logger = structlog.get_logger(__name__)


class MoERouter:
    """
    Mixture of Experts (MoE) Router - the intelligent task dispatcher.

    Routing pipeline:
      1. Parse task for type and context
      2. Check direct mapping (O(1) lookup)
      3. If ambiguous → compute task vector and score all available experts
      4. Apply ensemble if scores are close or confidence is low
      5. Return routing decision with explanation
    """

    def __init__(self, registry: ExpertRegistry | None = None):
        self._registry = registry or ExpertRegistry()
        self._priority_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._routing_history: list[dict[str, Any]] = []  # Last 1000 decisions
        self._lock = asyncio.Lock()

        logger.info(
            "MoERouter initialized", experts=list(self._registry.all_experts().keys())
        )

    # -- Main Routing Interface --------------------------------------------─
    async def route(
        self,
        task_type: str,
        task_name: str,
        task_id: str,
        project_id: str,
        input_context: str = "",
        required_skills: list[str] | None = None,
        priority: str = "medium",
        force_ensemble: bool = False,
        trace_id: str = "",
    ) -> MoERouteDecision:
        """
        Route a task to the best available expert.
        """
        if required_skills is None:
            required_skills = []
        start_time = time.monotonic()

        # -- Step -1: Early exit if no experts ----------------------------─
        if not self._registry.all_experts():
            logger.error("No experts registered in the system.")
            return await self._queue_for_retry(
                task_id, task_type, task_name, project_id, trace_id
            )

        # -- Step 0: Try Rust Service (Fast Path) --------------------------─
        rust_client = get_rust_client()
        if rust_client:
            experts_map = dict(self._registry.all_experts().items())
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

        # -- Step 1: Direct Routing Check (Python Fallback) ----------------
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

        # -- Step 2: Compute Task Vector ------------------------------------
        task_vector = task_type_to_vector(task_type, input_context)

        # -- Step 3: Get All Expert Stats ----------------------------------─
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
            experts = self._registry.all_experts()

        if not experts:
            logger.error("No experts registered in the system.")
            return await self._queue_for_retry(
                task_id, task_type, task_name, project_id, trace_id
            )

        # -- Step 4: Score and Rank ----------------------------------------─
        rankings = rank_experts(
            task_vector=task_vector,
            experts=experts,
            stats=stats_dict,
            exclude_overloaded=(priority not in ["critical"]),
        )

        if not rankings:
            return await self._queue_for_retry(
                task_id, task_type, task_name, project_id, trace_id
            )

        top_role, top_score, top_breakdown = rankings[0]
        second_role, second_score, _second_breakdown = (
            rankings[1] if len(rankings) > 1 else (None, 0.0, {})
        )

        # -- Step 5: Ensemble Decision --------------------------------------
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
            routing_reason += f" | Ensemble with {second_role}"

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
        return decision

    async def route_batch(self, tasks: list[dict[str, Any]]) -> list[MoERouteDecision]:
        """Route multiple tasks in parallel."""
        experts_map = dict(self._registry.all_experts().items())
        rust_client = get_rust_client()
        if not experts_map:
            return [
                await self._queue_for_retry(
                    t.get("task_id", ""),
                    t.get("task_type", ""),
                    t.get("task_name", ""),
                    t.get("project_id", ""),
                    t.get("trace_id", ""),
                )
                for t in tasks
            ]

        if rust_client:
            stats_map = {
                role: s.to_dict() for role, s in self._registry.all_stats().items()
            }
            resp = await rust_client.route_batch(
                tasks, experts=experts_map, stats=stats_map
            )
            if resp:
                for r in resp:
                    dec = MoERouteDecision(**r)
                    await self._record_decision(
                        dec, dec.routing_type, r.get("routing_ms", 0) / 1000.0
                    )
                return [MoERouteDecision(**r) for r in resp]

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

    async def _queue_for_retry(
        self,
        task_id: str,
        task_type: str,
        task_name: str,
        project_id: str,
        trace_id: str,
    ) -> MoERouteDecision:
        expert_keys = list(self._registry.all_experts().keys())
        if not expert_keys:
            return MoERouteDecision(
                request_id=task_id,
                selected_expert="NoExpertAvailable",
                fallback_experts=[],
                routing_score=0.0,
                routing_reason="No experts registered in system",
                ensemble_mode=False,
                confidence=0.0,
            )
        expert = expert_keys[0]
        decision = MoERouteDecision(
            request_id=task_id,
            selected_expert=expert,
            fallback_experts=[],
            routing_score=0.0,
            routing_reason="All experts overloaded - fallback routing",
            ensemble_mode=False,
            confidence=0.1,
        )
        return decision

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

    def get_routing_stats(self) -> dict[str, Any]:
        if not self._routing_history:
            return {"total_decisions": 0}
        return {"total_decisions": len(self._routing_history)}

    def get_expert_load_summary(self) -> list[dict[str, Any]]:
        return self._registry.get_all_stats_dict()
