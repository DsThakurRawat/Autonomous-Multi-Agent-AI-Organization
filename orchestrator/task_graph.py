"""
Task Graph Engine
DAG-based task dependency system for multi-agent coordination.
Supports parallel execution, dependency resolution, and real-time status.
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum, StrEnum
from typing import Any
import uuid

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field
import structlog

from agents.roles import AgentRole

logger = structlog.get_logger(__name__)


class TaskStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class TaskPriority(int, Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class Task(BaseModel):
    """Represents a single unit of work in the task graph."""

    def __init__(self, **data: Any):
        super().__init__(**data)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    agent_role: str  # Which agent executes this
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: list[str] = []  # Task IDs this depends on
    input_data: dict[str, Any] = {}
    output_data: dict[str, Any] | None = None
    error_message: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    estimated_duration_seconds: int = 60
    tags: list[str] = []

    model_config = ConfigDict(use_enum_values=True)

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.completed_at:
            from typing import cast
            from datetime import datetime
            st = cast(datetime, self.started_at)
            ct = cast(datetime, self.completed_at)
            delta = ct - st
            return delta.total_seconds()
        return None

    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    def record_start(self):
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now(timezone.utc)

    def record_complete(self, output: Any = None):
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.output_data = output

    def record_fail(self, error: str):
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = error
        self.retry_count += 1

    def transition_to(self, new_status: TaskStatus):
        self.status = new_status
        if new_status == TaskStatus.IN_PROGRESS and not self.started_at:
            self.started_at = datetime.now(timezone.utc)
        elif new_status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            self.completed_at = datetime.now(timezone.utc)

# -- Task Graph ----------------------------------------------------

class TaskGraph(BaseModel):
    """A directed acyclic graph (DAG) of tasks representing a project plan."""
    project_id: str
    tasks: dict[str, Task] = Field(default_factory=dict)
    graph: Any = Field(default_factory=nx.DiGraph, exclude=True)

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data: Any):
        super().__init__(**data)
        self._lock = asyncio.Lock()
        self._completion_event = asyncio.Event()
        # Rebuild graph from tasks if loading from serialized state
        if not self.graph:
            self.graph = nx.DiGraph()
        for task in self.tasks.values():
            if task.id not in self.graph:
                self.graph.add_node(task.id, task=task)
            for dep_id in task.dependencies:
                self.graph.add_edge(dep_id, task.id)
        logger.info("TaskGraph initialized", project_id=self.project_id)

    def add_task(self, task: Task) -> str:
        """Add a task node to the DAG."""
        self.tasks[task.id] = task
        self.graph.add_node(task.id, task=task)

        # Add dependency edges
        for dep_id in task.dependencies:
            if dep_id not in self.tasks:
                # Ghost dependency handling
                pass
            else:
                self.graph.add_edge(dep_id, task.id)

        # Validate no cycles
        if not nx.is_directed_acyclic_graph(self.graph):
            self.graph.remove_node(task.id)
            self.tasks.pop(task.id, None)
            raise ValueError(
                f"Adding task '{task.name}' creates a cycle in the task graph"
            )

        logger.info("Task added to graph", task_id=task.id, task_name=task.name)
        return task.id

    def get_task(self, task_id: str) -> Task | None:
        return self.tasks.get(task_id)

    def get_ready_tasks(self) -> list[Task]:
        """Return tasks whose all dependencies are completed and are PENDING."""
        ready = []
        for task_id, task in self.tasks.items():
            if task.status != TaskStatus.PENDING:
                continue
            deps = list(self.graph.predecessors(task_id))
            all_deps_complete = all(
                self.tasks[dep].status == TaskStatus.COMPLETED for dep in deps
            )
            if all_deps_complete:
                ready.append(task)
        # Sort by priority
        return sorted(ready, key=lambda t: t.priority)

    def get_blocked_tasks(self) -> list[Task]:
        """Return tasks blocked by failed dependencies."""
        blocked = []
        for task_id, task in self.tasks.items():
            if task.status != TaskStatus.PENDING:
                continue
            deps = list(self.graph.predecessors(task_id))
            if any(self.tasks[dep].status == TaskStatus.FAILED for dep in deps):
                blocked.append(task)
        return blocked

    def is_complete(self) -> bool:
        return all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED)
            for t in self.tasks.values()
        )

    def is_successful(self) -> bool:
        return all(t.status == TaskStatus.COMPLETED for t in self.tasks.values())

    def get_critical_path(self) -> list[str]:
        """Returns the longest dependency chain (critical path), weighted by task duration."""
        try:
            # Issue #26: Use actual or estimated duration as the weight for correct diamond-dependency calc
            for _, data in self.graph.nodes(data=True):
                t: Task = data["task"]
                # networkx dag_longest_path uses the 'weight' attribute on edges.
                # For node-weights, we must assign it to the outgoing edges.
                weight = t.duration_seconds or t.estimated_duration_seconds or 60
                data["weight"] = weight

            for u, _v, d in self.graph.edges(data=True):
                # The weight of an edge u->v is the duration of u
                d["weight"] = self.graph.nodes[u].get("weight", 60)

            return nx.dag_longest_path(self.graph, weight="weight")
        except Exception as e:
            logger.warning("Failed to calculate critical path", error=str(e))
            return []

    def get_status_summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {str(s): 0 for s in TaskStatus}
        for task in self.tasks.values():
            status_key = str(task.status)
            counts[status_key] += 1
        total = len(self.tasks)
        completed = counts.get(str(TaskStatus.COMPLETED), 0)
        return {
            "total": total,
            "completed": completed,
            "failed": counts.get(str(TaskStatus.FAILED), 0),
            "in_progress": counts.get(str(TaskStatus.IN_PROGRESS), 0),
            "pending": counts.get(str(TaskStatus.PENDING), 0),
            "progress_pct": float(int(completed / total * 1000) / 10.0) if total > 0 else 0.0,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize the task graph for API/frontend consumption."""
        nodes = []
        edges = []

        for task_id, task in self.tasks.items():
            nodes.append(
                {
                    "id": task_id,
                    "name": task.name,
                    "agent_role": task.agent_role,
                    "status": task.status,
                    "priority": task.priority,
                    "duration": task.duration_seconds,
                    "error": task.error_message,
                }
            )

        for src, dst in self.graph.edges():
            edges.append({"source": src, "target": dst})

        return {
            "project_id": self.project_id,
            "nodes": nodes,
            "edges": edges,
            "summary": self.get_status_summary(),
            "critical_path": self.get_critical_path(),
        }


