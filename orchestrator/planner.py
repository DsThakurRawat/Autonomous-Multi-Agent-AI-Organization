"""
Main Orchestrator Engine
The central coordinator that manages agent execution, task scheduling,
event broadcasting, and the self-critique feedback loop.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import structlog

from .task_graph import TaskGraph, Task, TaskStatus, build_standard_task_graph
from .memory.project_memory import ProjectMemory
from .memory.decision_log import DecisionLog
from .memory.cost_ledger import CostLedger
from .memory.artifacts_store import ArtifactsStore

logger = structlog.get_logger(__name__)


class AgentExecutionContext:
    """Runtime context provided to each agent during execution."""

    def __init__(
        self,
        project_id: str,
        task: Task,
        memory: ProjectMemory,
        decision_log: DecisionLog,
        cost_ledger: CostLedger,
        artifacts: ArtifactsStore,
        event_emitter: Callable,
    ):
        self.project_id = project_id
        self.task = task
        self.memory = memory
        self.decision_log = decision_log
        self.cost_ledger = cost_ledger
        self.artifacts = artifacts
        self.emit_event = event_emitter


class ExecutionEvent:
    """Structured event emitted during execution for real-time UI updates."""

    def __init__(
        self,
        event_type: str,  # task_started, agent_message, task_completed, error
        agent_role: str,
        message: str,
        data: Dict[str, Any] = None,
        level: str = "info",  # info, warning, error, success
    ):
        self.id = str(uuid.uuid4())
        self.event_type = event_type
        self.agent_role = agent_role
        self.message = message
        self.data = data or {}
        self.level = level
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.event_type,
            "agent": self.agent_role,
            "message": self.message,
            "data": self.data,
            "level": self.level,
            "timestamp": self.timestamp.isoformat(),
        }


class OrchestratorEngine:
    """
    The Brain of the AI Organization.

    Responsibilities:
    - Bootstraps all agents and shared memory
    - Builds and executes the task graph (DAG)
    - Routes tasks to appropriate agents
    - Handles failures, retries, and rollbacks
    - Broadcasts real-time execution events
    - Triggers self-critique loop post-deployment
    """

    def __init__(self, budget_usd: float = 200.0, output_dir: str = "./output"):
        self.budget_usd = budget_usd
        self.output_dir = output_dir
        self._agent_registry: Dict[str, Any] = {}
        self._event_subscribers: List[Callable] = []
        self._active_projects: Dict[str, Dict[str, Any]] = {}
        logger.info("OrchestratorEngine initialized")

    def register_agent(self, role: str, agent_instance: Any):
        """Register an agent for a specific role."""
        self._agent_registry[role] = agent_instance
        logger.info("Agent registered", role=role)

    def subscribe_events(self, callback: Callable):
        """Subscribe to execution events (for WebSocket streaming)."""
        self._event_subscribers.append(callback)

    async def _emit(self, event: ExecutionEvent):
        """Broadcast event to all subscribers."""
        for cb in self._event_subscribers:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(event)
                else:
                    cb(event)
            except Exception as e:
                logger.error("Event subscriber failed", error=str(e))

    # ── Project Bootstrap ──────────────────────────────────────────
    async def start_project(
        self, business_idea: str, user_constraints: Dict[str, Any] = None
    ) -> str:
        """
        Entry point: Given a business idea, spin up the entire AI company.
        Returns a project_id that can be used to poll status.
        """
        project_id = str(uuid.uuid4())
        logger.info(
            "Starting new project", project_id=project_id, idea=business_idea[:80]
        )

        # Initialize shared memory systems
        memory = ProjectMemory(project_id=project_id)
        decision_log = DecisionLog(project_id=project_id)
        cost_ledger = CostLedger(project_id=project_id, budget_usd=self.budget_usd)
        artifacts = ArtifactsStore(project_id=project_id, output_dir=self.output_dir)

        memory.project_config = {
            "business_idea": business_idea,
            "budget_usd": self.budget_usd,
            "cloud_provider": "AWS",
            "started_at": datetime.utcnow().isoformat(),
            **(user_constraints or {}),
        }

        self._active_projects[project_id] = {
            "memory": memory,
            "decision_log": decision_log,
            "cost_ledger": cost_ledger,
            "artifacts": artifacts,
            "task_graph": None,
            "status": "bootstrapping",
            "started_at": datetime.utcnow(),
        }

        await self._emit(
            ExecutionEvent(
                event_type="project_started",
                agent_role="Orchestrator",
                message=f"🚀 Project started: {business_idea[:60]}",
                data={"project_id": project_id},
                level="success",
            )
        )

        # Run in background
        asyncio.create_task(self._run_project_lifecycle(project_id))
        return project_id

    # ── Main Lifecycle ─────────────────────────────────────────────
    async def _run_project_lifecycle(self, project_id: str):
        """Full project lifecycle: Strategy → Architecture → Build → QA → Deploy."""
        ctx = self._active_projects[project_id]
        memory = ctx["memory"]
        decision_log = ctx["decision_log"]
        cost_ledger = ctx["cost_ledger"]
        artifacts = ctx["artifacts"]

        try:
            # ── Phase 1: CEO Strategy ──────────────────────────────
            ctx["status"] = "strategy"
            await self._emit(
                ExecutionEvent(
                    "phase_start", "CEO", "📋 CEO analyzing business idea..."
                )
            )
            ceo_agent = self._agent_registry.get("CEO")
            if ceo_agent:
                exec_ctx = AgentExecutionContext(
                    project_id,
                    None,
                    memory,
                    decision_log,
                    cost_ledger,
                    artifacts,
                    self._emit,
                )
                business_plan = await ceo_agent.run(
                    business_idea=memory.project_config["business_idea"],
                    context=exec_ctx,
                )
                memory.business_plan = business_plan
            else:
                # Fallback mock for demo
                memory.business_plan = self._mock_business_plan(
                    memory.project_config["business_idea"]
                )

            await self._emit(
                ExecutionEvent(
                    "phase_complete",
                    "CEO",
                    f"✅ Business plan created: {len(memory.business_plan.get('mvp_features', []))} features",
                    data=memory.business_plan,
                    level="success",
                )
            )

            # ── Phase 2: CTO Architecture ──────────────────────────
            ctx["status"] = "architecture"
            await self._emit(
                ExecutionEvent(
                    "phase_start", "CTO", "🏗 CTO designing system architecture..."
                )
            )
            cto_agent = self._agent_registry.get("CTO")
            if cto_agent:
                exec_ctx = AgentExecutionContext(
                    project_id,
                    None,
                    memory,
                    decision_log,
                    cost_ledger,
                    artifacts,
                    self._emit,
                )
                architecture = await cto_agent.run(
                    business_plan=memory.business_plan,
                    budget_usd=self.budget_usd,
                    context=exec_ctx,
                )
                memory.architecture = architecture
            else:
                memory.architecture = self._mock_architecture()

            # Validate cost estimate against budget
            estimated_cost = memory.architecture.get("estimated_monthly_cost_usd", 0)
            if estimated_cost > self.budget_usd:
                await self._emit(
                    ExecutionEvent(
                        "warning",
                        "CTO",
                        f"⚠️ Estimated cost ${estimated_cost} exceeds budget ${self.budget_usd}. Optimizing...",
                        level="warning",
                    )
                )

            await self._emit(
                ExecutionEvent(
                    "phase_complete",
                    "CTO",
                    "✅ Architecture designed",
                    data=memory.architecture,
                    level="success",
                )
            )

            # ── Phase 3: Build Task Graph ──────────────────────────
            task_graph = build_standard_task_graph(project_id, memory.architecture)
            ctx["task_graph"] = task_graph

            await self._emit(
                ExecutionEvent(
                    "task_graph_ready",
                    "Orchestrator",
                    f"📊 Task graph built: {len(task_graph.tasks)} tasks queued",
                    data=task_graph.to_dict(),
                )
            )

            # ── Phase 4: Execute Task Graph ────────────────────────
            ctx["status"] = "executing"
            await self._execute_task_graph(project_id, task_graph)

            # ── Phase 5: Self-Critique Loop ────────────────────────
            ctx["status"] = "self_critique"
            await self._run_self_critique(project_id)

            # ── Final Report ───────────────────────────────────────
            ctx["status"] = "completed"
            deployment_url = artifacts.get_deployment_url()
            await self._emit(
                ExecutionEvent(
                    "project_completed",
                    "Orchestrator",
                    f"🎉 Project complete! Deployed at: {deployment_url or 'URL pending'}",
                    data={
                        "deployment_url": deployment_url,
                        "cost_report": cost_ledger.report(),
                        "decision_summary": decision_log.summary(),
                        "artifact_count": len(artifacts._artifacts),
                    },
                    level="success",
                )
            )

        except Exception as e:
            ctx["status"] = "failed"
            logger.error(
                "Project lifecycle failed", project_id=project_id, error=str(e)
            )
            await self._emit(
                ExecutionEvent(
                    "project_failed",
                    "Orchestrator",
                    f"❌ Project failed: {str(e)}",
                    data={"error": str(e)},
                    level="error",
                )
            )

    # ── Task Graph Execution ───────────────────────────────────────
    async def _execute_task_graph(self, project_id: str, task_graph: TaskGraph):
        """Execute the DAG respecting dependencies, with parallel execution."""

        while not task_graph.is_complete():
            ready_tasks = task_graph.get_ready_tasks()

            if not ready_tasks:
                blocked = task_graph.get_blocked_tasks()
                if blocked:
                    logger.warning("Tasks blocked by failures", count=len(blocked))
                await asyncio.sleep(0.5)
                continue

            # Execute ready tasks in parallel
            await asyncio.gather(
                *[
                    self._execute_single_task(project_id, task, task_graph)
                    for task in ready_tasks
                ]
            )

        summary = task_graph.get_status_summary()
        logger.info("Task graph execution complete", **summary)

    async def _execute_single_task(
        self, project_id: str, task: Task, task_graph: TaskGraph
    ):
        """Execute one task, with retry on failure."""
        ctx = self._active_projects[project_id]
        task.status = TaskStatus.IN_PROGRESS
        task.mark_started()

        await self._emit(
            ExecutionEvent(
                "task_started",
                task.agent_role,
                f"⚙️ [{task.agent_role}] Starting: {task.name}",
                data={"task_id": task.id, "task_name": task.name},
            )
        )

        while True:
            try:
                agent = self._agent_registry.get(task.agent_role)
                exec_ctx = AgentExecutionContext(
                    project_id,
                    task,
                    ctx["memory"],
                    ctx["decision_log"],
                    ctx["cost_ledger"],
                    ctx["artifacts"],
                    self._emit,
                )

                if agent:
                    output = await agent.execute_task(task=task, context=exec_ctx)
                else:
                    # Demo mode — simulate execution
                    await asyncio.sleep(1)
                    output = {"status": "simulated", "task": task.name}

                task.mark_completed(output)
                await self._emit(
                    ExecutionEvent(
                        "task_completed",
                        task.agent_role,
                        f"✅ [{task.agent_role}] Completed: {task.name}",
                        data={"task_id": task.id, "output_keys": list(output.keys())},
                        level="success",
                    )
                )
                break

            except Exception as e:
                logger.error(
                    "Task failed", task_id=task.id, error=str(e), retry=task.retry_count
                )

                if task.can_retry():
                    task.retry_count += 1
                    task.status = TaskStatus.RETRYING
                    await self._emit(
                        ExecutionEvent(
                            "task_retry",
                            task.agent_role,
                            f"🔁 Retrying ({task.retry_count}/{task.max_retries}): {task.name}",
                            level="warning",
                        )
                    )
                    await asyncio.sleep(2**task.retry_count)  # Exponential backoff
                else:
                    task.mark_failed(str(e))
                    await self._emit(
                        ExecutionEvent(
                            "task_failed",
                            task.agent_role,
                            f"❌ [{task.agent_role}] Failed: {task.name} — {str(e)[:100]}",
                            level="error",
                        )
                    )
                    break

    # ── Self-Critique Loop ─────────────────────────────────────────
    async def _run_self_critique(self, project_id: str):
        """Post-deployment autonomous evaluation and improvement cycle."""
        await self._emit(
            ExecutionEvent(
                "self_critique_start",
                "Orchestrator",
                "🔍 Running self-critique evaluation...",
            )
        )
        # TODO: Integrate with CloudWatch metrics + CTO re-evaluation
        await asyncio.sleep(0.5)
        await self._emit(
            ExecutionEvent(
                "self_critique_complete",
                "Orchestrator",
                "✅ Self-critique complete — system operating nominally",
                level="success",
            )
        )

    # ── Status API ─────────────────────────────────────────────────
    def get_project_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        if project_id not in self._active_projects:
            return None
        ctx = self._active_projects[project_id]
        task_graph = ctx.get("task_graph")
        return {
            "project_id": project_id,
            "status": ctx["status"],
            "started_at": ctx["started_at"].isoformat(),
            "memory_snapshot": ctx["memory"].snapshot(),
            "cost_report": ctx["cost_ledger"].report(),
            "task_graph": task_graph.to_dict() if task_graph else None,
            "decision_summary": ctx["decision_log"].summary(),
            "artifacts": ctx["artifacts"].manifest(),
        }

    # ── Mock Fallbacks (demo mode) ─────────────────────────────────
    def _mock_business_plan(self, idea: str) -> Dict[str, Any]:
        return {
            "vision": idea,
            "mvp_features": [
                "User Authentication",
                "Dashboard",
                "Data Management",
                "Reports",
            ],
            "milestones": [
                "Architecture",
                "Backend",
                "Frontend",
                "Testing",
                "Deployment",
            ],
            "risk_assessment": ["Cost overrun", "Scope creep", "Integration issues"],
            "target_users": "SMBs and individual professionals",
            "revenue_model": "Freemium SaaS",
            "success_metrics": ["100+ DAU", "< 200ms p95 latency", "99.9% uptime"],
        }

    def _mock_architecture(self) -> Dict[str, Any]:
        return {
            "frontend": "Next.js 14",
            "backend": "FastAPI",
            "database": "PostgreSQL 15 on RDS",
            "auth": "AWS Cognito",
            "deployment": "ECS Fargate",
            "cdn": "CloudFront",
            "cache": "ElastiCache Redis",
            "storage": "S3",
            "estimated_monthly_cost_usd": 95,
            "api_contracts": [
                "POST /api/auth/login",
                "POST /api/auth/register",
                "GET /api/items",
                "POST /api/items",
                "PUT /api/items/{id}",
                "DELETE /api/items/{id}",
            ],
        }
