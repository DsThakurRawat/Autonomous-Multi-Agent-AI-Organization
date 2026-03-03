"""
Kafka Topic Definitions — Single source of truth for all topic names.
"""


class KafkaTopics:
    """All Kafka topic names used in the AI Organization system."""

    # ── Task Dispatch Topics (per agent role) ──────────────────────────────
    TASKS_CEO = "ai-org.tasks.ceo"
    TASKS_CTO = "ai-org.tasks.cto"
    TASKS_ENGINEER_BACKEND = "ai-org.tasks.engineer_backend"
    TASKS_ENGINEER_FRONTEND = "ai-org.tasks.engineer_frontend"
    TASKS_QA = "ai-org.tasks.qa"
    TASKS_DEVOPS = "ai-org.tasks.devops"
    TASKS_FINANCE = "ai-org.tasks.finance"

    # ── Result Topics (per project) ────────────────────────────────────────
    RESULTS_PREFIX = "ai-org.results"  # ai-org.results.{project_id}

    # ── Event Topics (lifecycle events for UI streaming) ──────────────────
    EVENTS_PREFIX = "ai-org.events"  # ai-org.events.{project_id}

    # ── Error Bus ─────────────────────────────────────────────────────────
    ERRORS = "ai-org.errors"

    # ── Metrics Bus ───────────────────────────────────────────────────────
    METRICS = "ai-org.metrics"

    # ── MoE Router ────────────────────────────────────────────────────────
    MOE_ROUTE_REQUEST = "ai-org.moe.route_request"
    MOE_ROUTE_DECISION = "ai-org.moe.route_decision"

    # ── Audit Log ─────────────────────────────────────────────────────────
    AUDIT = "ai-org.audit"

    # ── Role to Topic Mapping ─────────────────────────────────────────────
    ROLE_TO_TOPIC = {
        "CEO": TASKS_CEO,
        "CTO": TASKS_CTO,
        "Engineer_Backend": TASKS_ENGINEER_BACKEND,
        "Engineer_Frontend": TASKS_ENGINEER_FRONTEND,
        "QA": TASKS_QA,
        "DevOps": TASKS_DEVOPS,
        "Finance": TASKS_FINANCE,
    }

    @classmethod
    def task_topic_for_role(cls, role: str) -> str:
        """Get the Kafka task topic for a given agent role."""
        topic = cls.ROLE_TO_TOPIC.get(role)
        if not topic:
            raise ValueError(f"No Kafka topic registered for agent role: {role}")
        return topic

    @classmethod
    def results_topic(cls, project_id: str) -> str:
        return f"{cls.RESULTS_PREFIX}.{project_id}"

    @classmethod
    def events_topic(cls, project_id: str) -> str:
        return f"{cls.EVENTS_PREFIX}.{project_id}"

    @classmethod
    def all_task_topics(cls) -> list:
        return list(cls.ROLE_TO_TOPIC.values())

    # ── Topic Configurations ───────────────────────────────────────────────
    # Used when creating topics programmatically
    TOPIC_CONFIGS = {
        TASKS_CEO: {"num_partitions": 6, "replication_factor": 3},
        TASKS_CTO: {"num_partitions": 6, "replication_factor": 3},
        TASKS_ENGINEER_BACKEND: {"num_partitions": 12, "replication_factor": 3},
        TASKS_ENGINEER_FRONTEND: {"num_partitions": 6, "replication_factor": 3},
        TASKS_QA: {"num_partitions": 9, "replication_factor": 3},
        TASKS_DEVOPS: {"num_partitions": 6, "replication_factor": 3},
        TASKS_FINANCE: {"num_partitions": 3, "replication_factor": 3},
        ERRORS: {"num_partitions": 3, "replication_factor": 3},
        METRICS: {"num_partitions": 6, "replication_factor": 3},
        AUDIT: {"num_partitions": 3, "replication_factor": 3},
    }
