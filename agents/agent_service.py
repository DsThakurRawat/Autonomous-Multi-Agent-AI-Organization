"""
Agent Service - Kafka Consumer Entrypoint
Each agent microservice runs this module.
The AGENT_ROLE env var determines which agent class is loaded
and which Kafka topic is consumed.

Flow:
  Kafka topic (ai-org.tasks.<role>)
    → TaskMessage consumed
    → agent.execute_task() called
    → ResultMessage published to ai-org.results.<project_id>
    → EventMessage published to ai-org.events.<project_id>
"""

import asyncio
import os
import signal
import time
import traceback
from typing import Any, cast

import structlog

from agents.model_registry import get_default
from agents.roles import AgentRole
from messaging.kafka_client import KafkaConsumerClient, KafkaProducerClient
from messaging.schemas import EventMessage, ResultMessage, TaskMessage
from messaging.topics import KafkaTopics
from utils.logging_config import setup_logging

logger = structlog.get_logger(__name__)


# -- Agent Role → (Module, Class) Mapping ------------------------------------─
AGENT_REGISTRY: dict[str, tuple] = {
    AgentRole.CEO: ("agents.ceo_agent", "CEOAgent"),
    AgentRole.CTO: ("agents.cto_agent", "CTOAgent"),
    AgentRole.ENGINEER_BACKEND: ("agents.backend_agent", "BackendAgent"),
    AgentRole.ENGINEER_FRONTEND: ("agents.frontend_agent", "FrontendAgent"),
    AgentRole.QA: ("agents.qa_agent", "QAAgent"),
    AgentRole.DEVOPS: ("agents.devops_agent", "DevOpsAgent"),
    AgentRole.FINANCE: ("agents.finance_agent", "FinanceAgent"),
}


def _build_llm_client(llm_config: dict, agent_role: str):
    """
    Build the correct LLM client from the llm_config injected into the
    Kafka TaskMessage by the Go Orchestrator. Falls back to model_registry
    defaults + server env vars if no config is provided.

    Returns: (client, model_name, provider)
    """
    # Fill in defaults from model_registry if the payload is missing config
    defaults = get_default(agent_role)
    provider = llm_config.get("provider") or defaults["provider"]
    api_key = llm_config.get("api_key") or ""
    model = llm_config.get("model") or defaults["model"]

    # If no user key was injected, try server env vars as fallback
    if not api_key and provider != "bedrock":
        import os

        env_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
        }
        api_key = os.getenv(env_map.get(provider, "GOOGLE_API_KEY"), "")

    if not api_key and provider != "bedrock":
        logger.warning("No API key found - running in mock mode", provider=provider)
        return None, model, provider

    try:
        if provider == "openai":
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            logger.info("OpenAI client built", model=model)
            return client, model, provider

        elif provider == "anthropic":
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            logger.info("Anthropic client built", model=model)
            return client, model, provider

        elif provider == "google":
            from google import genai

            client = genai.Client(api_key=api_key)
            logger.info("Gemini client built", model=model)
            return client, model, provider

        elif provider == "bedrock":
            import os

            import boto3

            # boto3 automatically uses AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY from the environment
            region = os.getenv("AWS_REGION", "us-east-1")
            try:
                client = boto3.client("bedrock-runtime", region_name=region)
                logger.info("Bedrock client built", model=model, region=region)
                return client, model, provider
            except Exception as e:
                logger.warning(
                    "Failed to initialize Bedrock client, falling back to mock mode",
                    error=str(e),
                )
                return None, model, provider

        else:
            logger.warning("Unknown provider, mock mode", provider=provider)
            return None, model, provider

    except ImportError as e:
        logger.error("LLM package not installed", provider=provider, error=str(e))
        return None, model, provider


def _load_agent(role: str, llm_client=None):
    """Dynamically import and instantiate the agent for the given role."""
    if role not in AGENT_REGISTRY:
        raise ValueError(
            f"Unknown agent role: {role}. Known: {list(AGENT_REGISTRY.keys())}"
        )

    module_path, class_name = AGENT_REGISTRY[role]
    import importlib

    module = importlib.import_module(module_path)
    AgentClass = getattr(module, class_name)

    # Instantiate the agent
    try:
        agent = AgentClass(llm_client=llm_client)
    except TypeError:
        # Fallback if the agent doesn't accept llm_client in init
        agent = AgentClass()

    logger.info("Agent loaded", role=role, class_name=class_name)
    return agent


