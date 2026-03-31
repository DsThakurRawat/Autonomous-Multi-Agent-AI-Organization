"""
Mixture of Experts (MoE) Router - Expert Registry
Maintains capability vectors and real-time load/performance stats
for all registered agent experts.
"""

import asyncio
from datetime import  datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# -- Expert Capability Vectors ----------------------------------------------
# Each vector represents the agent's specialization across task dimensions.
# Dimensions: [strategy, architecture, backend_code, frontend_code,
#              testing, devops, cost_optimization, security]
EXPERT_CAPABILITY_VECTORS = {
    "CEO": {
        "vector": [0.95, 0.40, 0.10, 0.10, 0.10, 0.10, 0.60, 0.40],
        "skills": [
            "strategy",
            "vision",
            "planning",
            "risk_assessment",
            "product_definition",
        ],
        "description": "Business strategy, MVP scoping, market analysis",
        "preferred_models": ["gpt-4-turbo-preview", "claude-3-sonnet-20240229"],
        "avg_task_tokens": 3000,
        "max_concurrent": 3,
    },
    "CTO": {
        "vector": [0.50, 0.95, 0.50, 0.30, 0.40, 0.60, 0.70, 0.80],
        "skills": [
            "architecture",
            "tech_stack",
            "database_design",
            "api_contracts",
            "cost_estimation",
        ],
        "description": "Technical architecture, stack decisions, cost modeling",
        "preferred_models": ["gpt-4-turbo-preview", "claude-3-sonnet-20240229"],
        "avg_task_tokens": 4000,
        "max_concurrent": 2,
    },
    "Engineer_Backend": {
        "vector": [0.10, 0.40, 0.95, 0.10, 0.60, 0.40, 0.30, 0.50],
        "skills": [
            "python",
            "fastapi",
            "sqlalchemy",
            "postgresql",
            "redis",
            "authentication",
            "api_design",
        ],
        "description": "FastAPI backend, DB models, CRUD APIs, auth",
        "preferred_models": ["claude-3-sonnet-20240229", "gpt-4-turbo-preview"],
        "avg_task_tokens": 8000,
        "max_concurrent": 5,
    },
    "Engineer_Frontend": {
        "vector": [0.10, 0.20, 0.10, 0.95, 0.50, 0.10, 0.20, 0.30],
        "skills": [
            "react",
            "nextjs",
            "typescript",
            "tailwind",
            "ui_design",
            "api_integration",
        ],
        "description": "Next.js frontend, React components, mobile-responsive",
        "preferred_models": ["claude-3-sonnet-20240229", "gpt-4-turbo-preview"],
        "avg_task_tokens": 6000,
        "max_concurrent": 3,
    },
    "QA": {
        "vector": [0.20, 0.30, 0.60, 0.60, 0.95, 0.30, 0.20, 0.75],
        "skills": [
            "testing",
            "pytest",
            "security_scanning",
            "coverage",
            "api_testing",
            "validation",
        ],
        "description": "Unit/integration tests, security scan, coverage analysis",
        "preferred_models": ["gpt-4-turbo-preview", "claude-3-sonnet-20240229"],
        "avg_task_tokens": 5000,
        "max_concurrent": 4,
    },
    "DevOps": {
        "vector": [0.20, 0.60, 0.50, 0.20, 0.40, 0.95, 0.60, 0.70],
        "skills": [
            "terraform",
            "aws",
            "docker",
            "kubernetes",
            "cicd",
            "monitoring",
            "deployment",
        ],
        "description": "IaC, Docker, ECS/EKS deployment, CI/CD pipelines",
        "preferred_models": ["gpt-4-turbo-preview", "claude-3-sonnet-20240229"],
        "avg_task_tokens": 7000,
        "max_concurrent": 2,
    },
    "Finance": {
        "vector": [0.40, 0.30, 0.10, 0.10, 0.10, 0.20, 0.95, 0.20],
        "skills": [
            "cost_tracking",
            "budget_governance",
            "aws_pricing",
            "optimization",
            "reporting",
        ],
        "description": "Cost analysis, budget monitoring, optimization recommendations",
        "preferred_models": ["gpt-4-turbo-preview"],
        "avg_task_tokens": 2000,
        "max_concurrent": 2,
    },
}

# Task type → expert mapping (direct routing)
TASK_TYPE_TO_EXPERT = {
    "strategy": "CEO",
    "vision": "CEO",
    "business_plan": "CEO",
    "architecture": "CTO",
    "tech_stack": "CTO",
    "database_design": "CTO",
    "backend_code": "Engineer_Backend",
    "api_generation": "Engineer_Backend",
    "frontend_code": "Engineer_Frontend",
    "ui_generation": "Engineer_Frontend",
    "testing": "QA",
    "security_scan": "QA",
    "deployment": "DevOps",
    "terraform": "DevOps",
    "infrastructure": "DevOps",
    "cost_analysis": "Finance",
    "budget_review": "Finance",
}


