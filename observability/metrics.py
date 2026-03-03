"""
Prometheus Metrics Registry
Centralized metrics definitions for the entire AI Organization system.
All Prometheus counters, histograms, and gauges are defined here.
Import `metrics` and call .inc(), .observe(), .set() anywhere.
"""

import time
from contextlib import contextmanager

import structlog

logger = structlog.get_logger(__name__)

# Try importing prometheus_client; gracefully degrade if not installed
try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        generate_latest,
        start_http_server,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed — metrics will be no-ops")


# ── Metric Stubs (no-op fallback) ─────────────────────────────────────────
class _NoOpMetric:
    """No-op metric used when prometheus_client is unavailable."""

    def labels(self, **kwargs):
        return self

    def inc(self, amount=1):
        pass

    def dec(self, amount=1):
        pass

    def set(self, value):
        pass

    def observe(self, value):
        pass

    def time(self):
        return _NoOpContextManager()


class _NoOpContextManager:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _metric(constructor, *args, **kwargs):
    """Create a real Prometheus metric or a no-op fallback."""
    if PROMETHEUS_AVAILABLE:
        try:
            return constructor(*args, **kwargs)
        except ValueError:
            # Already registered (happens in tests with module reload)
            return constructor(*args, **kwargs)
    return _NoOpMetric()


# ══════════════════════════════════════════════════════════════════════════
# AGENT METRICS
# ══════════════════════════════════════════════════════════════════════════