class AgentMicroservice:
    """
    Wraps an agent in a Kafka consumer loop.
    Handles graceful shutdown via SIGTERM/SIGINT.
    """

    def __init__(self):
        self.role = os.getenv("AGENT_ROLE", AgentRole.CEO)
        self.topic = os.getenv(
            "KAFKA_CONSUMER_TOPIC"
        ) or KafkaTopics.task_topic_for_role(self.role)
        self.group_id = os.getenv("KAFKA_CONSUMER_GROUP", f"{self.role.lower()}-group")
        self.running = True
        self.agent: Any | None = None
        self.consumer: KafkaConsumerClient | None = None
        self.producer: KafkaProducerClient | None = None
        self._tasks_done = 0
        self._tasks_failed = 0

    async def start(self):
        setup_logging()
        logger.info("Agent microservice starting", role=self.role, topic=self.topic)

        # Wire up signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._shutdown)

        # Agent is loaded once - LLM client is resolved per-task from Kafka payload
        self.agent = _load_agent(self.role)
        self.producer = KafkaProducerClient()
        self.consumer = KafkaConsumerClient(
            topics=[self.topic],
            group_id=self.group_id,
        )

        logger.info(
            "Agent ready", role=self.role, topic=self.topic, mode="per-task-key"
        )

        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        health_task = asyncio.create_task(self._health_server())

        await self._consume_loop()

        heartbeat_task.cancel()
        health_task.cancel()

    def _shutdown(self, *args):
        logger.info("Shutdown signal received", role=self.role)
        self.running = False
        consumer = self.consumer
        if consumer:
            consumer.stop()

    async def _heartbeat_loop(self):
        """Periodically ping the Go Health Monitor via Kafka."""
        import socket

        pod_id = socket.gethostname()

        while self.running:
            try:
                producer = self.producer
                if producer:
                    hb_topic = KafkaTopics.heartbeat_topic()
                    payload = {
                        "agent_role": self.role,
                        "pod_id": pod_id,
                        "status": "healthy",
                    }
                    await producer.publish_json(
                        hb_topic, payload, key=f"{self.role}-{pod_id}"
                    )
            except Exception as e:
                logger.error("Heartbeat failed", error=str(e))

            await asyncio.sleep(10)

    async def _health_server(self, port: int = 8000):
        """Native asyncio HTTP server to reply to Docker healthchecks."""

        async def handle_request(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ):
            import contextlib

            with contextlib.suppress(Exception):
                request_line = await asyncio.wait_for(
                    reader.readuntil(b"\r\n"), timeout=1.0
                )
                if b"GET /health" in request_line:
                    response = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"
                else:
                    response = (
                        b"HTTP/1.1 404 Not Found\r\nContent-Length: 9\r\n\r\nNot Found"
                    )
                writer.write(response)
                await writer.drain()
            writer.close()

        server = await asyncio.start_server(handle_request, "0.0.0.0", port)
        logger.info("Health check server listening", port=port)
        async with server:
            await server.serve_forever()

    async def _consume_loop(self):
        """Main consumer loop - pull TaskMessages, process, publish ResultMessage."""
        logger.info("Consumer loop started", role=self.role)

        consumer = self.consumer
        if not consumer:
            logger.error("Consumer not initialized")
            return

        async for raw_msg in consumer.consume_stream():
            if not self.running:
                break

            try:
                task_msg = TaskMessage(**raw_msg)
            except Exception as e:
                _ = str(raw_msg)
                logger.error(
                    "Failed to parse TaskMessage",
                    error=str(e),
                    raw_preview=(
                        cast(str, str(raw_msg))[:500]
                        if len(cast(str, str(raw_msg))) > 500
                        else cast(str, str(raw_msg))
                    ),
                )
                await self._emit_error_event(
                    project_id=(
                        str(raw_msg.get("project_id", "unknown"))
                        if isinstance(raw_msg, dict)
                        else "unknown"
                    ),
                    message=f"Agent fallback: Failed to parse task message for {self.role}",
                    error=str(e),
                )

                # Send bad payload to Dead Letter Queue (DLQ)
                if self.producer:
                    dlq_payload = {
                        "original_topic": self.topic,
                        "error": str(e),
                        "raw_message": raw_msg,
                    }
                    try:
                        producer = self.producer
                        assert producer is not None
                        await producer.publish_json(
                            "ai-org-dlq", dlq_payload, key="parse-error"
                        )
                    except Exception as pub_err:
                        logger.error("Failed to publish to DLQ", error=str(pub_err))
                continue

            if task_msg.agent_role != self.role:
                # In a shared topic architecture, ignore tasks meant for other expert agents
                continue

            logger.info(
                "Task received",
                task_id=task_msg.task_id,
                task_name=task_msg.task_name,
                role=self.role,
                trace_id=task_msg.trace_id,
            )

            await self._process_task(task_msg)

        logger.info(
            "Consumer loop exited",
            role=self.role,
            done=self._tasks_done,
            failed=self._tasks_failed,
        )

    async def _process_task(self, task_msg: TaskMessage):
        """Execute one task and publish the result."""
        start_ms = time.time() * 1000

        # -- Resolve LLM client per-task from Kafka payload ----------------
        # The Go Orchestrator injects the resolved llm_config based on the
        # user's Settings preferences (or platform defaults as fallback).
        llm_config = task_msg.input_data.get("llm_config", {})
        llm_client, model_name, provider = _build_llm_client(llm_config, self.role)

        # Patch the resolved client onto the agent instance for this task only.
        # This is safe - agent pods process tasks sequentially per role.
        if self.agent is None:
            raise RuntimeError("Agent not initialized")
        agent = self.agent
        assert agent is not None
        agent.llm_client = llm_client
        agent.model_name = model_name
        agent.provider = provider
        # Instantiate a fresh task-scoped agent to prevent race conditions
        # if tasks were ever processed concurrently in the event loop.
        agent_instance = _load_agent(self.role, llm_client=llm_client)
        agent_instance.model_name = model_name
        agent_instance.provider = provider

        logger.info(
            "Task LLM resolved",
            role=self.role,
            provider=provider,
            model=model_name,
            mode="live" if llm_client else "mock",
        )

        # Emit task_start event
        await self._emit_event(
            project_id=task_msg.project_id,
            event_type="task_start",
            message=f"[{self.role}] Starting: {task_msg.task_name} ({provider}/{model_name})",
            data={
                "task_id": task_msg.task_id,
                "provider": provider,
                "model": model_name,
            },
            level="info",
            trace_id=task_msg.trace_id,
        )

        try:
            # Build a minimal task object the agent understands
            class _TaskProxy:
                """Lightweight proxy so agent code sees task.name, task.id, etc."""

                id = task_msg.task_id
                name = task_msg.task_name
                task_type = task_msg.task_type
                agent_role = task_msg.agent_role
                input_data = task_msg.input_data
                retry_count = task_msg.retry_count
                max_retries = task_msg.max_retries
                status = "running"

            agent = self.agent
            if not agent:
                raise RuntimeError("Agent not initialized")
            output = await agent_instance.execute_task(
                task=_TaskProxy(),
                context=_build_minimal_context(task_msg),
            )

            duration_ms = int(time.time() * 1000 - start_ms)
            self._tasks_done += 1

            # Publish ResultMessage
            result = ResultMessage(
                task_id=task_msg.task_id,
                task_name=task_msg.task_name,
                agent_role=self.role,
                project_id=task_msg.project_id,
                status="completed",
                output_data=(
                    output if isinstance(output, dict) else {"result": str(output)}
                ),
                duration_ms=duration_ms,
                cost_usd=(
                    output.get("_cost_usd", 0.0) if isinstance(output, dict) else 0.0
                ),
                tokens_used=(
                    output.get("_tokens_used", 0) if isinstance(output, dict) else 0
                ),
                model_used=(
                    output.get("_model_used") if isinstance(output, dict) else None
                ),
                trace_id=task_msg.trace_id,
            )

            producer = self.producer
            if not producer:
                raise RuntimeError("Producer not initialized") from None

            result_topic = KafkaTopics.results_topic(task_msg.project_id)
            await producer.publish_model(result_topic, result, key=task_msg.task_id)

            # Emit completion event
            await self._emit_event(
                project_id=task_msg.project_id,
                event_type="task_complete",
                message=f"[{self.role}] Completed: {task_msg.task_name} ({duration_ms}ms)",
                data={"task_id": task_msg.task_id, "duration_ms": duration_ms},
                level="success",
                trace_id=task_msg.trace_id,
            )

            logger.info(
                "Task completed",
                task_id=task_msg.task_id,
                duration_ms=duration_ms,
                role=self.role,
            )

        except Exception as e:
            duration_ms = int(time.time() * 1000 - start_ms)
            self._tasks_failed += 1
            err_str = str(e)

            logger.error(
                "Task failed",
                task_id=task_msg.task_id,
                error=err_str,
                trace=cast(str, traceback.format_exc())[-500:],
                role=self.role,
            )

            is_final_failure = task_msg.retry_count >= task_msg.max_retries

            result = ResultMessage(
                task_id=task_msg.task_id,
                task_name=task_msg.task_name,
                agent_role=self.role,
                project_id=task_msg.project_id,
                status="failed" if not is_final_failure else "fatal",
                error_message=err_str,
                duration_ms=duration_ms,
                trace_id=task_msg.trace_id,
            )

            if self.producer is None:
                raise RuntimeError("Producer not initialized") from None

            if is_final_failure:
                dlq_payload = {
                    "task_id": task_msg.task_id,
                    "error": err_str,
                    "final_failure": True,
                    "trace_id": task_msg.trace_id,
                    "original_payload": task_msg.model_dump(),
                }
                await self.producer.publish_json(
                    "ai-org-dlq", dlq_payload, key=task_msg.task_id
                )
            else:
                result_topic = KafkaTopics.results_topic(task_msg.project_id)
                await self.producer.publish_model(
                    result_topic, result, key=task_msg.task_id
                )

            await self._emit_event(
                project_id=task_msg.project_id,
                event_type="task_failed",
                message=f"[{self.role}] Failed: {task_msg.task_name} — {cast(str, err_str)[:100]}",
                data={"task_id": task_msg.task_id, "error": err_str},
                level="error",
                trace_id=task_msg.trace_id,
            )

    async def _emit_error_event(
        self,
        project_id: str,
        message: str,
        error: str,
        data: dict[str, Any] | None = None,
        trace_id: str = "",
    ):
        """Standardized error event emitter for parsing/system failures."""
        await self._emit_event(
            project_id=project_id,
            event_type="agent_system_error",
            message=message,
            data={"error": error, **(data or {})},
            level="error",
            trace_id=trace_id,
        )

    async def _emit_event(
        self,
        project_id: str,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
        level: str = "info",
        trace_id: str = "",
    ):
        """Publish an EventMessage to the project's event topic."""
        try:
            event = EventMessage(
                event_type=event_type,
                agent_role=self.role,
                project_id=project_id,
                message=message,
                data=data or {},
                level=level,
                trace_id=trace_id,
            )
            topic = KafkaTopics.events_topic(project_id)
            producer = self.producer
            if producer is not None:
                await producer.publish_model(topic, event, key=event_type)
        except Exception as e:
            logger.warning("Failed to emit event", error=str(e))


