"""
orchestrator/kafka_dispatcher.py
Kafka-based task dispatcher — sends tasks to agent topics and waits for results.
Falls back gracefully when Kafka is not available.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog

from messaging.kafka_client import KafkaProducerClient, KafkaConsumerClient
from messaging.schemas import TaskMessage, ResultMessage, EventMessage
from messaging.topics import KafkaTopics

log = structlog.get_logger(__name__)

# How long to wait for a result before timing out (seconds)
RESULT_TIMEOUT = int(__import__("os").getenv("KAFKA_RESULT_TIMEOUT", "120"))


class KafkaDispatcher:
    """
    Dispatch a task to the correct agent topic, then wait for its result.
    Usage::

        dispatcher = KafkaDispatcher()
        result = await dispatcher.dispatch_and_wait(task_msg, agent_role="Engineer_Backend")
    """

    def __init__(self) -> None:
        self._producer: Optional[KafkaProducerClient] = None
        self._consumer: Optional[KafkaConsumerClient] = None
        self._pending: dict[str, asyncio.Future] = {}
        self._consumer_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------ #
    #  Lifecycle                                                           #
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """Create producer/consumer and start the background result loop."""
        self._producer = KafkaProducerClient()
        result_topic = KafkaTopics.task_result()
        self._consumer = KafkaConsumerClient(
            topics=[result_topic],
            group_id="orchestrator-results",
        )
        self._consumer_task = asyncio.create_task(
            self._consume_results_loop(), name="kafka-results-consumer"
        )
        log.info("kafka_dispatcher.started", result_topic=result_topic)

    async def stop(self) -> None:
        """Graceful shutdown."""
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        if self._consumer:
            await self._consumer.close()
        if self._producer:
            await self._producer.close()
        log.info("kafka_dispatcher.stopped")

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    async def dispatch_and_wait(
        self,
        task_msg: TaskMessage,
        agent_role: str,
        timeout: float = RESULT_TIMEOUT,
    ) -> ResultMessage:
        """
        Publish *task_msg* to the agent's topic and block until the result arrives
        or *timeout* seconds elapse.

        Returns the ``ResultMessage`` from the agent.
        Raises ``asyncio.TimeoutError`` on timeout.
        """
        if self._producer is None:
            raise RuntimeError("KafkaDispatcher.start() was not awaited.")

        loop = asyncio.get_event_loop()
        fut: asyncio.Future[ResultMessage] = loop.create_future()
        self._pending[task_msg.task_id] = fut

        topic = KafkaTopics.agent_task_topic(agent_role)
        await self._producer.publish_model(topic, task_msg)
        log.info(
            "kafka_dispatcher.task_dispatched",
            task_id=task_msg.task_id,
            agent_role=agent_role,
            topic=topic,
        )

        try:
            result = await asyncio.wait_for(fut, timeout=timeout)
        finally:
            self._pending.pop(task_msg.task_id, None)

        return result

    # ------------------------------------------------------------------ #
    #  Internal                                                            #
    # ------------------------------------------------------------------ #

    async def _consume_results_loop(self) -> None:
        """Background task: reads ResultMessages and resolves waiting futures."""
        assert self._consumer is not None
        async for raw in self._consumer.consume_stream():
            try:
                result = ResultMessage.model_validate(raw)
            except Exception as exc:
                log.warning("kafka_dispatcher.bad_result_msg", error=str(exc))
                continue

            fut = self._pending.get(result.task_id)
            if fut and not fut.done():
                fut.set_result(result)
            else:
                log.debug("kafka_dispatcher.unmatched_result", task_id=result.task_id)


class KafkaEventPublisher:
    """
    Thin wrapper to publish EventMessage objects to the project-events topic.
    Used by the orchestrator to stream progress to the dashboard.
    """

    def __init__(self) -> None:
        self._producer: Optional[KafkaProducerClient] = None

    async def start(self) -> None:
        self._producer = KafkaProducerClient()

    async def stop(self) -> None:
        if self._producer:
            await self._producer.close()

    async def publish(self, event: EventMessage) -> None:
        if self._producer is None:
            raise RuntimeError("KafkaEventPublisher.start() was not awaited.")
        topic = KafkaTopics.project_events()
        await self._producer.publish_model(topic, event)

    # Convenience factory ------------------------------------------------
    @staticmethod
    def make_event(
        project_id: str,
        event_type: str,
        data: dict[str, Any],
        agent_role: str = "orchestrator",
    ) -> EventMessage:
        return EventMessage(
            event_id=str(uuid.uuid4()),
            project_id=project_id,
            agent_role=agent_role,
            event_type=event_type,
            data=data,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