# Task execution counters
task_total = (
    _metric(
        Counter,
        "ai_org_task_total",
        "Total number of agent tasks executed",
        ["agent", "task_type", "status"],  # status: completed|failed|retrying
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)

# Task duration (per agent, per task type)
task_duration_seconds = (
    _metric(
        Histogram,
        "ai_org_task_duration_seconds",
        "Agent task execution duration in seconds",
        ["agent", "task_type"],
        buckets=[1, 5, 15, 30, 60, 120, 300, 600, 1800],
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)

# Agent queue depth (from Kafka consumer lag)
task_queue_depth = (
    _metric(
        Gauge,
        "ai_org_task_queue_depth",
        "Current number of pending tasks per agent",
        ["agent"],
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)

# Active tasks in flight
tasks_in_flight = (
    _metric(
        Gauge,
        "ai_org_tasks_in_flight",
        "Number of tasks currently being processed",
        ["agent"],
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)


# ══════════════════════════════════════════════════════════════════════════
# LLM METRICS
# ══════════════════════════════════════════════════════════════════════════

# Token usage
llm_tokens_total = (
    _metric(
        Counter,
        "ai_org_llm_tokens_total",
        "Total LLM tokens consumed",
        ["agent", "model", "direction"],  # direction: input|output
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)

# LLM call duration
llm_latency_seconds = (
    _metric(
        Histogram,
        "ai_org_llm_latency_seconds",
        "LLM API call duration in seconds",
        ["agent", "model"],
        buckets=[0.5, 1, 2, 5, 10, 20, 30, 60],
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)

# LLM call outcomes
llm_calls_total = (
    _metric(
        Counter,
        "ai_org_llm_calls_total",
        "Total LLM API calls",
        ["agent", "model", "status"],  # status: success|error|ratelimited
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)

# LLM cost tracking
llm_cost_usd_total = (
    _metric(
        Counter,
        "ai_org_llm_cost_usd_total",
        "Total LLM spend in USD",
        ["agent", "model"],
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)


# ══════════════════════════════════════════════════════════════════════════
# PROJECT METRICS
# ══════════════════════════════════════════════════════════════════════════

active_projects = (
    _metric(
        Gauge,
        "ai_org_active_projects",
        "Number of currently active projects",
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)

project_total = (
    _metric(
        Counter,
        "ai_org_project_total",
        "Total projects started",
        ["status"],  # status: completed|failed|in_progress
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)

project_duration_seconds = (
    _metric(
        Histogram,
        "ai_org_project_duration_seconds",
        "Full project lifecycle duration in seconds",
        buckets=[60, 300, 600, 1800, 3600, 7200],
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)

budget_utilization_pct = (
    _metric(
        Gauge,
        "ai_org_budget_utilization_pct",
        "Budget utilization percentage per project",
        ["project_id"],
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)

project_cost_usd_total = (
    _metric(
        Counter,
        "ai_org_project_cost_usd_total",
        "Total AWS + LLM cost per project",
        ["project_id"],
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)


# ══════════════════════════════════════════════════════════════════════════
# MoE ROUTER METRICS
# ══════════════════════════════════════════════════════════════════════════

moe_routing_total = (
    _metric(
        Counter,
        "ai_org_moe_routing_total",
        "Total MoE routing decisions",
        ["selected_expert", "routing_type"],  # routing_type: direct|scored|ensemble
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)

moe_routing_latency_ms = (
    _metric(
        Histogram,
        "ai_org_moe_routing_latency_ms",
        "MoE routing decision latency in milliseconds",
        buckets=[0.5, 1, 2, 5, 10, 25, 50],
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)

moe_routing_score = (
    _metric(
        Histogram,
        "ai_org_moe_routing_score",
        "MoE routing composite score distribution",
        buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)

moe_ensemble_total = (
    _metric(
        Counter,
        "ai_org_moe_ensemble_total",
        "Number of ensemble routing decisions",
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)


# ══════════════════════════════════════════════════════════════════════════
# KAFKA METRICS
# ══════════════════════════════════════════════════════════════════════════

kafka_publish_total = (
    _metric(
        Counter,
        "ai_org_kafka_publish_total",
        "Total Kafka messages published",
        ["topic", "status"],
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)

kafka_consume_total = (
    _metric(
        Counter,
        "ai_org_kafka_consume_total",
        "Total Kafka messages consumed",
        ["topic", "group"],
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)

kafka_consumer_lag = (
    _metric(
        Gauge,
        "ai_org_kafka_consumer_lag",
        "Kafka consumer group lag (pending messages)",
        ["topic", "group"],
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)

kafka_dlq_total = (
    _metric(
        Counter,
        "ai_org_kafka_dlq_total",
        "Messages sent to dead-letter queue",
        ["topic"],
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)


# ══════════════════════════════════════════════════════════════════════════
# SYSTEM HEALTH METRICS
# ══════════════════════════════════════════════════════════════════════════

system_errors_total = (
    _metric(
        Counter,
        "ai_org_system_errors_total",
        "Total system errors",
        ["component", "error_type"],
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)

agent_restarts_total = (
    _metric(
        Counter,
        "ai_org_agent_restarts_total",
        "Total agent service restarts",
        ["agent"],
    )
    if PROMETHEUS_AVAILABLE
    else _NoOpMetric()
)


# ══════════════════════════════════════════════════════════════════════════
# HELPER CONTEXT MANAGERS
# ══════════════════════════════════════════════════════════════════════════


@contextmanager
def track_task(agent: str, task_type: str):
    """
    Context manager to track task duration and update counters.

    Usage:
        with track_task("CEO", "strategy"):
            result = await ceo_agent.run(...)
    """
    tasks_in_flight.labels(agent=agent).inc()
    start = time.monotonic()
    status = "completed"
    try:
        yield
    except Exception as e:
        status = "failed"
        system_errors_total.labels(component=agent, error_type=type(e).__name__).inc()
        raise
    finally:
        duration = time.monotonic() - start
        tasks_in_flight.labels(agent=agent).dec()
        task_total.labels(agent=agent, task_type=task_type, status=status).inc()
        task_duration_seconds.labels(agent=agent, task_type=task_type).observe(duration)


@contextmanager
def track_llm_call(agent: str, model: str):
    """
    Context manager to track LLM call latency and outcome.

    Usage:
        with track_llm_call("CEO", "gpt-4-turbo-preview") as tracker:
            response = await openai_client.chat.completions.create(...)
            tracker.record_tokens(input_tokens=100, output_tokens=200, cost=0.01)
    """
    start = time.monotonic()
    status = "success"

    class _Tracker:
        def record_tokens(self, input_tokens: int, output_tokens: int, cost_usd: float):
            llm_tokens_total.labels(agent=agent, model=model, direction="input").inc(
                input_tokens
            )
            llm_tokens_total.labels(agent=agent, model=model, direction="output").inc(
                output_tokens
            )
            llm_cost_usd_total.labels(agent=agent, model=model).inc(cost_usd)

    tracker = _Tracker()
    try:
        yield tracker
    except Exception:
        status = "error"
        raise
    finally:
        duration = time.monotonic() - start
        llm_latency_seconds.labels(agent=agent, model=model).observe(duration)
        llm_calls_total.labels(agent=agent, model=model, status=status).inc()


def start_metrics_server(port: int = 9090):
    """Expose Prometheus /metrics endpoint."""
    if PROMETHEUS_AVAILABLE:
        start_http_server(port)
        logger.info("Prometheus metrics server started", port=port)
    else:
        logger.warning("prometheus_client not available — metrics server not started")


def get_metrics_text() -> str:
    """Return current metrics in Prometheus text format."""
    if PROMETHEUS_AVAILABLE:
        return generate_latest().decode("utf-8")
    return "# prometheus_client not available\n"
