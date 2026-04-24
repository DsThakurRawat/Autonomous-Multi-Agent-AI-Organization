# API Reference — Proximus Go Gateway

The Go Gateway (running on port `8080` by default) is the primary entry point for the Enterprise SaaS mode. It handles authentication, project lifecycle, and agent management.

---

## 🔐 Authentication & Security

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/healthz` | System-wide health check (Go, Postgres, Kafka). |
| `GET` | `/auth/google` | Initiate Google OAuth2 flow. |
| `GET` | `/auth/google/callback` | OAuth2 callback handler (sets JWT HttpOnly cookie). |

---

## 🏗️ Project Management

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/v1/projects` | Create a new project from a mission statement. |
| `GET` | `/v1/projects` | List all projects for the authenticated tenant. |
| `GET` | `/v1/projects/:id` | Get detailed status, memory snapshot, and task counts. |
| `DELETE` | `/v1/projects/:id` | Cancel an active project and stop its agents. |

---

## 📊 Monitoring & Insights

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/v1/projects/:id/tasks` | Get the full Task Graph (DAG) status. |
| `GET` | `/v1/projects/:id/events` | Stream project event logs. |
| `GET` | `/v1/projects/:id/cost` | Get real-time cost breakdown per agent role. |

---

## ⚙️ User Settings & LLM Keys

Users can manage their own LLM API keys. Keys are stored **AES-256-GCM encrypted** in the database.

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/v1/settings/keys` | Add a new encrypted LLM API key. |
| `GET` | `/v1/settings/keys` | List labels and key hints (last 4 chars) of stored keys. |
| `DELETE` | `/v1/settings/keys/:id` | Permanently delete a stored key. |
| `POST` | `/v1/settings/agent-prefs` | Set specific model preferences per agent role. |
| `GET` | `/v1/settings/agent-prefs` | Get all per-agent model overrides. |

---

## 🛰️ WebSocket Integration

The WebSocket hub (`/ws`) provides real-time event streaming using the following event types:
*   `task_start`: Emitted when an agent begins a task.
*   `agent_message`: Intermediate "thoughts" or logs from an agent.
*   `task_completed`: Emitted upon successful task resolution.
*   `budget_alert`: Emitted when cost thresholds are crossed.
