# Proximus Developer Hub — Technical Documentation

Welcome to the **Proximus** technical documentation hub. This document serves as the single source of truth for developers contributing to the Autonomous Multi-Agent AI Organization.

---

## 🏗️ High-Level System Architecture

Proximus is a polyglot system (Go, Python, Rust) that operates in two primary modes. It uses a specialized "Swarm" of AI experts to autonomously build software projects.

### 🔄 The Execution Lifecycle
Every Proximus project follows a structured 5-phase lifecycle:

1.  **CEO Strategy**: Analyzes the mission and generates a Product Requirements Document (PRD).
2.  **CTO Design**: Takes the PRD and designs the architecture, tech stack, and DB schema.
3.  **Task Graph (DAG)**: The orchestrator builds a Directed Acyclic Graph of parallelizable implementation tasks.
4.  **Expert Execution**: Backend, Frontend, QA, and DevOps agents work in parallel to build the project.
5.  **Self-Critique**: Agents evaluate their own output for quality and security before completion.

---

## 🐝 Hive: The Core Framework
Proximus is powered by the **Hive** framework, a production-grade multi-agent orchestration engine. Hive provides the fundamental abstractions for agent reasoning, tool use, and memory management.

### Key Hive Architectural Patterns
*   **Pydantic V2 Validation**: All internal state, message schemas, and tool parameters are strictly validated using Pydantic V2, offering 5x performance improvements over V1.
*   **SecretStr for Security**: Sensitive configuration fields (API keys, passwords) use Pydantic's `SecretStr` type to prevent accidental leakage in logs and serializations.
*   **Vector-Native Memory**: Agents utilize a Hive-managed semantic cache (Qdrant-backed) to reuse expensive LLM reasoning across project phases.

---

## 🛠️ Technology Stack (Modernized)

### Core Languages & Frameworks
*   **Go (v1.25.0)**: Powers the API Gateway, Enterprise Orchestrator, and the **Native MCP Server**.
*   **Python (v3.12)**: The logic engine for AI Agents, utilizing **Pydantic V2** and **OpenTelemetry**.
*   **Rust**: High-performance "Mixture of Experts" scoring and AST-based security validation (`security-check`).
*   **TypeScript / Next.js 15**: The real-time management dashboard.

### Infrastructure & Event Bus
*   **Apache Kafka**: The backbone for asynchronous agent-to-orchestrator communication.
*   **PostgreSQL 15**: Structured data persistence for projects, tasks, and tenants.
*   **Redis 7**: Distributed locks, **Budget Gating**, and WebSocket event routing.
*   **Qdrant**: High-performance vector database for **Semantic Cache** and long-term agent memory.

---

## 📂 Repository Map (Expanded)

### Core Logic
*   [`orchestrator/`](../orchestrator/): The central brain. Contains the Python `OrchestratorEngine` and Task Graph logic.
*   [`agents/`](../agents/): Specialized AI agent definitions built on the Hive `BaseAgent` class.
*   [`go-backend/`](../go-backend/): The Go microservices stack, including the **MCP Server** (`go-backend/cmd/mcp-server`).

### Specialized Services
*   [`security-check/`](../security-check/): Rust-based service for AST validation and PII scrubbing.
*   [`moe-scoring/`](../moe-scoring/): Rust engine for optimized agent/model routing.
*   [`tools/`](../tools/): Shared tools (File Editing, Web Search, Collaboration) used by agents via MCP or direct injection.

---

## 🏗️ Model Context Protocol (MCP) Integration
Proximus/Hive now supports the **Model Context Protocol (MCP)** for standardized tool execution.

*   **MCP Server (Go)**: Located in `go-backend/cmd/mcp-server`. It exposes local filesystem tools (`read_file`, `write_file`, `list_files`) to agents in a secure, sandboxed manner.
*   **Agent MCP Client**: Hive agents can dynamically connect to MCP servers to extend their capabilities without code changes.

---

## 📖 Technical Deep-Dives
...

### Interfaces
*   [`tui.py`](../tui.py): The primary interactive Terminal UI for Desktop Workbench.
*   [`dashboard/`](../dashboard/): The Next.js web application for SaaS project management.

---

## 🧠 LLM Configuration & Model Registry

By default, Proximus is optimized for **Amazon Nova** models on Bedrock, but it supports a provider-agnostic expert mesh.

