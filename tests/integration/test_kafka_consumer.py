import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from testcontainers.kafka import KafkaContainer

from agents.agent_service import AgentMicroservice
from agents.roles import AgentRole
from messaging.kafka_client import KafkaConsumerClient, KafkaProducerClient
from messaging.schemas import TaskMessage
from messaging.topics import KafkaTopics


@pytest.fixture(scope="module")
def kafka_container():
    with KafkaContainer(image="confluentinc/cp-kafka:7.4.0") as kafka:
        yield kafka


@pytest.fixture
def kafka_env(kafka_container, monkeypatch):
    bootstrap_server = kafka_container.get_bootstrap_server()
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", bootstrap_server)
    monkeypatch.setenv("AGENT_ROLE", AgentRole.CTO)
    monkeypatch.setenv(
        "KAFKA_TEST_MODE", "true"
    )  # Prevent some prod behaviors if needed
    return bootstrap_server


@pytest.mark.asyncio
async def test_agent_microservice_consumer_loop(kafka_env, monkeypatch):
    # Setup mock agent so we don't call real LLMs
    mock_agent = AsyncMock()
    mock_agent.execute_task = AsyncMock(
        return_value={"_cost_usd": 0.05, "result": "architecture is good"}
    )

    # Mock _load_agent so it returns our mocked agent
    with patch("agents.agent_service._load_agent", return_value=mock_agent):

        service = AgentMicroservice()
        service.agent = mock_agent
        service.producer = KafkaProducerClient()
        service.consumer = KafkaConsumerClient(
            topics=[service.topic], group_id=service.group_id
        )

        # Run consume loop in background
        loop_task = asyncio.create_task(service._consume_loop())

        # Publish a TaskMessage into the input topic
        test_producer = KafkaProducerClient()
        task_msg = TaskMessage(
            task_id="t-integration-123",
            task_name="Architect System",
            task_type="design",
            agent_role=AgentRole.CTO,
            project_id="p-456",
            input_data={"idea": "build something cool"},
            retry_count=0,
            max_retries=3,
        )
        await test_producer.publish_model(service.topic, task_msg, key=task_msg.task_id)

        # Give it a couple seconds to process
        await asyncio.sleep(2)

        # Read from the output topic (results topic)
        result_topic = KafkaTopics.results_topic(task_msg.project_id)
        result_consumer = KafkaConsumerClient(
            topics=[result_topic], group_id="test-result-group"
        )

        async def fetch_result():
            async for data in result_consumer.consume_stream():
                return data

        fetch_task = asyncio.create_task(fetch_result())
        try:
            result_data = await asyncio.wait_for(fetch_task, timeout=10.0)
        except TimeoutError:
            service.running = False
            loop_task.cancel()
            pytest.fail("Timeout waiting for result message from Kafka")

        assert result_data["task_id"] == "t-integration-123"
        assert result_data["agent_role"] == AgentRole.CTO
        assert result_data["status"] == "completed"
        assert result_data["output_data"]["result"] == "architecture is good"

        # Stop background loops
        service.running = False
        loop_task.cancel()
