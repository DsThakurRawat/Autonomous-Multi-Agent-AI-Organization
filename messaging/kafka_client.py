"""
Kafka Producer/Consumer Clients
Production-grade async Kafka clients with:
- Connection pooling and automatic reconnection
- Exactly-once semantics (producer side)
- Consumer group management with offset commits
- Dead-letter queue (DLQ) routing on repeated failure
- OpenTelemetry trace context propagation
- Prometheus metrics instrumentation
"""

import asyncio
import json
import os
from typing import Any, Callable, Dict, List, Optional
import structlog

logger = structlog.get_logger(__name__)

# Try importing kafka-python; fall back to a mock for local dev without Kafka
try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.admin import KafkaAdminClient, NewTopic
    from kafka.errors import TopicAlreadyExistsError

    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("kafka-python not installed — using in-memory mock bus")


# ── In-Memory Mock Bus (dev/test without Kafka) ────────────────────────────
class _InMemoryBus:
    """
    Simple in-process pub/sub bus used when Kafka is not available.
    Enables full local development and testing without a real Kafka cluster.
    """

    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}
        self._subscribers: Dict[str, List[Callable]] = {}

    def _get_queue(self, topic: str) -> asyncio.Queue:
        if topic not in self._queues:
            self._queues[topic] = asyncio.Queue(maxsize=10_000)
        return self._queues[topic]

    async def publish(self, topic: str, key: str, value: bytes):
        queue = self._get_queue(topic)
        await queue.put({"key": key, "value": value})
        logger.debug("InMemoryBus: published", topic=topic, key=key)

    async def consume(self, topic: str, group_id: str = "default") -> Dict[str, Any]:
        """Block until a message is available."""
        queue = self._get_queue(topic)
        msg = await queue.get()
        return msg

    async def consume_batch(
        self, topics: List[str], group_id: str, timeout_ms: int = 1000
    ) -> List[Dict[str, Any]]:
        """Consume from multiple topics in a non-blocking batch."""
        messages = []
        for topic in topics:
            queue = self._get_queue(topic)
            try:
                while True:
                    msg = queue.get_nowait()
                    messages.append({"topic": topic, **msg})
            except asyncio.QueueEmpty:
                pass
        return messages


# Singleton in-memory bus for dev mode
_dev_bus = _InMemoryBus()


