# System Architecture — Proximus

Proximus Nova is a high-performance, expert-driven AI organization that operates in two modes: **Desktop Workbench** (Surgical Local Mastery) and **Enterprise SaaS** (Distributed Cloud Orchestration).

---

## 🏗️ High-Level Overview

The system is built on the **Hive Framework**, a polyglot orchestration engine (Go, Python, Rust) that coordinates specialized agents to achieve complex engineering goals across **Desktop Workbench** (standalone Python) and **Enterprise SaaS** (distributed Go/Kafka) modes.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'background': '#ffffff', 'primaryColor': '#f8fafc', 'primaryBorderColor': '#cbd5e1', 'primaryTextColor': '#0f172a', 'lineColor': '#475569', 'clusterBkg': '#ffffff', 'clusterBorder': '#cbd5e1', 'edgeLabelBackground': '#ffffff'}}}%%
flowchart TB
    User(["User Mission"]) --> TUI["Proximus TUI Shell\n(Master Control)"]
    
    subgraph Mode_Desktop ["1. Desktop Nova Mode (Active Focus)"]
        TUI -->|"Direct Loop"| PythonOrch["Standalone Python Engine\n(Desktop Nova)"]
        PythonOrch --> Experts
    end

    subgraph Mode_SaaS ["2. Enterprise SaaS Mode (Reserved)"]
        TUI -->|"API Call"| GoCore
        GoCore["Go Gateway + Orchestrator\nKafka Event Bus"]
        GoCore --> Experts
    end

    subgraph Experts ["AI Specialist Swarm"]
        CEO["CEO · Nova Lite\nScope & Planning"]
        CTO["CTO · Nova Lite\nArch & Tech Stack"]
        ENG["Engineers (FE/BE)\nSurgical Implementation"]
        Experts_More["QA / DevOps / Finance"]
    end

    Experts -->|"Direct File Surgery"| LocalDisk["Local Host Filesystem"]
    Experts -->|"Containerized Artifacts"| Volumes["Project Volumes"]
```

---

## 🛠️ Operational Modes

### 1. Desktop Nova (Local Workbench)
The primary mode for high-precision engineering.
- **Engine**: A standalone Python `OrchestratorEngine` running locally.
- **Mastery**: Experts modify code directly on the user's host machine using the `LocalFileEditTool`.
- **Latency**: Zero. No network hops between orchestrator and agents.

### 2. Enterprise SaaS (Cloud Scale)
The distributed architecture for multi-tenant deployments.
- **Engine**: The Go-based Gateway and Orchestrator managed via Distributed Sagas.
- **Backbone**: Apache Kafka handles asynchronous task delivery and cross-service resilience.
- **Status**: Reserved for production scaling (Oracle Cloud / AWS).

---

## 🧱 Expert Coordination Mesh

Proximus leverages a high-performance **Go Orchestrator** to coordinate specialized experts:

1. **Strategic Experts (CEO/CTO)**: Use a Saga-based planning system to define project milestones and technical requirements.
2. **Surgical Execution**: Engineer Specialists (Backend/Frontend) are equipped with precision tools (e.g., `LocalFileEditTool`) to modify source code with minimal side effects and maximum token efficiency.
3. **Hybrid Workbench**: The system supports both isolated **SaaS environments** and **Local direct-mount** modes, allowing the specialist mesh to work directly on the host filesystem when `AI_ORG_LOCAL_MODE` is enabled.

## 🧱 Core Components

### 1. API Gateway (`go-backend/cmd/gateway`)

The gateway is the single entry point for all external traffic.

- **Authentication**: Supports both local mode (no login) and SaaS mode (Google OAuth2 + RS256 JWT).
- **Routing**: Proxies requests to internal services and manages project/task resources.
- **WebSockets**: Integrated with `ws-hub` to provide real-time updates to the dashboard.

### 2. Orchestrator (`go-backend/cmd/orchestrator`)

The brain of the system orchestration.

- **DAG Generation**: Converts a high-level goal into a Directed Acyclic Graph (DAG) of tasks.
- **Task Dispatch**: Broadcasts tasks to Kafka with specialized LLM configurations per agent role.
- **State Management**: Tracks project progress and coordinates agent hand-offs.

### 3. AI Agent Fleet (`agents/`)

Specialized Python workers that consume tasks from Kafka and execute them using LLMs.

- **Multi-Provider Support**: Backend support for Amazon Bedrock (Nova), OpenAI, Anthropic, and Google (Gemini).
- **Tool Use**: Agents can access shared tools (code execution, file system, web search) to perform their tasks.
- **Sandboxing**: Code execution is isolated using gVisor (`runsc`) for production security.

### 4. Event Bus (`messaging/`)

Apache Kafka serves as the backbone for asynchronous communication.

- **`ai-org-tasks`**: New tasks for agents.
- **`ai-org-results`**: Completed task data.
- **`ai-org-events`**: Real-time progress logs (streamed to UI via WebSockets).

### 5. Model Context Protocol (MCP) Server (`go-backend/cmd/mcp-server`)

The MCP server provides a standardized interface for agents to interact with the host system.
- **Sandboxed File IO**: Secure reading and writing of files within a restricted path.
- **Extensible Tooling**: Standardized protocol for adding new capabilities (e.g., DB access, browser control) without modifying agent core logic.

### 6. Mixture of Experts (MoE) Routing (`moe-scoring/`)

A high-performance Rust service that routes tasks to the most efficient LLM or agent based on complexity and cost constraints.

---

## 🔄 Data Flow: From Idea to Code

1. **Submission**: User submits a business idea via the **Dashboard** or **TUI**.
2. **Orchestration**: The **Go Orchestrator** creates a multi-phase project plan (CEO → CTO → Engineers → QA → DevOps).
3. **Goal Definition**: The **CEO Agent** researches the idea and produces a PRD (Product Requirements Document).
4. **Technical Design**: The **CTO Agent** takes the PRD and defines the architecture, database schema, and technology stack.
5. **Implementation**: **Engineer Agents (FE/BE)** write the actual source code based on the technical design.
6. **Quality Assurance**: The **QA Agent** performs code review and executes tests.
7. **Deployment**: The **DevOps Agent** generates infrastructure-as-code (Terraform/K8s) to deploy the project.
8. **Completion**: The **Orchestrator** marks the project as complete, and the user is notified.

---

## 🛡️ Security & Reliability

- **Distributed Sagas**: Ensures atomic cross-service agent state transitions.
- **Distributed Tracing**: Full visibility via OpenTelemetry (Go, Python, Rust) integrated with LangSmith.
- **AST Validation**: AI-generated code is validated using a Rust-based parser before execution.
- **Egress Proxy**: Restricts agent network access to an allowlist of permitted domains.