class ExpertStats:
    """Runtime statistics for an expert agent - updated in real-time."""

    def __init__(self, role: str, max_concurrent: int):
        self.role = role
        self.max_concurrent = max_concurrent
        self.current_load: int = 0  # active tasks
        self.total_tasks: int = 0
        self.failed_tasks: int = 0
        self.total_cost_usd: float = 0.0
        self.total_tokens: int = 0
        self.latencies_ms: list[float] = []  # rolling window (last 100)
        self.last_active: datetime | None = None
        self._lock = asyncio.Lock()

    async def record_start(self):
        async with self._lock:
            self.current_load += 1
            self.total_tasks += 1
            self.last_active = datetime.now(timezone.utc)

    async def record_complete(self, latency_ms: float, cost_usd: float, tokens: int):
        async with self._lock:
            self.current_load = max(0, self.current_load - 1)
            self.total_cost_usd += cost_usd
            self.total_tokens += tokens
            self.latencies_ms.append(latency_ms)
            if len(self.latencies_ms) > 100:  # Rolling window
                self.latencies_ms.pop(0)

    async def record_failure(self, latency_ms: float):
        async with self._lock:
            self.current_load = max(0, self.current_load - 1)
            self.failed_tasks += 1
            self.latencies_ms.append(latency_ms)

    @property
    def load_factor(self) -> float:
        """0.0 (idle) → 1.0 (at capacity)."""
        if self.max_concurrent == 0:
            return 1.0
        return min(1.0, self.current_load / self.max_concurrent)

    @property
    def success_rate(self) -> float:
        """Historical success rate (0.0 → 1.0). Defaults to 1.0 if no history."""
        if self.total_tasks == 0:
            return 1.0
        successful = self.total_tasks - self.failed_tasks
        return successful / self.total_tasks

    @property
    def p95_latency_ms(self) -> float:
        """P95 latency from rolling window."""
        if not self.latencies_ms:
            return 30_000.0  # Assume 30s as cold-start estimate
        sorted_lat = sorted(self.latencies_ms)
        idx = max(0, int(len(sorted_lat) * 0.95) - 1)
        return sorted_lat[idx]

    @property
    def avg_cost_per_task_usd(self) -> float:
        if self.total_tasks == 0:
            return 0.05  # Estimated default
        return self.total_cost_usd / self.total_tasks

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "current_load": self.current_load,
            "max_concurrent": self.max_concurrent,
            "load_factor": round(self.load_factor, 3),
            "success_rate": round(self.success_rate, 3),
            "p95_latency_ms": round(self.p95_latency_ms, 1),
            "total_tasks": self.total_tasks,
            "failed_tasks": self.failed_tasks,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "avg_cost_usd": round(self.avg_cost_per_task_usd, 4),
            "last_active": self.last_active.isoformat() if self.last_active else None,
        }


class ExpertRegistry:
    """
    Central registry of all expert agents with their capability vectors
    and live runtime statistics.
    Thread-safe, singleton per process.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._experts: dict[str, dict[str, Any]] = {}
        self._stats: dict[str, ExpertStats] = {}
        self._initialized = True

        # Register all built-in experts
        for role, config in EXPERT_CAPABILITY_VECTORS.items():
            self._register(role, config)

        logger.info("ExpertRegistry initialized", expert_count=len(self._experts))

    def _register(self, role: str, config: dict[str, Any]):
        self._experts[role] = {
            "role": role,
            "vector": config["vector"],
            "skills": config["skills"],
            "description": config["description"],
            "preferred_models": config["preferred_models"],
            "avg_task_tokens": config["avg_task_tokens"],
            "max_concurrent": config["max_concurrent"],
        }
        self._stats[role] = ExpertStats(
            role=role, max_concurrent=config["max_concurrent"]
        )

    def get_expert(self, role: str) -> dict[str, Any] | None:
        return self._experts.get(role)

    def get_stats(self, role: str) -> ExpertStats | None:
        return self._stats.get(role)

    def all_experts(self) -> dict[str, dict[str, Any]]:
        return dict(self._experts)

    def all_stats(self) -> dict[str, ExpertStats]:
        return dict(self._stats)

    async def record_task_start(self, role: str):
        if role in self._stats:
            await self._stats[role].record_start()

    async def record_task_complete(
        self, role: str, latency_ms: float, cost_usd: float, tokens: int
    ):
        if role in self._stats:
            await self._stats[role].record_complete(latency_ms, cost_usd, tokens)

    async def record_task_failure(self, role: str, latency_ms: float):
        if role in self._stats:
            await self._stats[role].record_failure(latency_ms)

    def get_direct_expert_for_task_type(self, task_type: str) -> str | None:
        """Return direct expert if task type maps unambiguously."""
        return TASK_TYPE_TO_EXPERT.get(task_type.lower())

    def get_all_stats_dict(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._stats.values()]