| Agent Role | Default Provider | Default Model | Supported Alternatives |
| :--- | :--- | :--- | :--- |
| **CEO** | Bedrock | `amazon.nova-lite-v1:0` | OpenAI, Anthropic, Google |
| **CTO** | Bedrock | `amazon.nova-lite-v1:0` | OpenAI, Anthropic, Google |
| **Backend Eng** | Bedrock | `amazon.nova-lite-v1:0` | Anthropic, OpenAI |
| **Frontend Eng** | Bedrock | `amazon.nova-lite-v1:0` | Google (Gemini) |
| **QA** | Bedrock | `amazon.nova-lite-v1:0` | Anthropic, OpenAI |
| **DevOps** | Bedrock | `amazon.nova-lite-v1:0` | Anthropic |
| **Finance** | Bedrock | `amazon.nova-micro-v1:0` | OpenAI, Google |

### Per-User Key Management
Users can override these defaults in the Dashboard Settings. Resolution order:
1. User role preference -> User stored key.
2. User stored key for provider.
3. Server environment variables.

---

## 🗄️ Database & State Management

### Migrations (PostgreSQL)
Migrations are managed via `migrate` and run automatically in the local Docker stack.

| Migration | Purpose |
| :--- | :--- |
| `001_init` | Core schema (tenants, users, projects, tasks). |
| `002_user_llm_keys` | Encrypted key storage and agent preferences. |
| `003_user_auth` | Atomic Google OAuth login functions. |
| `004_projects_name` | Project naming and backfilling. |

---

## 🖥️ Dashboard Page Map (Enterprise SaaS)
Access the dashboard at `http://localhost:3000`.

| Page | Description |
| :--- | :--- |
| `/dashboard` | Main project list and active swarm health metrics. |
| `/projects/new` | Create a new project mission. |
| `/projects/:id` | Live agent feed, task DAG, and real-time logs. |
| `/settings` | LLM API key management and per-agent model selection. |
| `/finance` | Cost analysis and budget threshold configuration. |

---

## 🛡️ Production Resilience & Hardening

*   **Egress Proxy**: Restricts agent network access to a strict allowlist.
*   **Log Redactor**: High-performance Rust-based masking of API keys and PII.
*   **Memory Decay**: Background workers prune stale agent context to prevent data rot.
*   **Budget Alerts**: Real-time spending thresholds integrated into the Finance loop.
*   **Health Orchestrator**: Unified readiness checks on `/healthz` (Postgres, Redis, Kafka).

---

## 📖 Technical Deep-Dives

Explore the detailed component-level documentation for each subsystem:

### Core Subsystems
*   **[Agent Subsystem](./agents/README.md)**: BaseAgent, all 7 specialist agents, model registry, security hooks, and how to add new roles.
*   **[Orchestrator Engine](./orchestrator/README.md)**: OrchestratorEngine, Task Graph (DAG), Memory Subsystem (ProjectMemory, DecisionLog, CostLedger, ArtifactsStore, CheckpointManager).
*   **[Tool Subsystem](./tools/README.md)**: BaseTool, LocalFileEditTool, GitTool, BrowserTool, LinterTool, DockerSandboxTool, and extensibility guide.
*   **[Messaging & Kafka](./messaging/README.md)**: All 6 message schemas, topic architecture, producer/consumer clients, DLQ patterns, and the in-memory mock bus.

### Infrastructure & Security
*   **[Security & Rust Services](./infrastructure/README.md)**: AST validation, PII scrubbing, MoE scoring engine, Go backend services, and database migrations.
*   **[API Reference](./API_REFERENCE.md)**: Go Gateway REST routes and WebSocket event schema.

### Operational Guides
*   **[Desktop Mastery](./DESKTOP_MASTERY.md)**: Internals of the local standalone Python engine.
*   **[Enterprise SaaS Guide](./ENTERPRISE_SAS_GUIDE.md)**: Distributed orchestration with Go and Kafka.

---

## 🚀 Getting Started as a Contributor

1.  **Fork the repository** and clone it locally.
2.  **Read the [CONTRIBUTING.md](../CONTRIBUTING.md)** for coding standards and PR workflows.
3.  **Setup your environment** following the **[SETUP.md](../SETUP.md)** guide.
4.  **Run the test suite**:
    ```bash
    make test
    ```

---

## 🛡️ Security Policy
Please refer to **[SECURITY.md](../SECURITY.md)** for information on vulnerability reporting and our security-first design principles.