def _build_minimal_context(task_msg: TaskMessage):
    """Build a minimal context object that agent.execute_task() expects."""

    class _MinimalContext:
        project_id = task_msg.project_id
        task = None  # set by _TaskProxy above

        async def emit_event(self, event):
            pass  # events are handled by AgentMicroservice._emit_event

        class Memory:
            project_config = task_msg.input_data.get("project_config", {})
            business_plan = task_msg.input_data.get("business_plan", {})
            architecture = task_msg.input_data.get("architecture", {})

            @staticmethod
            def snapshot():
                return task_msg.input_data

        class DecisionLog:
            @staticmethod
            def summary():
                return {}

            @staticmethod
            def log(*args, **kwargs):
                pass

        class CostLedger:
            @staticmethod
            def report():
                return {}

        class Artifacts:
            _artifacts = []  # noqa: RUF012

            @staticmethod
            def get_deployment_url():
                return None

            @staticmethod
            def manifest():
                return []

            @staticmethod
            def save(*args, **kwargs):
                pass

            @staticmethod
            def save_code_file(*args, **kwargs):
                pass

        memory = Memory
        decision_log = DecisionLog
        cost_ledger = CostLedger
        artifacts = Artifacts

    return _MinimalContext()


async def main():
    service = AgentMicroservice()
    await service.start()


if __name__ == "__main__":
    asyncio.run(main())
