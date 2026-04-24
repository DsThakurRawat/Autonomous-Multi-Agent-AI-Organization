# Proximus — Autonomous Multi-Agent AI Organization

[![Go](https://img.shields.io/badge/go-1.25.0-00ADD8?style=flat-square&logo=go&logoColor=white)](https://go.dev/)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat-square&logo=next.js)](https://nextjs.org/)
[![Kafka](https://img.shields.io/badge/Kafka-Event_Driven-231F20?style=flat-square&logo=apachekafka)](https://kafka.apache.org/)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

> A production-grade, event-driven system where a team of specialized AI agents autonomously plan, build, test, and ship real software from a single business idea.

---

## ✨ Core Philosophy: Surgical Mastery
Proximus is built on the principle of **precision**. Instead of generic code generation, our specialist agents (CEO, CTO, Engineers, QA, DevOps) perform **surgical local mastery**. They modify your source code with minimal side effects, preserving your style and maintaining full context.

## 🚀 Quick Start (30 Seconds)

The fastest way to experience Proximus is through the **Desktop Nova** standalone runner.

### 1. Setup
```bash
git clone https://github.com/DsThakurRawat/Autonomous-Multi-Agent-AI-Organization.git
cd "Autonomous Multi-Agent AI Organization"
cp .env.example .env # Add your LLM API keys
```

### 2. Launch the Swarm
Choose your preferred interface:

*   **Interactive TUI Shell (Recommended)**:
    ```bash
    python3 tui.py
    ```
*   **CLI Runner**:
    ```bash
    python3 desktop_nova.py "Build a real-time weather dashboard with FastAPI"
    ```

## 🏗️ The Hive Core Framework
Proximus is powered by the **Hive Framework**, a specialized multi-agent orchestration engine designed for surgical precision in autonomous engineering. Hive provides the foundational layers for Pydantic V2 validation, SecretStr security, and vector-native semantic caching.

- **[HIVE_ENGINEERING_ROADMAP.md](./HIVE_ENGINEERING_ROADMAP.md)**: Deep-dive into the engineering layers and implementation patterns of the framework.
- **[FUTURE_ROADMAP.md](./FUTURE_ROADMAP.md)**: The high-level product vision and upcoming feature milestones.

---

## 🛠️ Operational Modes

| Mode | **Desktop Nova (Active)** | **Enterprise SaaS (Scalable)** |
| :--- | :--- | :--- |
| **Identity** | High-Precision Local Workbench | Distributed Cloud Platform |
| **Logic Engine** | Standalone Python Orchestrator | Go Orchestrator + Kafka Sagas |
| **Dependency** | None (Zero-Infra) | Kafka, PostgreSQL, Redis |
| **Best For** | Daily Coding & Refactoring | Multi-Tenant AI-Org-as-a-Service |

---

## 🗺️ Navigation & Documentation

We believe in clean, deep-dive documentation. Please explore our specialized guides:

*   **[Developer Hub](./docs/DEVELOPER_HUB.md)**: The central technical entry point for the polyglot codebase.
*   **[Architecture Guide](./architecture.md)**: High-level system design and data flow.
*   **[API Reference](./docs/API_REFERENCE.md)**: Go Gateway routes and WebSocket events.
*   **[Desktop Mastery](./docs/DESKTOP_MASTERY.md)**: Internals of the local standalone engine.
*   **[Enterprise Setup](./docs/ENTERPRISE_SAS_GUIDE.md)**: How to run the full Docker-based SaaS stack.

---

## 🛡️ Security & Reliability
Proximus is hardened for production environments with:
*   **PII Scrubbing**: Rust-based log redaction.
*   **AST Validation**: Security analysis of AI-generated scripts before execution.
*   **Egress Proxy**: Restricted agent network access to an allowlist of domains.
*   **Budget Gates**: Real-time spending control and alerts.

---

## 🧠 LLM Configuration
By default, the entire system is powered by **Amazon Nova** models, but it is provider-agnostic. Specific agents can be dynamically swapped via the UI.

| Agent | Default Model | Alternatives |
| :--- | :--- | :--- |
| **CEO / CTO** | `nova-lite-v1:0` | GPT-4o, Claude 3.5 |
| **Engineers** | `nova-lite-v1:0` | Gemini 1.5, GPT-4o |
| **QA / DevOps**| `nova-lite-v1:0` | Claude 3 Haiku |
| **Finance** | `nova-micro-v1:0` | GPT-4o-mini |

---

## 🛠️ Troubleshooting

### Kafka Issues
If agents are not receiving tasks, ensure Kafka is healthy:
```bash
make status
make logs  # Check for kafka connection errors
```
If stuck, run `make clean` to wipe volumes and restart.

### Dashboard/WebSockets
Ensure `ws-hub` is running. Check browser console for WebSocket connection errors to `localhost:8080`.

### LLM Errors
Verify `.env` has valid API keys. Check agent logs: `make logs-agents`.

---

## 🤝 Contributing
We welcome contributions! Please see **[CONTRIBUTING.md](./CONTRIBUTING.md)** for our standards and **[SETUP.md](./SETUP.md)** for local development environment configuration.

## 📄 License
MIT — see `LICENSE` for details.
