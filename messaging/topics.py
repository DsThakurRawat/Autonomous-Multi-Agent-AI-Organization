"""
Kafka Topic Definitions - Single source of truth for all topic names.
"""


class KafkaTopics:
    """All Kafka topic names used in the AI Organization system."""

    # -- Static Topics matching Go Backend ----------------------------------
    TASKS = "ai-org-tasks"
    RESULTS = "ai-org-results"
    EVENTS = "ai-org-events"
    HEARTBEATS = "ai-org-heartbeats"

    @classmethod
    def task_topic_for_role(cls, role: str) -> str:
        """All roles pull from the single ai-org-tasks topic, filtering by agent_role."""
        return cls.TASKS

    @classmethod
    def results_topic(cls, project_id: str) -> str:
        """All results go to the single ai-org-results topic."""
        return cls.RESULTS

    @classmethod
    def events_topic(cls, project_id: str) -> str:
        """All events go to the single ai-org-events topic."""
        return cls.EVENTS

    @classmethod
    def heartbeat_topic(cls) -> str:
        return cls.HEARTBEATS

    @classmethod
    def all_task_topics(cls) -> list:
        return [cls.TASKS]

    # -- Dispatcher-friendly aliases ----------------------------------------
    @classmethod
    def agent_task_topic(cls, agent_role: str) -> str:
        return cls.TASKS

    @classmethod
    def task_result(cls, project_id: str) -> str:
        return cls.RESULTS

    @classmethod
    def project_events(cls, project_id: str) -> str:
        return cls.EVENTS

    # -- Topic Configurations ----------------------------------------------─
    # Used when creating topics programmatically
    TOPIC_CONFIGS = {
        TASKS: {"num_partitions": 12, "replication_factor": 3},
        RESULTS: {"num_partitions": 12, "replication_factor": 3},
        EVENTS: {"num_partitions": 6, "replication_factor": 3},
        HEARTBEATS: {"num_partitions": 3, "replication_factor": 3},
    }
