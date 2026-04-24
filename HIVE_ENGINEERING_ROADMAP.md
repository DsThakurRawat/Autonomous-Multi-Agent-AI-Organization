# Hive Engineering Roadmap — Core Framework Mastery

This document serves as the master guide for engineering excellence within the **Hive Framework**. It maps the theoretical architectural layers to their specific implementations in this repository.

---

## 🏗️ Layer 1: Python Runtime & Dependency Management
The foundation of Hive is a strict, isolated Python environment.
*   **Key Tool**: `uv` (high-performance Python package installer).
*   **Key Files**:
    - `pyproject.toml`: Project metadata, dependencies, and build configuration.
    - `requirements.txt`: Frozen dependencies for production consistency.
    - `Dockerfile.agent`: The base container definition for Hive agents.

---

## 🛡️ Layer 2: Data Validation & Configuration (Pydantic V2)
Hive leverages Pydantic V2 for high-speed validation and secure configuration.
*   **Key Patterns**:
    - **SecretStr**: Used for sensitive keys (API keys, DB passwords).
    - **BaseSettings**: Automatic environment variable loading.
*   **Key Files**:
    - `agents/base_agent.py`: Initial budget gating and secret retrieval logic.
    - `messaging/kafka_client.py`: Pydantic models for message serialization.

---

## 🧠 Layer 3: Agent Core & Reasoning (Hive Engine)
The reasoning loop that powers all Hive agents.
*   **Abstractions**: `BaseAgent`, `SemanticCache`, `Self-Critique`.
*   **Key Files**:
    - `agents/base_agent.py`: The `BaseAgent` abstract class.
    - `agents/memory.py`: Qdrant-backed `SemanticCache` implementation.
    - `agents/agent_service.py`: The entry point for agents as Kafka consumers.

---

## 🛠️ Layer 4: Standardized Tooling (MCP)
The Model Context Protocol (MCP) provides a bridge between the agent and the host.
*   **Key Files**:
    - `go-backend/cmd/mcp-server/`: Go implementation of the MCP server.
    - `go-backend/internal/mcp/server.go`: Tool definitions (`read_file`, `write_file`).

---

## 📡 Layer 5: Asynchronous Messaging (Kafka)
The event bus that coordinates the entire Hive swarm.
*   **Topics**: `ai-org-tasks`, `ai-org-results`, `ai-org-events`, `ai-org-heartbeats`.
*   **Key Files**:
    - `messaging/kafka_client.py`: Unified producer/consumer clients.
    - `go-backend/internal/shared/kafka/`: Go implementation of Kafka logic.

---

## 🛡️ Layer 6: Security & AST Validation
Rust-based services that protect the system from malicious AI-generated code.
*   **Key Files**:
    - `security-check/`: Rust source code for log scrubbing and Python AST validation.
    - `agents/base_agent.py`: `_scrub_text` and `_validate_code_safety` hooks.

---

## 📊 Layer 7: Observability & Budget Governance
Real-time tracking of agent health, costs, and traces.
*   **Key Files**:
    - `observability/`: OpenTelemetry tracing and metrics configuration.
    - `agents/base_agent.py`: OTEL setup and Redis-backed budget gating.
    - `go-backend/cmd/health-monitor/`: Central health status service.

---

## 🚀 Mastery Path
To become a Hive Framework Master, follow this sequence:
1.  **Level 1**: Understand the `BaseAgent` and how to implement a new agent role.
2.  **Level 2**: Master Pydantic V2 schemas and serialization patterns in `messaging/`.
3.  **Level 3**: Extend the `mcp-server` with new custom tools in Go.
4.  **Level 4**: Implement advanced reflection/self-fix loops in the agent reasoning layer.
5.  **Level 5**: Optimize the MoE scoring engine in Rust for custom model routing.
