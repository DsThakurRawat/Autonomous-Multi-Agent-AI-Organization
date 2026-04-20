# Messaging & Kafka Subsystem — Technical Reference

> **Module**: `messaging/`
> **Language**: Python 3.12
> **Key Dependencies**: `kafka-python`, `pydantic`, `opentelemetry`, `structlog`

---

## 1. Overview

The Messaging Subsystem provides the asynchronous communication backbone for the Enterprise SaaS mode. It consists of typed Kafka message schemas, topic definitions, and production-grade producer/consumer clients with built-in resilience.

In Desktop Nova (local) mode, the entire Kafka layer is transparently replaced by an **in-memory mock bus** (`_InMemoryBus`), enabling full development without a running Kafka cluster.

---

## 2. Message Schemas

**Source**: [`messaging/schemas.py`](../messaging/schemas.py)

All messages are Pydantic V2 `BaseModel` subclasses with built-in serialization/deserialization for Kafka.

### 2.1. `TaskMessage` — Orchestrator → Agent

Dispatched by the Go/Python Orchestrator when a task is ready for execution.

| Field | Type | Description |
| :--- | :--- | :--- |
| `message_id` | `str (UUID)` | Unique message identifier. |
| `task_id` | `str` | The task graph node ID. |
| `task_name` | `str` | Human-readable task description. |
| `task_type` | `str` | Category: `strategy`, `architecture`, `code_gen`, `testing`, `deployment`. |
| `agent_role` | `str` | Target agent (e.g., `Engineer_Backend`). |
| `project_id` | `str` | Parent project identifier. |
| `input_data` | `dict` | Task-specific payload (architecture, business plan, etc.). |
| `priority` | `MessagePriority` | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`. |
| `deadline_ms` | `int \| None` | Optional Unix timestamp deadline. |
| `max_retries` / `retry_count` | `int` | Retry governance. |
| `trace_id` / `span_id` | `str` | OpenTelemetry distributed tracing context. |

### 2.2. `ResultMessage` — Agent → Orchestrator

Published by an agent upon task completion or failure.

| Field | Type | Description |
| :--- | :--- | :--- |
| `status` | `str` | `completed`, `failed`, or `retrying`. |
| `output_data` | `dict` | Generated artifacts, code, or analysis results. |
| `error_message` | `str \| None` | Error details on failure. |
| `duration_ms` | `int` | Wall-clock execution time. |
| `cost_usd` | `float` | LLM token cost for this task. |
| `tokens_used` | `int` | Total tokens consumed. |
| `model_used` | `str` | Which LLM model was invoked. |

### 2.3. `EventMessage` — Any Component → Dashboard

Published for real-time UI updates. Streamed via the WebSocket Hub to the browser.

### 2.4. `ErrorMessage` — Catastrophic Failure Tracking

Published on unrecoverable failures. Includes `stack_trace`, `is_fatal` flag, and retry count for centralized error monitoring.

### 2.5. `MetricMessage` — Telemetry

Published for real-time cost and performance tracking. Contains `metric_name` (e.g., `llm_tokens_used`), `value`, `unit`, and dimensional `labels`.

### 2.6. `MoERouteRequest` / `MoERouteDecision` — Expert Routing

Request/response pair for the Mixture-of-Experts router. The request includes a task embedding vector and required skills; the response contains the selected expert role and a confidence score.

---

## 3. Topic Architecture

**Source**: [`messaging/topics.py`](../messaging/topics.py)

All topics are defined in the `KafkaTopics` class as a single source of truth, ensuring consistency between the Python agents and the Go backend.

### 3.1. Topic Map

| Topic Name | Partitions | Replication | Purpose |
| :--- | :--- | :--- | :--- |
| `ai-org-tasks` | 12 | 3 | Task dispatch from Orchestrator to all agents. |
| `ai-org-results` | 12 | 3 | Result reporting from agents back to Orchestrator. |
| `ai-org-events` | 6 | 3 | Lifecycle events for Dashboard/WebSocket streaming. |
| `ai-org-heartbeats` | 3 | 3 | Agent health monitoring heartbeats. |

### 3.2. Routing Strategy

The system uses a **single-topic-with-role-filtering** pattern rather than per-role topics. The `agent_role` field in `TaskMessage` is used by consumers to filter relevant messages. This simplifies topic management while maintaining logical separation.

---

## 4. Kafka Clients

**Source**: [`messaging/kafka_client.py`](../messaging/kafka_client.py)

### 4.1. `KafkaProducerClient`

**Producer Configuration** (real mode):

| Setting | Value | Rationale |
| :--- | :--- | :--- |
| `acks` | `all` | Wait for all replicas to acknowledge for durability. |
| `enable_idempotence` | `true` | Exactly-once producer semantics. |
| `max_in_flight_requests` | `1` | Preserves message ordering per partition. |
| `compression_type` | `gzip` | Reduces network bandwidth for large JSON payloads. |
| `retries` | `5` | Auto-retry on transient failures. |

**Methods**:
-   `publish(topic, value, key, headers)` — Raw bytes.
-   `publish_json(topic, data, key)` — Serialize dict to JSON.
-   `publish_model(topic, model, key)` — Serialize Pydantic model via `model_dump_json()`.

**Fallback**: If `kafka-python` is not installed or the broker is unreachable, the producer transparently switches to `_InMemoryBus`.

### 4.2. `KafkaConsumerClient`

**Consumer Configuration** (real mode):

| Setting | Value | Rationale |
| :--- | :--- | :--- |
| `enable_auto_commit` | `false` | Manual offset commits after successful processing. |
| `auto_offset_reset` | `earliest` | Process all unread messages on startup. |
| `max_poll_records` | `50` | Bounded batch size for predictable memory usage. |
| `session_timeout_ms` | `30000` | 30s session timeout for crash detection. |

**Consumption Patterns**:
-   `consume_one(timeout_ms)` — Non-blocking single-message poll.
-   `consume_loop(handler, dlq_topic, max_retries)` — Infinite loop with retry + DLQ routing.
-   `consume_stream()` — Async generator yielding parsed JSON dicts.

**Dead-Letter Queue (DLQ)**: When a message fails processing after `max_retries` attempts (with exponential backoff: 2s, 4s, 8s), it is automatically published to the configured DLQ topic for manual inspection.

**OpenTelemetry Integration**: Each consumed message is wrapped in a `tracer.start_as_current_span("kafka.consume")` span with messaging-system attributes for distributed tracing.

### 4.3. `KafkaAdminManager`

Manages topic creation on system startup. Called once by the Go backend or Python bootstrap to ensure all topics in `TOPIC_CONFIGS` exist. Idempotent — silently skips already-existing topics.

### 4.4. `_InMemoryBus` (Development Mock)

A simple in-process pub/sub bus using `asyncio.Queue` per topic. Features:
-   **Bounded Queue**: 10,000 messages per topic.
-   **Persistence**: Appends all messages to a JSONL file (`kafka_mock_bus.jsonl`) for recovery across restarts.
-   **Batch Consumption**: Supports multi-topic batch reads.
