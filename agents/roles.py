from enum import StrEnum


class AgentRole(StrEnum):
    """
    Explicitly typed roles for multi-agent system coordination.
    """
    CEO = "CEO"
    CTO = "CTO"
    ENGINEER_BACKEND = "Engineer_Backend"
    ENGINEER_FRONTEND = "Engineer_Frontend"
    QA = "QA"
    DEVOPS = "DevOps"
    FINANCE = "Finance"
    ORCHESTRATOR = "Orchestrator"

    def __str__(self) -> str:
        return self.value