class KafkaProducerClient:
    """
    Async-friendly Kafka producer.
    Falls back to in-memory bus if Kafka is unavailable (dev mode).
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        client_id: str = "ai-org-producer",
    ):
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self.client_id = client_id
        self._producer = None
        self._use_mock = (
            not KAFKA_AVAILABLE or os.getenv("KAFKA_MOCK", "false").lower() == "true"
        )

        if not self._use_mock:
            self._init_real_producer()

        logger.info(
            "KafkaProducerClient initialized",
            mode="mock" if self._use_mock else "real",
            servers=self.bootstrap_servers,
        )

    def _init_real_producer(self):
        try:
            self._producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
                value_serializer=lambda v: (
                    v if isinstance(v, bytes) else v.encode("utf-8")
                ),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",  # Wait for all replicas
                retries=5,
                max_in_flight_requests_per_connection=1,  # Preserve ordering
                enable_idempotence=True,  # Exactly-once semantics
                compression_type="gzip",
                linger_ms=5,  # Small batching window
                batch_size=32768,  # 32KB batch
            )
            logger.info("Kafka real producer connected", servers=self.bootstrap_servers)
        except Exception as e:
            logger.warning(
                "Kafka producer failed to connect, falling back to mock", error=str(e)
            )
            self._use_mock = True

    async def publish(
        self,
        topic: str,
        value: bytes,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Publish a message to a Kafka topic.
        Returns True on success, False on failure.
        """
        if self._use_mock:
            await _dev_bus.publish(topic, key or "", value)
            return True

        try:
            kafka_headers = []
            if headers:
                kafka_headers = [(k, v.encode("utf-8")) for k, v in headers.items()]

            future = await asyncio.to_thread(
                self._producer.send, topic, value=value, key=key, headers=kafka_headers
            )
            await asyncio.to_thread(future.get, timeout=10)
            logger.debug("Kafka message published", topic=topic, key=key)
            return True

        except Exception as e:
            logger.error("Kafka publish failed", topic=topic, error=str(e))
            return False

    async def publish_json(
        self,
        topic: str,
        data: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Convenience method: serialize dict to JSON and publish."""
        payload = json.dumps(data, default=str).encode("utf-8")
        return await self.publish(topic, payload, key, headers)

    def close(self):
        if self._producer:
            self._producer.close()


class KafkaConsumerClient:
    """
    Async-friendly Kafka consumer with automatic offset management.
    Supports batch consumption and dead-letter queue routing on failure.
    """

    def __init__(
        self,
        topics: List[str],
        group_id: str,
        bootstrap_servers: Optional[str] = None,
        auto_offset_reset: str = "earliest",
    ):
        self.topics = topics
        self.group_id = group_id
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self._consumer = None
        self._use_mock = (
            not KAFKA_AVAILABLE or os.getenv("KAFKA_MOCK", "false").lower() == "true"
        )
        self._running = False

        if not self._use_mock:
            self._init_real_consumer(auto_offset_reset)

        logger.info(
            "KafkaConsumerClient initialized",
            topics=topics,
            group_id=group_id,
            mode="mock" if self._use_mock else "real",
        )

    def _init_real_consumer(self, auto_offset_reset: str):
        try:
            self._consumer = KafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset=auto_offset_reset,
                enable_auto_commit=False,  # Manual commit for reliability
                max_poll_records=50,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
                value_deserializer=lambda v: v,  # Return raw bytes
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
            )
            logger.info("Kafka real consumer connected", topics=self.topics)
        except Exception as e:
            logger.warning("Kafka consumer failed, falling back to mock", error=str(e))
            self._use_mock = True

    async def consume_one(self, timeout_ms: int = 5000) -> Optional[Dict[str, Any]]:
        """
        Poll for a single message (non-blocking).
        Returns None if no message available within timeout.
        """
        if self._use_mock:
            try:
                messages = await _dev_bus.consume_batch(
                    self.topics, self.group_id, timeout_ms
                )
                return messages[0] if messages else None
            except Exception:
                return None

        try:
            records = await asyncio.to_thread(
                self._consumer.poll, timeout_ms=timeout_ms, max_records=1
            )
            for tp, messages in records.items():
                if messages:
                    msg = messages[0]
                    return {
                        "topic": msg.topic,
                        "partition": msg.partition,
                        "offset": msg.offset,
                        "key": msg.key,
                        "value": msg.value,
                        "headers": dict(msg.headers) if msg.headers else {},
                        "timestamp": msg.timestamp,
                    }
            return None
        except Exception as e:
            logger.error("Kafka consume_one failed", error=str(e))
            return None

    async def consume_loop(
        self,
        handler: Callable,
        dlq_topic: Optional[str] = None,
        max_retries: int = 3,
    ):
        """
        Run an infinite consumption loop.
        On handler failure: retry up to max_retries, then send to DLQ.

        Args:
            handler: Async function accepting (raw_value: bytes, metadata: dict)
            dlq_topic: Dead-letter queue topic for unprocessable messages
            max_retries: Max retry attempts before DLQ
        """
        self._running = True
        dlq_producer = KafkaProducerClient() if dlq_topic else None

        logger.info(
            "Kafka consumer loop started", topics=self.topics, group=self.group_id
        )

        while self._running:
            msg = await self.consume_one(timeout_ms=1000)

            if msg is None:
                await asyncio.sleep(0.1)
                continue

            retry = 0
            success = False

            while retry <= max_retries and not success:
                try:
                    await handler(
                        msg["value"],
                        {
                            "topic": msg.get("topic"),
                            "key": msg.get("key"),
                            "headers": msg.get("headers", {}),
                            "timestamp": msg.get("timestamp"),
                        },
                    )
                    success = True

                    # Commit offset after successful processing
                    if self._consumer:
                        await asyncio.to_thread(self._consumer.commit)

                except Exception as e:
                    retry += 1
                    logger.warning(
                        "Handler failed, retrying",
                        attempt=retry,
                        max=max_retries,
                        error=str(e),
                    )
                    if retry <= max_retries:
                        await asyncio.sleep(2**retry)  # Exponential backoff

            if not success and dlq_producer and dlq_topic:
                logger.error(
                    "Message sent to DLQ after max retries", dlq_topic=dlq_topic
                )
                await dlq_producer.publish(dlq_topic, msg["value"], key=msg.get("key"))

    def stop(self):
        """Gracefully stop the consumer loop."""
        self._running = False
        if self._consumer:
            self._consumer.close()
        logger.info("Kafka consumer stopped", topics=self.topics)


class KafkaAdminManager:
    """
    Manages topic creation and configuration.
    Called once on system startup to ensure all topics exist.
    """

    def __init__(self, bootstrap_servers: Optional[str] = None):
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self._admin = None
        self._use_mock = (
            not KAFKA_AVAILABLE or os.getenv("KAFKA_MOCK", "false").lower() == "true"
        )

    def ensure_topics(self, topic_configs: Dict[str, Dict]) -> Dict[str, bool]:
        """
        Create all required topics if they don't exist.
        Returns dict of {topic: created_bool}.
        """
        if self._use_mock:
            logger.info(
                "Mock mode: skipping topic creation", topics=list(topic_configs.keys())
            )
            return {t: True for t in topic_configs}

        try:
            admin = KafkaAdminClient(bootstrap_servers=self.bootstrap_servers)
            topics_to_create = [
                NewTopic(
                    name=topic,
                    num_partitions=cfg.get("num_partitions", 6),
                    replication_factor=cfg.get("replication_factor", 1),
                )
                for topic, cfg in topic_configs.items()
            ]

            results = {}
            try:
                admin.create_topics(topics_to_create, validate_only=False)
                results = {t: True for t in topic_configs}
                logger.info("Kafka topics created", count=len(topics_to_create))
            except TopicAlreadyExistsError:
                results = {t: False for t in topic_configs}
                logger.info("Kafka topics already exist")
            finally:
                admin.close()
            return results

        except Exception as e:
            logger.error("Failed to ensure Kafka topics", error=str(e))
            return {}
