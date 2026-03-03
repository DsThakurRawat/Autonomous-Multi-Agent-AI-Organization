"""
Messaging Layer — Kafka-based distributed communication.
Provides async producer/consumer base classes and message schemas.
"""

from .schemas import (
    TaskMessage,
    ResultMessage,
    EventMessage,
    ErrorMessage,
    MetricMessage,
)
from .topics import KafkaTopics
from .kafka_client import KafkaProducerClient, KafkaConsumerClient

__all__ = [
    "TaskMessage",
    "ResultMessage",
    "EventMessage",
    "ErrorMessage",
    "MetricMessage",
    "KafkaTopics",
    "KafkaProducerClient",
    "KafkaConsumerClient",
]
