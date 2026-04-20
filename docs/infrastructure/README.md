# Security & Rust Services — Technical Reference

> **Modules**: `security-check/`, `moe-scoring/`
> **Language**: Rust
> **Key Dependencies**: `serde`, `regex`, `lazy_static`, `rustpython-parser`, `actix-web`

---

## 1. Overview

Proximus uses Rust for performance-critical, security-sensitive operations where Python's overhead or GIL limitations are unacceptable. There are two Rust services:

1.  **`security-check`**: AST-based code validation and PII/credential scrubbing.
2.  **`moe-scoring`**: Sub-millisecond Mixture-of-Experts routing engine.

Both are compiled to native binaries and invoked either via stdin/stdout IPC (local mode) or as HTTP microservices (SaaS mode).

---

## 2. `security-check` — Code Validation & Log Scrubbing

**Source**: [`security-check/src/`](../security-check/src/)

### 2.1. Architecture

The binary reads a JSON `SecurityRequest` from stdin and writes a `SecurityResponse` to stdout.

```
{
  "task": "scrub" | "validate_python",
  "content": "<code or log text>"
}
→
{
  "safe": true | false,
  "result": "<processed content>",
  "message": "Human-readable explanation"
}
```

### 2.2. PII Scrubber (`scrubber.rs`)

**Source**: [`security-check/src/scrubber.rs`](../security-check/src/scrubber.rs)

Uses compiled `lazy_static` regex patterns for high-throughput redaction.

**Patterns Detected**:

| Pattern | Regex | Replacement |
| :--- | :--- | :--- |
| **Email Addresses** | `[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}` | `[REDACTED_EMAIL]` |
| **API Keys** | `(sk-\|g-)[a-zA-Z0-9]{20,48}` | `[REDACTED_KEY]` |
| **IPv4 Addresses** | `\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b` | `[REDACTED_IP]` |

**Performance**: Regex patterns are compiled once at startup via `lazy_static!` and reused across all invocations — zero allocation overhead per call.

**Test Coverage**: 10 test cases covering single/multiple emails, plus-addressing, case sensitivity, API keys in JSON, IPv4 addresses, mixed content, and no-op pass-through.

### 2.3. Python AST Validator (`validator.rs`)

**Source**: [`security-check/src/validator.rs`](../security-check/src/validator.rs)

Uses `rustpython-parser` to parse AI-generated Python code into an Abstract Syntax Tree, then walks the tree looking for dangerous patterns.

**Blocked Imports**:

| Module | Risk |
| :--- | :--- |
| `os` | Filesystem access, `os.system()` shell execution. |
| `subprocess` | Arbitrary command execution. |
| `shutil` | Recursive file deletion. |
| `sh` | Shell execution wrapper. |
| `tempfile` | Potential for temp-file abuse. |

**Blocked Function Calls**:

| Function | Risk |
| :--- | :--- |
| `eval()` | Arbitrary code execution. |
| `exec()` | Arbitrary code execution. |
| `compile()` | Dynamic code compilation. |
| `getattr()` | Reflective attribute access (can bypass restrictions). |
| `open()` | File I/O (reads/writes arbitrary paths). |

**Recursive Analysis**: The validator recursively descends into `if/else` blocks to detect dangerous code hidden in conditional branches.

---

## 3. `moe-scoring` — Mixture-of-Experts Router

**Source**: [`moe-scoring/src/`](../moe-scoring/src/)

### 3.1. Purpose

When the system receives a task, the MoE Router determines which agent/model combination is optimal based on the task's semantic embedding, current agent load, historical success rates, cost, and latency.

### 3.2. Scoring Algorithm (`scorer.rs`)

**Source**: [`moe-scoring/src/scorer.rs`](../moe-scoring/src/scorer.rs)

Each expert receives a **composite score** computed as a weighted sum of 5 factors:

| Factor | Metric | Meaning |
| :--- | :--- | :--- |
| **Similarity** | Cosine similarity between task and expert embedding vectors | How well does the expert's specialization match the task? |
| **Load** | `1.0 - load_factor` | Prefer idle experts over saturated ones. |
| **Success** | Historical success rate (0.0–1.0) | Prefer experts with better track records. |
| **Cost** | Non-linear penalty: `(1 - cost_ratio)²` | Aggressive penalization of expensive models. |
| **Latency** | `1 - (p95_latency / max_latency)` | Prefer faster-responding models. |

### 3.3. Strategy-Based Weight Profiles

