"""
Health Check Endpoints
Standardized health check responses for Kubernetes liveness/readiness probes
and external monitoring systems.
"""

from datetime import UTC, datetime
import os
import time
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_start_time = time.time()


class HealthStatus:
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth:
    """Health check result for a single dependency."""

    def __init__(
        self, name: str, status: str, latency_ms: float = 0, details: dict | None = None
    ):
        self.name = name
        self.status = status
        self.latency_ms = latency_ms
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "latency_ms": round(self.latency_ms, 2),
            "details": self.details,
        }


async def check_redis(redis_client=None) -> ComponentHealth:
    """Ping Redis and measure latency."""
    if redis_client is None:
        return ComponentHealth(
            "redis", HealthStatus.DEGRADED, details={"reason": "not_configured"}
        )

    start = time.monotonic()
    try:
        await redis_client.ping()
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth("redis", HealthStatus.HEALTHY, latency_ms=latency)
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            "redis",
            HealthStatus.UNHEALTHY,
            latency_ms=latency,
            details={"error": str(e)},
        )


async def check_postgres(db_session=None) -> ComponentHealth:
    """Query PostgreSQL and measure latency."""
    if db_session is None:
        return ComponentHealth(
            "postgres", HealthStatus.DEGRADED, details={"reason": "not_configured"}
        )

    start = time.monotonic()
    try:
        await db_session.execute("SELECT 1")
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth("postgres", HealthStatus.HEALTHY, latency_ms=latency)
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            "postgres",
            HealthStatus.UNHEALTHY,
            latency_ms=latency,
            details={"error": str(e)},
        )


async def check_kafka(bootstrap_servers: str | None = None) -> ComponentHealth:
    """Check Kafka connectivity."""
    servers = bootstrap_servers or os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
    )
    mock_mode = os.getenv("KAFKA_MOCK", "false").lower() == "true"

    if mock_mode:
        return ComponentHealth("kafka", HealthStatus.HEALTHY, details={"mode": "mock"})

    start = time.monotonic()
    try:
        import socket

        host, port_str = servers.split(":") if ":" in servers else (servers, "9092")
        port = int(port_str)
        sock = socket.create_connection((host, port), timeout=2)
        sock.close()
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            "kafka",
            HealthStatus.HEALTHY,
            latency_ms=latency,
            details={"servers": servers},
        )
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentHealth(
            "kafka",
            HealthStatus.DEGRADED,
            latency_ms=latency,
            details={"error": str(e), "servers": servers},
        )


def build_health_response(
    service_name: str,
    version: str = "2.0.0",
    component_checks: dict[str, ComponentHealth] | None = None,
    extra_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a standardized health response.
    Aggregates component statuses: if any UNHEALTHY → overall UNHEALTHY.
    """
    components = component_checks or {}
    statuses = [c.status for c in components.values()]

    if HealthStatus.UNHEALTHY in statuses:
        overall = HealthStatus.UNHEALTHY
    elif HealthStatus.DEGRADED in statuses:
        overall = HealthStatus.DEGRADED
    else:
        overall = HealthStatus.HEALTHY

    uptime_seconds = int(time.time() - _start_time)

    return {
        "status": overall,
        "service": service_name,
        "version": version,
        "timestamp": datetime.now(UTC).isoformat() + "Z",
        "uptime_seconds": uptime_seconds,
        "components": {name: c.to_dict() for name, c in components.items()},
        **(extra_info or {}),
    }


def get_readiness_response(ready: bool, reason: str = "") -> dict[str, Any]:
    """
    Kubernetes readiness probe response.
    Returns 200 if ready, 503 if not.
    """
    return {
        "ready": ready,
        "reason": reason,
        "timestamp": datetime.now(UTC).isoformat() + "Z",
    }


def get_liveness_response() -> dict[str, Any]:
    """
    Kubernetes liveness probe response.
    Always returns 200 as long as the process is running.
    """
    return {
        "alive": True,
        "pid": os.getpid(),
        "timestamp": datetime.now(UTC).isoformat() + "Z",
    }
