# Proximus — Autonomous Multi-Agent AI Organization

[![Go](https://img.shields.io/badge/go-1.24.0-00ADD8?style=flat-square&logo=go&logoColor=white)](https://go.dev/)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=next.js)](https://nextjs.org/)
[![Kafka](https://img.shields.io/badge/Kafka-Event_Driven-231F20?style=flat-square&logo=apachekafka)](https://kafka.apache.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![Go CI](https://github.com/DsThakurRawat/Autonomous-Multi-Agent-AI-Organization/actions/workflows/go-ci.yml/badge.svg)](https://github.com/DsThakurRawat/Autonomous-Multi-Agent-AI-Organization/actions/workflows/go-ci.yml)
[![Frontend CI](https://github.com/DsThakurRawat/Autonomous-Multi-Agent-AI-Organization/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/DsThakurRawat/Autonomous-Multi-Agent-AI-Organization/actions/workflows/frontend-ci.yml)
[![Rust CI](https://github.com/DsThakurRawat/Autonomous-Multi-Agent-AI-Organization/actions/workflows/rust-ci.yml/badge.svg)](https://github.com/DsThakurRawat/Autonomous-Multi-Agent-AI-Organization/actions/workflows/rust-ci.yml)

> A production-grade, event-driven system where a team of specialized AI agents autonomously plan, build, test, and ship real software from a single business idea — powered by **Amazon Nova** foundation models and **Nova Act** browser automation.

## Core Features

- **Full-Stack Observability**: Unified distributed tracing via **OpenTelemetry (Jaeger)**, metrics via **Prometheus/Grafana**, and deep LLM reasoning visibility with **LangSmith**.
- **Production-Grade Shielding**: Kernel-level sandboxing with **gVisor** (`runsc`), and high-performance **Rust-based AST validation and PII scrubbing**.
- **Distributed Reliability**: API Idempotency (Redis) and **Distributed Sagas** for atomic state transitions across microservices.
- **MCP Sandboxing**: Native **Model Context Protocol (MCP)** server for secure, standardized tool execution and resource access.
- **ML Memory & MoE**: High-performance **Semantic Vector Caching** (Qdrant) and sub-ms **Rust-based expert routing** (Mixture of Experts).
- **Real-Time UX**: Live multi-agent task streaming via **WebSockets (ws-hub)** and interactive **React Flow** DAG visualization.
- **Next.js Vibe Dashboard**: Premium animated UI for live task tracking, system health monitoring, and LLM key management.
- **Interactive TUI**: A powerful **Textual-based Terminal UI** for headless control and live event monitoring.

---

## What It Does

You type a business idea. The system:

1. **CEO Agent** — Researches the market, defines scope and requirements
2. **CTO Agent** — Designs the system architecture and database schema
3. **Backend Engineer Agent** — Writes Python/Go APIs, database schemas, and logic
4. **Frontend Engineer Agent** — Writes React/TypeScript/CSS code and responsive layouts
5. **QA Agent** — Runs tests, detects edge cases and bugs
6. **DevOps Agent** — Generates Terraform, Kubernetes manifests, CI/CD pipelines
7. **Finance Agent** — Tracks token usage and enforces budget limits

**Continuous Quality Loop**: After each phase, the Orchestrator runs a self-critique cycle where agents reflect on their own outputs, providing quality scores and approval signals before the project proceeds.

Every agent runs asynchronously over Kafka. You watch it all happen live in the dashboard.

---

## Architecture

Proximus uses a microservices architecture with a Go-based core, Python AI agents, and a Next.js dashboard. For a detailed breakdown of components and data flow, see [architecture.md](./architecture.md).

---

## Tech Stack

| Command      | Description                                                      |
| :----------- | :--------------------------------------------------------------- |
| `make start` | Launches the full platform (detached)                            |
| `make stop`  | Gracefully stops all services                                    |
| `make clean` | Stops services and **wipes all volumes** (fixes Kafka ID issues) |
| `make logs`  | Tails logs for all services                                      |

| Layer             | Technology                                                       |
| ----------------- | ---------------------------------------------------------------- |
| **API Gateway**   | Go 1.24.0 · Fiber v2                                             |
| **Orchestrator**  | Go · gRPC · DAG engine                                           |
| **WebSocket Hub** | Go · Redis Pub/Sub                                               |
| **AI Agents**     | Python 3.12 · Amazon Bedrock / OpenAI / Anthropic / Google       |
| **Event Bus**     | Apache Kafka 7.6.0 · ZooKeeper                                   |
| **Database**      | PostgreSQL 15 · pgcrypto                                         |
| **Cache & Store** | Redis 7 · Qdrant 1.8.2 (Vector DB)                               |
| **Dashboard**     | Next.js 14 · TypeScript · React Flow                             |
| **TUI**           | Python · Textual · WebSockets                                    |
| **Observability** | Jaeger 1.54 · Prometheus 2.49.1 · Grafana 10.3.1 · OpenTelemetry |
| **MoE Routing**   | Rust (sub-ms expert scoring)                                     |
| **Security**      | Rust (AST Validation + PII Masking)                              |
| **Auth (SaaS)**   | Google OAuth2 · RS256 JWT                                        |
| **Infra**         | Docker Compose · Helm · Terraform                                |

---

## Quick Start

The fastest way to run Proximus is using the unified **CLI Launcher**.

### Prerequisites

- **Docker + Docker Compose**
- **gVisor (runsc)** — Optional, for hardened agent sandboxing.
- **AWS Bedrock Access** (or fallback keys for OpenAI/Anthropic)
- **Qdrant** — For semantic caching.
- **OpenTelemetry Collector** — For distributed tracing.

### 1-Minute Setup

```bash
# 1. Clone
git clone https://github.com/DsThakurRawat/Autonomous-Multi-Agent-AI-Organization.git
cd "Autonomous Multi-Agent AI Organization"

# 2. Setup environment
cp .env.example .env
# Edit .env and add your AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_REGION

# 3. Start the platform
make start
```

---

## Future Vision

Ongoing development focuses on scaling to production, advanced self-healing, and visual intelligence. For the full technical vision, please see the [FUTURE_ROADMAP.md](./FUTURE_ROADMAP.md).

---

## Advanced Settings

For deploying on a server where multiple users sign in with Google accounts.

**Prerequisites:** Docker, a domain, Google Cloud Console app

```bash
# 1. Clone
git clone https://github.com/DsThakurRawat/Autonomous-Multi-Agent-AI-Organization.git
cd "Autonomous Multi-Agent AI Organization"

# 2. Copy SaaS env template
cp .env.example .env

# 3. Generate RSA keys for JWT signing
mkdir -p keys
openssl genrsa -out keys/private.pem 2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem

# 4. Generate encryption key
openssl rand -hex 32   # → paste as KEY_ENCRYPTION_KEY in .env

# 5. Fill in Google OAuth credentials in .env
#    Create at: https://console.cloud.google.com/apis/credentials
#    Authorized redirect URI: https://yourdomain.com/auth/google/callback

# 6. Fill in AWS API keys and any fallback LLM API keys in .env (platform-wide defaults)

# 7. Start
docker-compose -f go-backend/deploy/docker-compose.yml up --build

# 8. Open
open https://yourdomain.com
```

Users land on a login page → **Sign in with Google** → redirected to their dashboard.

---

## Environment Variables

### Auth & Security

| `AUTH_DISABLED`        | Yes      | Set to `true` for local, `false` for SaaS      |
| `KEY_ENCRYPTION_KEY`   | Yes      | 64-char hex (32 bytes). `openssl rand -hex 32` |
| `JWT_PRIVATE_KEY_PATH` | Yes      | Path to `keys/private.pem` (SaaS only)         |
| `JWT_PUBLIC_KEY_PATH`  | Yes      | Path to `keys/public.pem` (SaaS only)          |
| `JWT_EXPIRY`           |          | Default: `168h` (7 days)                       |

---

## API Routes (Go Gateway — port 8080)

| Method   | Path                             | Description                         |
| -------- | -------------------------------- | ----------------------------------- |
| `GET`    | `/healthz`                       | Health check                        |
| `GET`    | `/auth/google`                   | Initiate Google OAuth (SaaS mode)   |
| `GET`    | `/auth/google/callback`          | OAuth callback → JWT cookie         |
| `POST`   | `/v1/projects`                   | Create a new project                |
| `GET`    | `/v1/projects`                   | List your projects                  |
| `GET`    | `/v1/projects/:id`               | Get project detail + task counts    |
| `DELETE` | `/v1/projects/:id`               | Cancel a project                    |
| `GET`    | `/v1/projects/:id/tasks`         | DAG task list (for DagViewer)       |
| `GET`    | `/v1/projects/:id/events`        | Recent agent event log              |
| `GET`    | `/v1/projects/:id/cost`          | Cost breakdown per agent            |
| `POST`   | `/v1/settings/keys`              | Add encrypted LLM API key           |
| `GET`    | `/v1/settings/keys`              | List stored key labels              |
| `DELETE` | `/v1/settings/keys/:id`          | Delete a stored key                 |
| `POST`   | `/v1/settings/agent-prefs`       | Set model preference per agent role |
| `GET`    | `/v1/settings/agent-prefs`       | Get all agent model preferences     |
| `DELETE` | `/v1/settings/agent-prefs/:role` | Reset agent to default model        |

---

## LLM Configuration

### Default Models (Current Configuration)

By default, the entire system is powered by Amazon Nova models. However, the orchestrator and agent layers are designed to be provider-agnostic. Later on, specific agents can be dynamically swapped via the UI to use specialized models (e.g., using Gemini for a highly visual Frontend Engineer task, or Claude for complex Backend QA).

| Agent         | Default Provider | Default Model            | Supported Alternatives    |
| :------------ | :--------------- | :----------------------- | :------------------------ |
| CEO           | Bedrock          | `amazon.nova-lite-v1:0`  | OpenAI, Anthropic, Google |
| CTO           | Bedrock          | `amazon.nova-lite-v1:0`  | OpenAI, Anthropic, Google |
| Backend Eng   | Bedrock          | `amazon.nova-lite-v1:0`  | Anthropic, OpenAI         |
| Frontend Eng  | Bedrock          | `amazon.nova-lite-v1:0`  | Google (Gemini)           |
| QA            | Bedrock          | `amazon.nova-lite-v1:0`  | Anthropic, OpenAI         |
| DevOps        | Bedrock          | `amazon.nova-lite-v1:0`  | Anthropic                 |
| Finance       | Bedrock          | `amazon.nova-micro-v1:0` | OpenAI, Google            |

### Per-User Key Management

In the dashboard → **Settings**, users can:

- Add multiple API keys per provider (stored AES-256-GCM encrypted)
- Override which model each agent role uses
- Select which stored key each agent uses

The resolution order per task:

1. User's agent-specific preference → their stored key
2. User's stored key for the provider (first valid)
3. Server environment variable (`AWS_ACCESS_KEY_ID`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, etc.)
4. Error if none available

---

## Database Migrations

Migrations run automatically in the local Docker Compose stack.

```bash
# Run manually
migrate -path go-backend/migrations -database "$DATABASE_URL" up

# Rollback last migration
migrate -path go-backend/migrations -database "$DATABASE_URL" down 1
```

| Migration           | Contents                                                                    |
| ------------------- | --------------------------------------------------------------------------- |
| `001_init`          | Core schema: tenants, users, projects, tasks, cost_events, agent_heartbeats |
| `002_user_llm_keys` | user_llm_keys + agent_model_prefs tables                                    |
| `003_user_auth`     | users.updated_at + `upsert_google_user()` PG function (atomic OAuth login)  |
| `004_projects_name` | projects.name column (backfilled from idea)                                 |

---

## Dashboard

Access at `http://localhost:3000`

| Page         | What's there                                                        |
| ------------ | ------------------------------------------------------------------- |
| `/`          | Landing page / Google Sign-In (SaaS mode)                           |
| `/dashboard` | Project list, create project, live agent feed, task DAG, cost meter |
| `/settings`  | Manage LLM API keys + per-agent model preferences                   |

---

## Project Structure

```text
├── Makefile                  Cross-platform shortcuts (start, stop, logs)
├── tui.py                    Interactive Terminal UI (Textual)
├── go-backend/               Go microservices
│   ├── cmd/
│   │   ├── gateway/          HTTP API (Fiber) — auth, routing, websockets
│   │   ├── health-monitor/   System health monitoring
│   │   ├── mcp-server/       Model Context Protocol (MCP) server
│   │   ├── metrics-svc/      Metrics tracking service
│   │   ├── orchestrator/     gRPC server — DAG planning, Kafka dispatch
│   │   ├── proxy/            Egress proxy (domain allowlist enforcement)
│   │   ├── tenant-svc/       Tenant management
│   │   └── ws-hub/           WebSocket server — Redis pub/sub
│   ├── internal/
│   │   ├── gateway/handler/  HTTP handlers (projects, tasks, settings, OAuth)
│   │   ├── gateway/middleware/  Auth (JWT + Local), CORS, rate limiting
│   │   ├── orchestrator/     DAG engine + gRPC server
│   │   └── shared/           auth, config, db, kafka, keystore, logger, redis
│   ├── migrations/           SQL migrations (001–004)
│   └── deploy/
│       ├── docker-compose.yml        SaaS mode
│       ├── docker-compose.local.yml  Local mode (no login)
│       └── dockerfiles/
├── agents/                   Python AI agents
│   ├── base_agent.py         Multi-provider LLM caller (OpenAI/Anthropic/Google)
│   ├── agent_service.py      Kafka consumer + per-task LLM resolution
│   ├── model_registry.py     Default model configs per agent role
│   ├── roles.py              Typed role definitions
│   ├── ceo_agent.py
│   ├── cto_agent.py
│   ├── backend_agent.py      (Handles Backend Engineer tasks)
│   ├── frontend_agent.py     (Handles Frontend Engineer tasks)
│   ├── qa_agent.py
│   ├── devops_agent.py
│   └── finance_agent.py
├── dashboard/                Next.js 14 frontend
│   ├── app/
│   │   ├── page.tsx          Landing / login page
│   │   ├── dashboard/        Main dashboard
│   │   └── settings/         LLM key + model preference management
│   └── lib/api.ts            Typed API client
├── security-check/           Rust — AST validation and PII scrubbing gRPC service
├── moe-scoring/              Rust — sub-ms expert routing engine
├── infra/
│   ├── helm/                 Kubernetes Helm charts
│   └── terraform/            AWS infrastructure (Mocked by DevOps Agent)
├── monitoring/               Grafana dashboards and Prometheus configuration
├── observability/            Python-based OpenTelemetry tracing and metrics
├── api/                      API definitions and specs
├── messaging/                Kafka schemas and clients
├── orchestrator/             Python orchestrator logic
├── output/                   Log/artifact outputs
├── tests/                    Test suite (unit and integration)
├── tools/                    Shared agent tools
├── utils/                    Shared utility functions
├── tui.py                    Interactive Terminal UI (Textual)
├── docker-compose.yml        Root compose file (SaaS)
├── docker-compose.observability.yml Metrics and Observability
├── .env.example              SaaS mode env template
├── requirements.txt          Python dependencies
└── Dockerfile.agent          Python agent container image
```

---

## Kubernetes Deployment

```bash
cd infra/helm/ai-org
helm install ai-org . --namespace ai-org-system --create-namespace \
  --set gateway.env.AUTH_DISABLED=false \
  --set gateway.env.GOOGLE_CLIENT_ID=<your-id> \
  --set gateway.env.GOOGLE_CLIENT_SECRET=<your-secret>
```

---

## Terraform (AWS)

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

> **Note**: These files are currently managed and simulated by the DevOps agent locally. Real AWS deployment bindings will be fully integrated.

---

## Production Softening & Resilience

The system is now hardened for production environments:

- **Egress Proxy**: Restricts agent network access to an allowlist of LLM providers and infrastructure.
- **Log Redactor**: Automatically masks API keys (AWS, Google, OpenAI) in both Python and Go logging pipelines using high-performance regex cores.
- **Memory Decay**: Background worker periodically prunes stale agent memories to prevent context-window explosion and data rot.
- **Budget Alerts**: Real-time emission of `budget_alert` events when spend thresholds are crossed, integrated into the Finance Agent's monitoring loop.
- **Health Orchestrator**: Go-based aggregator provides unified readiness checks on `/healthz`, verifying Postgres, Redis, and Kafka availability.

---

## Security

- **Encrypted API keys** — AES-256-GCM. Raw keys never written to disk.
- **`key_hint`** — Only last 4 chars of a key are stored unencrypted (safe for UI display).
- **RS256 JWT** — Asymmetric signing. Private key never leaves the server.
- **CSRF protection** — OAuth state token validated via HttpOnly cookie.
- **HttpOnly JWT cookie** — Immune to XSS token theft.
- **Agent sandboxing** — Support for **gVisor (`runsc`)** for kernel-isolated code execution.
- **Least privilege** — CEO cannot write code; Engineer cannot modify billing.
- **PII Scrubbing** — High-performance Rust-based redaction of logs and agent outputs.
- **AST Validation** — Real-time security analysis of AI-generated Python scripts.

---

## Troubleshooting

### Kafka Connectivity Issues

If agents are not receiving tasks, ensure Kafka is healthy:

```bash
make status
make logs  # check for kafka connection errors
```

If Kafka is stuck, run `make clean` to wipe volumes and restart.

### Dashboard not updating

Ensure the `ws-hub` service is running and that your browser can connect to `localhost:8080`. Check the browser console for WebSocket connection errors.

### LLM API Errors

Verify your `.env` file contains valid API keys. Check the agent logs for specific error messages:

```bash
make logs-agents
```

---

## Contributing

We welcome contributions from the community! Whether you're fixing a bug, adding a feature, or improving documentation, please read our [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines on our PR workflow and coding standards.

---

## Branding & Identity

**Proximus** is the official identity of the Autonomous Multi-Agent AI Organization. When contributing:

- Use **Proximus** when referring to the platform as a whole.
- Maintain the specialized agent roles (CEO, CTO, etc.) as the core organizational units.

---

## License

MIT — see `LICENSE` for details.