| Strategy | Similarity | Load | Success | Cost | Latency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Balanced** | 0.35 | 0.20 | 0.20 | 0.15 | 0.10 |
| **Performance** | 0.30 | 0.10 | 0.30 | 0.05 | 0.25 |
| **CostSaver** | 0.30 | 0.20 | 0.10 | 0.35 | 0.05 |

### 3.4. Ensemble Mode

When the top expert's confidence is below `0.70` OR the gap between the top two experts is less than `0.10`, the system triggers **ensemble mode** — sending the task to multiple experts and merging their outputs.

### 3.5. Expert Ranking Pipeline

```
Task Embedding → Cosine Similarity per Expert
                → Combine with Load/Success/Cost/Latency
                → Apply Strategy Weights
                → Sort Descending by Composite Score
                → Return Top Expert + Fallbacks
```

**Overload Exclusion**: When `exclude_overloaded=true`, experts with `load_factor >= 1.0` are completely removed from the candidate pool.

### 3.6. Additional Modules

| Module | Purpose |
| :--- | :--- |
| `models.rs` | Data structures for `Expert`, `ExpertStats`, `ExpertScore`, `Strategy`. |
| `vectorizer.rs` | Task-to-vector embedding logic for semantic matching. |
| `metrics.rs` | Prometheus metric instrumentation (scoring latency, cache hits). |
| `main.rs` | HTTP server (Actix-Web) exposing `/route` and `/health` endpoints. |

### 3.7. Test Coverage

15 unit tests covering:
-   Cosine similarity edge cases (identical, orthogonal, zero, opposite, partial overlap, truncation).
-   Expert scoring (perfect expert, overloaded expert).
-   Ranking (sorted output, overload exclusion toggle).
-   Ensemble decision boundaries (threshold, gap, boundary conditions).

---

## 4. Go Backend Services

**Source**: [`go-backend/`](../go-backend/)

The Go backend is a collection of microservices that form the Enterprise SaaS orchestration layer.

### 4.1. Service Map

| Service | Directory | Port | Responsibility |
| :--- | :--- | :--- | :--- |
| **API Gateway** | `cmd/gateway/` | `8080` | Auth, REST API, project CRUD, key management. |
| **Orchestrator** | `cmd/orchestrator/` | `50051` | gRPC-based DAG execution, Kafka task dispatch. |
| **WebSocket Hub** | `cmd/ws-hub/` | `8081` | Redis PubSub → Browser WebSocket streaming. |
| **Health Monitor** | `cmd/health-monitor/` | `8082` | Unified `/healthz` for all infra dependencies. |
| **MCP Server** | `cmd/mcp-server/` | `8090` | Model Context Protocol server for tool execution. |
| **Metrics Service** | `cmd/metrics-svc/` | `9090` | Prometheus metric aggregation. |
| **Tenant Service** | `cmd/tenant-svc/` | `8083` | Multi-tenant isolation and billing. |
| **Egress Proxy** | `cmd/proxy/` | `8888` | Domain-allowlist enforcement for agent network access. |

### 4.2. Internal Packages (`go-backend/internal/`)

| Package | Purpose |
| :--- | :--- |
| `gateway/` | HTTP routing, middleware, JWT auth, Google OAuth2. |
| `orchestrator/` | gRPC service, state machine, Kafka producer. |
| `hub/` | WebSocket connection management, Redis subscriber. |
| `health/` | Readiness/liveness probe logic (Postgres, Redis, Kafka). |
| `mcp/` | MCP protocol handlers for standardized tool calls. |
| `metrics/` | OpenTelemetry collector and Prometheus exporter. |
| `proxy/` | HTTP forward proxy with domain allowlist. |
| `tenant/` | Tenant CRUD, data isolation, billing records. |
| `shared/` | Logger, config, database pool, crypto utilities. |

### 4.3. Database Migrations (`go-backend/migrations/`)

| Migration | Purpose |
| :--- | :--- |
| `001_init` | Core schema: `tenants`, `users`, `projects`, `tasks`. |
| `002_user_llm_keys` | AES-256-GCM encrypted key storage and per-agent model preferences. |
| `003_user_auth` | Atomic `upsert_user_from_google_login` function. |
| `004_projects_name` | Project naming and back-fill function. |
| `005_seed_local_data` | Default tenant/user seed data for `AUTH_DISABLED=true` mode. |

### 4.4. Security Model

-   **Authentication**: Google OAuth2 → RS256 JWT (stored in HttpOnly cookies).
-   **Key Encryption**: User LLM API keys are encrypted with AES-256-GCM before database storage.
-   **Egress Proxy**: All agent HTTP requests are routed through a Go proxy that enforces a domain allowlist.
-   **CORS**: Restricted to the dashboard origin only.
