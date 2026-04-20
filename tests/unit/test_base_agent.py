"""
Unit Tests — BaseAgent
Tests the abstract base agent's utility methods, mock LLM, and tool management.
"""

import json
import os
from unittest.mock import patch

import pytest

from agents.base_agent import AgentToolCall, BaseAgent, _clean_json_response


# Concrete subclass for testing (BaseAgent is abstract)
class StubAgent(BaseAgent):
    ROLE = "TestAgent"

    @property
    def system_prompt(self) -> str:
        return "You are a test agent."

    async def run(self, **kwargs):
        return {"status": "ok"}


class TestCleanJsonResponse:
    def test_strips_json_codeblock(self):
        raw = '```json\n{"key": "value"}\n```'
        assert _clean_json_response(raw) == '{"key": "value"}'

    def test_strips_plain_codeblock(self):
        raw = '```\n{"key": "value"}\n```'
        assert _clean_json_response(raw) == '{"key": "value"}'

    def test_passthrough_clean_json(self):
        raw = '{"key": "value"}'
        assert _clean_json_response(raw) == '{"key": "value"}'

    def test_strips_whitespace(self):
        raw = '  \n{"key": "value"}\n  '
        assert _clean_json_response(raw) == '{"key": "value"}'


class TestAgentToolCall:
    def test_construction(self):
        tc = AgentToolCall(tool_name="git_clone", parameters={"url": "http://x.com"})
        assert tc.tool_name == "git_clone"
        assert tc.parameters["url"] == "http://x.com"
        assert tc.result is None
        assert tc.error is None
        assert tc.timestamp is not None


class TestGetSecret:
    def test_falls_back_to_env(self):
        with patch.dict(os.environ, {"MY_SECRET": "env_value"}):
            assert BaseAgent.get_secret("MY_SECRET") == "env_value"

    def test_returns_default_when_missing(self):
        result = BaseAgent.get_secret("NONEXISTENT_SECRET_XYZ", default="fallback")
        assert result == "fallback"

    def test_returns_none_when_no_default(self):
        result = BaseAgent.get_secret("NONEXISTENT_SECRET_XYZ")
        assert result is None

    def test_tmpfs_takes_precedence(self, tmp_path):
        secret_file = tmp_path / "TEST_KEY"
        secret_file.write_text("tmpfs_value")
        with (
            patch("agents.base_agent.os.path.exists", return_value=True),
            patch(
                "builtins.open",
                create=True,
                return_value=open(str(secret_file)),
            ),
        ):
            result = BaseAgent.get_secret("TEST_KEY")
            assert result == "tmpfs_value"


class TestMockLLMResponse:
    @pytest.fixture
    def agent(self):
        return StubAgent(llm_client=None, provider="google", model_name="mock")

    def test_mock_returns_valid_json(self, agent):
        messages = [{"role": "user", "content": "Hello world"}]
        result = agent._mock_llm_response(messages)
        data = json.loads(result)
        assert data["agent"] == "TestAgent"
        assert "Hello world" in data["response"]

    def test_mock_uses_last_user_message(self, agent):
        messages = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Reply"},
            {"role": "user", "content": "Second message here"},
        ]
        result = agent._mock_llm_response(messages)
        data = json.loads(result)
        assert "Second message here" in data["response"]


class TestScratchpad:
    @pytest.fixture
    def agent(self):
        return StubAgent(llm_client=None, provider="google", model_name="mock")

    def test_add_and_get(self, agent):
        agent.add_to_scratchpad("user", "test note")
        msgs = agent.get_scratchpad_messages()
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "test note"

    def test_clear(self, agent):
        agent.add_to_scratchpad("user", "note 1")
        agent.add_to_scratchpad("assistant", "note 2")
        assert len(agent.get_scratchpad_messages()) == 2
        agent.clear_scratchpad()
        assert len(agent.get_scratchpad_messages()) == 0

    def test_clear_resets_iteration(self, agent):
        agent._iteration_count = 5
        agent.clear_scratchpad()
        assert agent._iteration_count == 0


class TestToolManagement:
    @pytest.fixture
    def agent(self):
        return StubAgent(llm_client=None, provider="google", model_name="mock")

    def test_collaboration_tool_auto_registered(self, agent):
        assert "collaboration" in agent.tools

    @pytest.mark.asyncio
    async def test_use_tool_unknown_raises(self, agent):
        with pytest.raises(ValueError, match="not available"):
            await agent.use_tool("nonexistent_tool")

    @pytest.mark.asyncio
    async def test_use_tool_sync(self, agent):
        agent.tools["echo"] = lambda text: f"echoed: {text}"
        result = await agent.use_tool("echo", text="hello")
        assert result == "echoed: hello"

    @pytest.mark.asyncio
    async def test_use_tool_async(self, agent):
        async def async_echo(text):
            return f"async: {text}"

        agent.tools["async_echo"] = async_echo
        result = await agent.use_tool("async_echo", text="world")
        assert result == "async: world"


class TestAgentRun:
    @pytest.mark.asyncio
    async def test_run_returns_ok(self):
        agent = StubAgent(llm_client=None, provider="google", model_name="mock")
        result = await agent.run()
        assert result == {"status": "ok"}