def build_standard_task_graph(
    project_id: str, architecture: dict[str, Any]
) -> TaskGraph:
    """
    Build the standard AI company task graph based on CTO architecture output.
    This is the default DAG for a full project lifecycle.
    """
    graph = TaskGraph(project_id=project_id)

    # -- Phase 0: Foundation ----------------------------------------─
    t_repo = Task(
        name="Setup Repository",
        description="Initialize Git repository with project structure",
        agent_role=AgentRole.DEVOPS,
        priority=TaskPriority.CRITICAL,
        estimated_duration_seconds=30,
        tags=["foundation"],
    )
    repo_id = graph.add_task(t_repo)

    # -- Phase 1: Backend --------------------------------------------
    t_backend = Task(
        name="Build Backend API",
        description="Generate FastAPI application with all endpoints and DB models",
        agent_role=AgentRole.ENGINEER_BACKEND,
        priority=TaskPriority.HIGH,
        dependencies=[repo_id],
        input_data={"architecture": architecture},
        estimated_duration_seconds=180,
        tags=["backend", "code"],
    )
    backend_id = graph.add_task(t_backend)

    # -- Phase 2: Frontend ------------------------------------------─
    t_frontend = Task(
        name="Build Frontend UI",
        description="Generate Next.js dashboard and forms connected to backend API",
        agent_role=AgentRole.ENGINEER_FRONTEND,
        priority=TaskPriority.HIGH,
        dependencies=[repo_id],
        input_data={"architecture": architecture},
        estimated_duration_seconds=180,
        tags=["frontend", "code"],
    )
    frontend_id = graph.add_task(t_frontend)

    # -- Phase 3: Testing --------------------------------------------
    t_tests = Task(
        name="Run QA Testing",
        description="Generate and run unit tests, security scan, API contract validation",
        agent_role=AgentRole.QA,
        priority=TaskPriority.HIGH,
        dependencies=[backend_id],
        estimated_duration_seconds=120,
        tags=["testing", "quality"],
    )
    tests_id = graph.add_task(t_tests)

    # -- Phase 4: Dockerize ------------------------------------------
    t_docker = Task(
        name="Dockerize Application",
        description="Create Dockerfiles for backend and frontend, build images",
        agent_role=AgentRole.DEVOPS,
        priority=TaskPriority.MEDIUM,
        dependencies=[backend_id, frontend_id],
        estimated_duration_seconds=90,
        tags=["docker", "infrastructure"],
    )
    docker_id = graph.add_task(t_docker)

    # -- Phase 5: AWS Infrastructure --------------------------------─
    t_infra = Task(
        name="Provision AWS Infrastructure",
        description="Run Terraform to create ECS, RDS, S3, ALB, and all required services",
        agent_role=AgentRole.DEVOPS,
        priority=TaskPriority.CRITICAL,
        dependencies=[tests_id, docker_id],
        estimated_duration_seconds=300,
        tags=["aws", "terraform", "infrastructure"],
    )
    infra_id = graph.add_task(t_infra)

    # -- Phase 6: Deploy --------------------------------------------─
    t_deploy = Task(
        name="Deploy to AWS ECS",
        description="Push images to ECR, deploy ECS services, configure ALB, setup HTTPS",
        agent_role=AgentRole.DEVOPS,
        priority=TaskPriority.CRITICAL,
        dependencies=[infra_id],
        estimated_duration_seconds=240,
        tags=["deployment", "aws"],
    )
    deploy_id = graph.add_task(t_deploy)

    # -- Phase 7: Finance Check --------------------------------------
    t_finance = Task(
        name="Cost Analysis",
        description="Analyze AWS costs, compare against budget, suggest optimizations",
        agent_role=AgentRole.FINANCE,
        priority=TaskPriority.MEDIUM,
        dependencies=[deploy_id],
        estimated_duration_seconds=60,
        tags=["cost", "finance"],
    )
    graph.add_task(t_finance)

    logger.info(
        "Standard task graph built", project_id=project_id, total_tasks=len(graph.tasks)
    )
    return graph


