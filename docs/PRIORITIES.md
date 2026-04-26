# Proximus — Contribution Priorities

> **Last Updated**: 2026-04-20

This document defines **where contributions should be focused** for maximum
impact. Please read this before opening a PR.

---

## Current Priorities

| Priority | Area | Status | Description |
|:---|:---|:---|:---|
| 🔴 **P0** | Agent Prompt Engineering | **Active** | Improve YAML prompt templates, add few-shot examples, refine reasoning chains |
| 🔴 **P0** | File Edit Tool Reliability | **Active** | Improve fuzzy matching accuracy, add new matching strategies |
| 🟠 **P1** | Python Test Coverage | **Active** | Target ≥80% coverage on `agents/`, `orchestrator/`, `tools/`, `messaging/` |
| 🟠 **P1** | Desktop Nova UX | **Active** | TUI improvements, error messages, status reporting |
| 🟡 **P2** | Pydantic Output Schemas | Open | Add schemas for Backend, Frontend, and DevOps agent outputs |
| 🟡 **P2** | Documentation | Open | Mermaid diagrams, architecture visuals, tutorial content |
| ⚪ **P3** | Go Backend / SaaS Mode | **Frozen** | Not accepting changes until v2.0 |
| ⚪ **P3** | MoE Router Integration | **Frozen** | Rust scorer is complete but not yet integrated into the Python layer |
| ⚪ **P3** | Dashboard Frontend | **Frozen** | Next.js dashboard is feature-complete for the current roadmap |

---

## 🧊 Infrastructure Freeze (Active)

The following components are **feature-frozen** until v2.0:

- **Go backend** (`go-backend/`) — All 8 microservices
- **Kafka messaging** (`messaging/kafka_client.py`) — Producer/consumer clients
- **Docker infrastructure** (`docker-compose*.yml`, `Dockerfile*`)
- **Rust services** (`security-check/`, `moe-scoring/`)
- **Database migrations** (`go-backend/migrations/`)

**Bug fixes** are still accepted for frozen components. **New features** are not.

### Why?

The infrastructure is enterprise-grade but the product intelligence (agent
quality, tool reliability, test coverage) hasn't caught up. All energy should
go into making the Desktop Nova mode produce genuinely usable output for real
use cases.

---

## How to Pick a Task

1. **Check the Issues tab** for items tagged `good-first-issue` or `help-wanted`.
2. **Read the prompt templates** in `agents/prompts/*.yaml` — improving a prompt
   is one of the highest-impact contributions you can make.
3. **Add a test** — any new test covering untested code paths is welcome.
4. **If unsure**, open a Discussion thread before starting work.

---

## What Makes a Great PR

- **Focused**: One issue per PR. Don't mix prompt improvements with infra changes.
- **Tested**: If you changed agent logic, include a test with a mock LLM response.
- **Documented**: If you added a new prompt template, update the agent's docstring.
- **Small**: Prefer 100-line PRs over 1000-line PRs. We'll merge faster.
