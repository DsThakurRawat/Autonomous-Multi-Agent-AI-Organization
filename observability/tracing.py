"""
Distributed Tracing - OpenTelemetry Setup
Provides a unified tracer that propagates context across all agents,
Kafka messages, and HTTP calls. Compatible with Jaeger and AWS X-Ray.
"""

import os
import functools
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Callable, Dict, Optional
import structlog

logger = structlog.get_logger(__name__)

# Try OpenTelemetry - graceful degradation if not installed
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.propagate import inject, extract
    from opentelemetry.trace import Status, StatusCode, SpanKind

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.warning("opentelemetry SDK not installed - tracing will be no-ops")


# -- No-Op Tracer Stubs ----------------------------------------------------─
class _NoOpSpan:
    def set_attribute(self, key, value):
        pass

    def set_status(self, *args, **kwargs):
        pass

    def record_exception(self, exc):
        pass

    def add_event(self, name, attributes=None):
        pass

    def get_span_context(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _NoOpTracer:
    def start_span(self, name, **kwargs):
        return _NoOpSpan()

    def start_as_current_span(self, name, **kwargs):
        return _NoOpContextManager()


class _NoOpContextManager:
    def __init__(self):
        self._span = _NoOpSpan()

    def __enter__(self):
        return self._span

    def __exit__(self, *args):
        pass

    async def __aenter__(self):
        return self._span

    async def __aexit__(self, *args):
        pass


# -- Tracer Initialization --------------------------------------------------
_tracer = None


def init_tracer(
    service_name: str = "ai-org",
    otlp_endpoint: Optional[str] = None,
) -> Any:
    """
    Initialize the OpenTelemetry tracer.
    Call once at application startup.

    Args:
        service_name:  Service name tag (e.g. "ceo-agent", "orchestrator")
        otlp_endpoint: OTLP collector endpoint (default: OTEL_EXPORTER_OTLP_ENDPOINT env var)
    """
    global _tracer

    if not OTEL_AVAILABLE:
        _tracer = _NoOpTracer()
        return _tracer

    endpoint = otlp_endpoint or os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317"
    )

    resource = Resource(
        attributes={
            "service.name": service_name,
            "service.version": "2.0.0",
            "deployment.env": os.getenv("ENVIRONMENT", "development"),
        }
    )

    provider = TracerProvider(resource=resource)

    try:
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info("OpenTelemetry OTLP exporter configured", endpoint=endpoint)
    except Exception as e:
        logger.warning("OTLP exporter failed, using no-op", error=str(e))

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name, "2.0.0")

    logger.info("OpenTelemetry tracer initialized", service=service_name)
    return _tracer


def get_tracer() -> Any:
    """Get the global tracer (lazy init with defaults if not initialized)."""
    global _tracer
    if _tracer is None:
        init_tracer()
    return _tracer


# -- Trace Context Propagation ----------------------------------------------─
def inject_trace_context(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Inject current trace context into headers dict.
    Use when publishing to Kafka or making HTTP calls.
    """
    if not OTEL_AVAILABLE:
        return headers
    inject(headers)
    return headers


def extract_trace_context(headers: Dict[str, str]):
    """
    Extract trace context from incoming headers.
    Use when consuming from Kafka or receiving HTTP requests.
    Returns an OTel context object (or None in no-op mode).
    """
    if not OTEL_AVAILABLE:
        return None
    return extract(headers)


# -- Span Context Manager ----------------------------------------------------
@contextmanager
def create_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    parent_context=None,
    kind: str = "internal",  # "internal" | "server" | "client" | "producer" | "consumer"
):
    """
    Context manager that creates a named span.

    Usage:
        with create_span("ceo_agent.run", {"agent": "CEO", "project_id": pid}) as span:
            result = await do_work()
            span.set_attribute("output.features", 5)
    """
    tracer = get_tracer()

    if not OTEL_AVAILABLE:
        yield _NoOpSpan()
        return

    span_kind_map = {
        "internal": SpanKind.INTERNAL,
        "server": SpanKind.SERVER,
        "client": SpanKind.CLIENT,
        "producer": SpanKind.PRODUCER,
        "consumer": SpanKind.CONSUMER,
    }
    otel_kind = span_kind_map.get(kind, SpanKind.INTERNAL)

    with tracer.start_as_current_span(
        name, context=parent_context, kind=otel_kind
    ) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(
                    key,
                    (
                        str(value)
                        if not isinstance(value, (str, int, float, bool))
                        else value
                    ),
                )
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise


@asynccontextmanager
async def async_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    parent_context=None,
):
    """Async version of create_span."""
    with create_span(name, attributes, parent_context) as span:
        yield span


# -- Decorator ------------------------------------------------------------─
def traced(span_name: Optional[str] = None, attributes: Optional[Dict] = None):
    """
    Decorator to automatically trace a function.

    Usage:
        @traced("ceo_agent.analyze_idea", {"agent": "CEO"})
        async def analyze_idea(self, idea: str):
            ...
    """

    def decorator(func: Callable) -> Callable:
        name = span_name or f"{func.__module__}.{func.__qualname__}"

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            async with async_span(name, attributes):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with create_span(name, attributes):
                return func(*args, **kwargs)

        import asyncio as _asyncio

        if _asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def get_current_trace_id() -> Optional[str]:
    """Get the current trace ID as a hex string (for logging correlation)."""
    if not OTEL_AVAILABLE:
        return None
    ctx = trace.get_current_span().get_span_context()
    if ctx and ctx.is_valid:
        return format(ctx.trace_id, "032x")
    return None
