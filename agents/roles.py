from enum import StrEnum


class AgentRole(StrEnum):
    """
    Explicitly typed research roles for the SARANG multi-agent system.
    """

    LEAD_RESEARCHER = "Lead_Researcher"
    MATH_ARCHITECT = "Math_Architect"
    IMPLEMENTATION_SPECIALIST = "Implementation_Specialist"
    VISUAL_INSIGHTS = "Visual_Insights"
    REPRODUCIBILITY_ENGINEER = "Reproducibility_Engineer"
    PEER_REVIEWER = "Peer_Reviewer"
    COMPUTE_MONITOR = "Compute_Monitor"
    ORCHESTRATOR = "Orchestrator"

    def __str__(self) -> str:
        return self.value
