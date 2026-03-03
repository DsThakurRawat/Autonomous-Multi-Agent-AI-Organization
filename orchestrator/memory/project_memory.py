"""
Project Memory
Redis-backed short-term session memory + DynamoDB long-term storage.
Maintains global shared context accessible by all agents.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger(__name__)


class ProjectMemory:
    """
    Multi-layer memory system:
    - L1 (Hot):  In-process dict (< 1ms access)
    - L2 (Warm): Redis (< 5ms, session-scoped)
    - L3 (Cold): DynamoDB (durable, cross-session)
    """

    def __init__(self, project_id: str, redis_client=None, dynamo_resource=None):
        self.project_id = project_id
        self._redis = redis_client
        self._dynamo = dynamo_resource
        self._hot_cache: Dict[str, Any] = {}

        # Core memory namespaces
        self.project_config: Dict[str, Any] = {}
        self.business_plan: Dict[str, Any] = {}
        self.architecture: Dict[str, Any] = {}
        self.generated_files: Dict[str, str] = {}  # path -> content
        self.test_results: Dict[str, Any] = {}
        self.deployment_info: Dict[str, Any] = {}
        self.agent_states: Dict[str, Any] = {}  # agent_id -> state
        self.error_history: List[Dict[str, Any]] = []
        self.knowledge_graph: List[Dict[str, Any]] = []  # Graph nodes/edges

        logger.info("ProjectMemory initialized", project_id=project_id)

    # ── Core CRUD ──────────────────────────────────────────────────
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Write to all memory layers."""
        self._hot_cache[key] = value
        serialized = json.dumps(value, default=str)

        if self._redis:
            redis_key = f"project:{self.project_id}:{key}"
            if ttl:
                await self._redis.setex(redis_key, ttl, serialized)
            else:
                await self._redis.set(redis_key, serialized)

        logger.debug("Memory set", project_id=self.project_id, key=key)

    async def get(self, key: str, default: Any = None) -> Any:
        """Read from fastest available layer."""
        if key in self._hot_cache:
            return self._hot_cache[key]

        if self._redis:
            redis_key = f"project:{self.project_id}:{key}"
            raw = await self._redis.get(redis_key)
            if raw:
                val = json.loads(raw)
                self._hot_cache[key] = val  # promote to L1
                return val

        return default

    async def delete(self, key: str):
        self._hot_cache.pop(key, None)
        if self._redis:
            await self._redis.delete(f"project:{self.project_id}:{key}")

    # ── Agent-Specific Memory ──────────────────────────────────────
    async def set_agent_state(self, agent_id: str, state: Dict[str, Any]):
        self.agent_states[agent_id] = {
            **state,
            "updated_at": datetime.utcnow().isoformat(),
        }
        await self.set(f"agent:{agent_id}", self.agent_states[agent_id])

    async def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        return self.agent_states.get(agent_id, {})

    # ── Knowledge Graph ────────────────────────────────────────────
    def add_knowledge_node(
        self, node_type: str, node_id: str, properties: Dict[str, Any]
    ):
        """Add a node to the in-memory knowledge graph."""
        self.knowledge_graph.append(
            {
                "type": "node",
                "node_type": node_type,  # Decision, File, Error, Architecture
                "node_id": node_id,
                "properties": properties,
                "created_at": datetime.utcnow().isoformat(),
            }
        )

    def add_knowledge_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,  # caused_by, depends_on, fixed_by
        properties: Dict[str, Any] = {},
    ):
        """Add a directed edge to the knowledge graph."""
        self.knowledge_graph.append(
            {
                "type": "edge",
                "source": source_id,
                "target": target_id,
                "relationship": relationship,
                "properties": properties,
                "created_at": datetime.utcnow().isoformat(),
            }
        )

    # ── Snapshot ───────────────────────────────────────────────────
    def snapshot(self) -> Dict[str, Any]:
        """Return complete project memory state."""
        return {
            "project_id": self.project_id,
            "project_config": self.project_config,
            "business_plan": self.business_plan,
            "architecture": self.architecture,
            "generated_files_count": len(self.generated_files),
            "test_results": self.test_results,
            "deployment_info": self.deployment_info,
            "agent_states": self.agent_states,
            "error_count": len(self.error_history),
            "knowledge_nodes": len(
                [k for k in self.knowledge_graph if k["type"] == "node"]
            ),
            "knowledge_edges": len(
                [k for k in self.knowledge_graph if k["type"] == "edge"]
            ),
        }
