# Proximus Enterprise SaaS Guide

> [!NOTE]
> **STATUS: DORMANT (PRESERVED FOR SCALING)**
> This distributed infrastructure is preserved for future multi-tenant cloud deployments. The **Proximus Desktop Nova** workbench is current active project identity for surgical local engineering.

This document provides a detailed technical overview of the **Enterprise SaaS** orchestration layer.

## 🏗️ Distributed Architecture

The Enterprise version of Proximus is built for high-scale, event-driven orchestration. It decouples the core business logic (Go) from the specialized AI expert agents (Python).

### Core Components

| Component | Responsibility | Technology |
| :--- | :--- | :--- |
| **API Gateway** | Auth, Project Management, Billing | Go (Fiber) |
| **Orchestrator** | DAG Planning, Task Dispatching | Go (gRPC) |
| **Event Bus** | Asynchronous Agent Communication | Apache Kafka |
| **WebSocket Hub** | Live Event Streaming to UI | Go + Redis |
| **Persistence** | Structured state & tenant data | PostgreSQL |
| **Observability** | Distributed Tracing | OpenTelemetry + Jaeger |

---

## 🚦 Operational Flow: The Distributed Saga

In Enterprise mode, the lifecycle of a software project is managed via a **Distributed Saga** pattern to ensure atomicity across heterogeneous services.

### 1. Project Initiation & Planning
The **Go Gateway** accepts a mission. It invokes the `ProposePlan` gRPC method on the **Orchestrator**. 
- The Orchestrator calls the **CEO Agent** via Kafka topic `ai-org-tasks-ceo`.
- The CEO returns a structured JSON payload containing the **Product Requirements Document (PRD)**.
- The Orchestrator then invokes the **CTO Agent** to generate the `ArchitecturePlan`.

### 2. The Task Graph (DAG)
The Orchestrator builds a Directed Acyclic Graph using a custom Go engine.
- **Dependencies**: Backend tasks can run in parallel with Frontend tasks if no data-layer dependency exists.
- **Persistence**: Every node in the DAG is persisted in the `tasks` table in PostgreSQL with states: `PENDING`, `RUNNING`, `COMPLETED`, or `FAILED`.

### 3. Kafka Topology
We use a **Single-Topic-Per-Role** pattern to ensure isolation and scalability:
- `ai-org-tasks-ceo`: Mission planning.
- `ai-org-tasks-be`: Backend implementation.
- `ai-org-tasks-fe`: Frontend implementation.
- `ai-org-results`: Unified results topic for all agents.

### 4. WebSocket Hub & Real-time UX
State changes in the Orchestrator are published to a **Redis Pub/Sub** channel. The **WebSocket Hub (Go)** listens to this channel and streams events to the browser dashboard using the `ProjectID` as the routing key.

---

## 🏗️ Technical Component Deep-Dive

### Go Orchestrator (`go-backend/cmd/orchestrator`)
- **gRPC Interface**: Implements the `OrchestratorService` defined in `api/proto/orchestrator.proto`.
- **State Machine**: Uses a lock-free advancement algorithm to process parallel agent results.
- **Error Handling**: Implements exponential backoff for failed LLM calls and automatic task re-dispatch.

### Go Gateway (`go-backend/cmd/gateway`)
- **Fiber Web Framework**: High-performance HTTP routing.
- **Security**: RS256 JWT validation and AES-256 Key Encryption for user LLM keys.

---

## 🚀 Booting the Enterprise Stack

## 🚀 Booting the Enterprise Stack

To re-activate the distributed infrastructure, ensure Docker is running and execute:

```bash
# 1. Start all infrastructure with observability
docker-compose -f docker-compose.yml -f docker-compose.observability.yml up -d

# 2. Verify Go Backend Health
curl http://localhost:8080/healthz

# 3. Access Dashboard
# Open http://localhost:3000
```

### Strategic Context: Why we use Go/Kafka
- **High Concurrency**: Go's goroutines handle thousands of simultaneous project streams with minimal overhead.
- **Fault Tolerance**: Kafka ensures that if an agent pod crashes, the task is re-delivered, preventing data loss.
- **Tenant Isolation**: The Go-backend enforces strict data boundaries between different SaaS users.

---

## 📁 Repository Map (Enterprise)

- `go-backend/`: The heart of the SaaS platform. Contains the Gateway, Orchestrator, and Health-Monitor.
- `messaging/`: Protobuf definitions and Kafka consumer/producer logic.
- `infra/`: Kubernetes (Helm) and Terraform blueprints for Cloud deployment.
- `api/`: Shared REST and gRPC service definitions.

*Note: For daily local development, use **Proximus Desktop Nova** (`python desktop_nova.py`) for a faster, zero-infra experience.*