async def generate_dynamic_task_graph(
    project_id: str,
    business_plan: dict[str, Any],
    architecture: dict[str, Any],
    llm_client: Any,
    model_name: str,
    provider: str = "google",
) -> TaskGraph:
    """
    Goal-Driven Graph Generation.
    Uses Gemini to analyze the business plan and architecture and emit a dynamic JSON array of tasks.
    """
    import json

    prompt = f"""
You are the AI Orchestrator of an Autonomous Software Company.
You need to generate a precise Directed Acyclic Graph (DAG) of actionable tasks to build and deploy the following application.

Business Plan:
{json.dumps(business_plan, indent=2)}

Architecture:
{json.dumps(architecture, indent=2)}

Output strictly a JSON array of objects representing the tasks.
Requirements for each task:
- "id": a unique string (e.g. "task_backend_api")
- "name": a short text description
- "description": deep details of what to build
- "agent_role": MUST be exactly one of: ["Engineer_Backend", "Engineer_Frontend", "QA", "DevOps", "Finance"]
- "priority": integer 1 (critical) to 4 (low)
- "dependencies": an array of "id" strings representing tasks this one blocks on
- "estimated_duration_seconds": roughly 60-300

Make sure there are no dependency cycles!
Return raw JSON ONLY. No markdown blocks.
    """

    try:
        text = ""
        if provider == "google":
            response = await asyncio.to_thread(
                llm_client.models.generate_content, model=model_name, contents=prompt
            )
            text = response.text
        elif provider == "bedrock":
            # Nova models use the Bedrock Converse API format
            bedrock_messages = [{"role": "user", "content": [{"text": prompt}]}]
            response = await asyncio.to_thread(
                llm_client.converse,
                modelId=model_name,
                messages=bedrock_messages,
                inferenceConfig={"temperature": 0.1},
            )
            text = response["output"]["message"]["content"][0]["text"]

        text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)

        graph = TaskGraph(project_id=project_id)

        uuid_map = {}
        for t_spec in data:
            t = Task(
                name=t_spec.get("name", "Unknown Task"),
                description=t_spec.get("description", ""),
                agent_role=t_spec.get("agent_role", AgentRole.ENGINEER_BACKEND),
                priority=TaskPriority(t_spec.get("priority", 3)),
                estimated_duration_seconds=t_spec.get("estimated_duration_seconds", 60),
            )
            uuid_map[t_spec["id"]] = t.id
            t_spec["_obj"] = t

        for t_spec in data:
            obj = t_spec["_obj"]
            for dep in t_spec.get("dependencies", []):
                if dep in uuid_map:
                    obj.dependencies.append(uuid_map[dep])
            graph.add_task(obj)

        logger.info(
            "Dynamic task graph generated",
            project_id=project_id,
            total_tasks=len(graph.tasks),
        )
        return graph

    except Exception as e:
        logger.error(
            "Failed dynamic graph generation, falling back cleanly", error=str(e)
        )
        return build_standard_task_graph(project_id, architecture)
