# Contributing to Proximus — Autonomous Multi-Agent AI Organization

## Branch Naming Convention

Every operation **must** be done on its own branch. Never commit directly to `main`.

### Format

```text
<type>/<short-description>
```

### Types

| Type | Used For | Example |
| :--- | :--- | :--- |
| `feature/` | New feature or enhancement | `feature/nextjs-dashboard` |
| `bugfix/` | Fixing a non-urgent bug | `bugfix/moe-router-edge-case` |
| `hotfix/` | Urgent production fix | `hotfix/kafka-connection-leak` |
| `release/` | Release preparation | `release/v1.2.0` |
| `chore/` | Refactoring / cleanup / housekeeping | `chore/gitignore-update` |
| `docs/` | Documentation only | `docs/architecture-diagram` |
| `test/` | Adding or fixing tests | `test/integration-kafka` |
| `perf/` | Performance improvements | `perf/moe-scoring-vectorize` |
| `infra/` | Infrastructure / DevOps changes | `infra/helm-chart-agents` |
| `lang/` | New language service (Rust, TS, etc) | `lang/rust-kafka-consumer` |

### Rules

1. **One branch = one concern.** Don't bundle unrelated changes.
2. **Branch from `main`** unless it's a hotfix on production.
3. **Never force-push to `main`.**
4. **Merge via PR** (or explicit user approval in this project).
5. **Delete branch after merge.**

---

## Commit Message Format

```text
<type>(<scope>): <short description>

[optional body]

[optional footer: refs #issue]
```

### Examples

```text
feat(moe): add ensemble routing for low-confidence tasks
fix(kafka): handle reconnect on broker restart
chore(deps): bump pydantic to 2.6.0
test(moe): add scoring edge case for zero vectors
docs(arch): update kafka topic schema table
infra(k8s): add KEDA ScaledObject for engineer-backend
lang(rust): add fast cosine similarity service
```

---

## Active Branches Log

| Branch                     | Type  | Status | Description                  |
| :------------------------- | :---- | :----- | :--------------------------- |
| `main`                     | —     | Stable | Production base              |
| `chore/git-workflow-setup` | chore | Active | Git conventions + .gitignore |

> **Update this table every time you create or merge a branch.**

---

## Developer PR Workflow

To maintain a clean and reliable history, we follow a strict Pull Request (PR) workflow:

1. **Create Feature Branch**: Use the standard `type/description` naming.
2. **Commit with Scope**: Use conventional commits (e.g., `feat(agents): ...`).
3. **Raise PR**: Push your branch to GitHub and open a Pull Request against `main`.
4. **Pass Checks**: Ensure CI/CD passes for Go, Python, and Rust.
5. **Merge**: Once approved, merge via PR. **Do not commit directly to `main`.**

---

## Tech Stack (Recommended Proficiencies)

Proximus is a polyglot system designed for performance and scalability:

- **Go 1.24.0** — API Gateway, Orchestrator, health monitoring, and system-level microservices.
- **Python 3.12** — AI Agents (Amazon Bedrock/Nova), TUI, and observability integrations.
- **Rust** — High-performance scoring (MoE) and security-critical services (AST validation).
- **TypeScript / Next.js 14** — Real-time analytics dashboard and React Flow visualization.
- **Apache Kafka** — Main event bus for agent-to-orchestrator communication.
- **PostgreSQL 15 & Redis 7** — Structured data persistence and low-latency caching/PubSub.
- **Docker & Terraform** — Containerization and Infrastructure as Code.
