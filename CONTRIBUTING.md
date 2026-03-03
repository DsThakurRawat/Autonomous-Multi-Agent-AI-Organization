# Contributing to Autonomous Multi-Agent AI Organization

## Branch Naming Convention

Every operation **must** be done on its own branch. Never commit directly to `master`/`main`.

### Format

```
<type>/<short-description>
```

### Types

| Type | Used For | Example |
|------|----------|---------|
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
2. **Branch from `master`** unless it's a hotfix on production.
3. **Never force-push to `master`.**
4. **Merge via PR** (or explicit user approval in this project).
5. **Delete branch after merge.**

---

## Commit Message Format

```
<type>(<scope>): <short description>

[optional body]

[optional footer: refs #issue]
```

### Examples

```
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

| Branch | Type | Status | Description |
|--------|------|--------|-------------|
| `master` | — | ✅ Stable | Production base |
| `chore/git-workflow-setup` | chore | 🔨 Active | Git conventions + .gitignore |

> **Update this table every time you create or merge a branch.**

---

## Local Setup

See [SETUP.md](./SETUP.md) for cross-platform installation instructions.

---

## Tech Stack (No Restrictions)

This project uses the best tool for each job:

- **Python** — Orchestrator, Agents, API
- **TypeScript / Next.js** — Dashboard
- **Rust** — High-performance services (future: fast MoE scoring, Kafka consumer)
- **Docker** — Cross-platform packaging
- **Terraform** — Infrastructure as Code
- **Kafka** — Distributed messaging
- **PostgreSQL + Redis** — Persistence and caching
