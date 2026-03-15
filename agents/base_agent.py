"""
Base Agent
Abstract base class for all AI agents in the organization.
Provides LLM invocation, memory access, tool calling, and event emission.
"""

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
import json
from typing import Any

from google.genai import types
import structlog

from tools.collaboration_tool import CollaborationTool

logger = structlog.get_logger(__name__)


def _clean_json_response(text: str) -> str:
    """Strip Markdown formatting (e.g. ```json ... ```) from LLM output."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


class AgentToolCall:
    """Represents a tool invocation request from an agent."""

    def __init__(self, tool_name: str, parameters: dict[str, Any]):
        self.tool_name = tool_name
        self.parameters = parameters
        self.result: Any = None
        self.error: str | None = None
        self.timestamp = datetime.now(UTC)


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents.

    Every agent has:
    - A defined ROLE and SYSTEM_PROMPT
    - Tool calling capability
    - Private scratchpad memory
    - Shared memory access (injected via context)
    - Self-critique/reflection loop
    """

    ROLE: str = "BaseAgent"
    MAX_ITERATIONS: int = 10

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        tools: Optional[Dict[str, Callable]] = None,
        model_name: Optional[str] = None,
        llm_client=None,
        tools: dict[str, Callable] | None = None,
        model_name: str | None = None,
        provider: str = "google",
    ):
        self.llm_client = llm_client
        self.tools = tools or {}
        if "collaboration" not in self.tools:
            self.tools["collaboration"] = CollaborationTool().run
        self.provider = provider
        self.model_name = model_name
        self._scratchpad: list[dict[str, str]] = []
        self._iteration_count = 0
        logger.info(
            "Agent initialized", role=self.ROLE, provider=provider, model=model_name
        )

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Each agent defines its own system prompt and role."""
        ...

    @abstractmethod
    async def run(self, **kwargs) -> dict[str, Any]:
        """Main entry point — each agent implements its specific logic."""
        ...

    async def execute_task(self, task: Any, context: Any) -> dict[str, Any]:
        """Generic task executor called by the orchestrator."""
        logger.info("Executing task", agent=self.ROLE, task=task.name)
        return await self.run(task=task, context=context)

    # ── LLM Interface ──────────────────────────────────────────────
    async def call_llm(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: str | None = None,  # "json_object" | None
    ) -> str:
        """
        Unified LLM call that dispatches to OpenAI, Anthropic, or Google
        based on self.provider, which is set from the Kafka TaskMessage llm_config.
        Falls back to mock mode if no llm_client is configured.
        """
        if self.llm_client is None:
            return self._mock_llm_response(messages)

        try:
            assert self.llm_client is not None  # guarded above
            # ── Google Gemini ──────────────────────────────────────────────
            if self.provider == "google":
                system_prompt = self.system_prompt
                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
                if response_format == "json_object":
                    config.response_mime_type = "application/json"

                gemini_messages = []
                for m in messages:
                    if m["role"] == "system":
                        continue
                    role = "model" if m["role"] == "assistant" else "user"
                    gemini_messages.append(
                        types.Content(
                            role=role, parts=[types.Part.from_text(text=m["content"])]
                        )
                    )

                response = await asyncio.to_thread(
                    self.llm_client.models.generate_content,  # type: ignore[union-attr]
                    model=self.model_name,
                    contents=gemini_messages,
                    config=config,
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.llm_client.models.generate_content,
                        model=self.model_name,
                        contents=gemini_messages,
                        config=config,
                    ),
                    timeout=60.0
                )
                return response.text

            # ── OpenAI ────────────────────────────────────────────────────
            elif self.provider == "openai":
                kwargs = {
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if response_format == "json_object":
                    kwargs["response_format"] = {"type": "json_object"}  # type: ignore[assignment]

                response = await asyncio.to_thread(
                    self.llm_client.chat.completions.create, **kwargs  # type: ignore[union-attr]
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.llm_client.chat.completions.create, **kwargs
                    ),
                    timeout=60.0
                )
                return response.choices[0].message.content

            # ── Anthropic Claude ──────────────────────────────────────────
            elif self.provider == "anthropic":
                # Extract system prompt separately — Anthropic uses it as a top-level param
                system_content = self.system_prompt
                if response_format == "json_object":
                    system_content += "\n\nIMPORTANT: Return ONLY a valid JSON object. Do not include markdown formatting like ```json or any other conversational text."

                anthropic_messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in messages
                    if m["role"] != "system"
                ]

                response = await asyncio.to_thread(
                    self.llm_client.messages.create,  # type: ignore[union-attr]
                    model=self.model_name,
                    max_tokens=max_tokens,
                    system=system_content,
                    messages=anthropic_messages,
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.llm_client.messages.create,
                        model=self.model_name,
                        max_tokens=max_tokens,
                        system=system_content,
                        messages=anthropic_messages,
                    ),
                    timeout=60.0
                )
                text = response.content[0].text
                if response_format == "json_object":
                    text = _clean_json_response(text)
                return text

            # ── Amazon Bedrock (Nova) ──────────────────────────────────────────────────
            elif self.provider == "bedrock":
                # Nova models use the Bedrock Converse API format
                system_content = self.system_prompt
                if response_format == "json_object":
                    system_content += "\n\nIMPORTANT: Return ONLY a valid JSON object. Do not include markdown formatting like ```json or any other conversational text."

                bedrock_messages = [
                    {"role": m["role"], "content": [{"text": m["content"]}]}
                    for m in messages
                    if m["role"] != "system"
                ]

                kwargs = {
                    "modelId": self.model_name,
                    "messages": bedrock_messages,
                    "system": [{"text": system_content}],
                    "inferenceConfig": {
                        "temperature": temperature,
                        "maxTokens": max_tokens,
                    },
                }

                response = await asyncio.to_thread(self.llm_client.converse, **kwargs)  # type: ignore[union-attr]
                text = response["output"]["message"]["content"][0]["text"]
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.llm_client.converse, **kwargs
                    ),
                    timeout=60.0
                )
                text = response['output']['message']['content'][0]['text']
                if response_format == "json_object":
                    text = _clean_json_response(text)
                return text

            else:
                logger.warning(
                    "Unknown provider, falling back to mock", provider=self.provider
                )
                return self._mock_llm_response(messages)

        except Exception as e:
            logger.error(
                "LLM call failed", error=str(e), agent=self.ROLE, provider=self.provider
            )
            raise

    def _mock_llm_response(self, messages: list[dict[str, str]]) -> str:
        """Deterministic mock response for demo mode."""
        last_user_msg = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        return json.dumps(
            {
                "status": "mock_response",
                "agent": self.ROLE,
                "response": f"[{self.ROLE}] Processed: {last_user_msg[:100]}",
            }
        )

    # ── Tool Calling ───────────────────────────────────────────────
    async def use_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a registered tool safely."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not available to {self.ROLE}")

        logger.info("Tool called", agent=self.ROLE, tool=tool_name)
        tool_fn = self.tools[tool_name]

        try:
            if asyncio.iscoroutinefunction(tool_fn):
                result = await tool_fn(**kwargs)
            else:
                result = await asyncio.to_thread(tool_fn, **kwargs)
            logger.info("Tool succeeded", agent=self.ROLE, tool=tool_name)
            return result
        except Exception as e:
            logger.error("Tool failed", agent=self.ROLE, tool=tool_name, error=str(e))
            raise

    # ── Memory Access ──────────────────────────────────────────────
    def add_to_scratchpad(self, role: str, content: str):
        """Add to agent's private reasoning scratchpad."""
        self._scratchpad.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    def get_scratchpad_messages(self) -> list[dict[str, str]]:
        """Return scratchpad as LLM message format."""
        return [{"role": m["role"], "content": m["content"]} for m in self._scratchpad]

    def clear_scratchpad(self):
        self._scratchpad = []
        self._iteration_count = 0

    # ── Self-Critique ──────────────────────────────────────────────
    async def self_critique(self, output: dict[str, Any]) -> dict[str, Any]:
        """
        Reflection loop: Agent reviews its own output and scores it.
        Returns the original output plus a critique score and suggestions.
        """
        critique_prompt = f"""
Review your previous output for the role of {self.ROLE}.
Output to review: {json.dumps(output, indent=2)[:2000]}

Evaluate:
1. Completeness (0-10): Are all required fields present?
2. Correctness (0-10): Is the output logically sound?
3. Safety (0-10): Does it follow security best practices?
4. Cost awareness (0-10): Is it budget-conscious?

Return JSON: {{"scores": {{}}, "issues": [], "improvements": [], "approved": true/false}}
"""
        try:
            raw = await self.call_llm(
                [{"role": "user", "content": critique_prompt}],
                temperature=0.1,
                response_format="json_object",
            )
            critique = json.loads(raw)
            output["_critique"] = critique
            return output
        except Exception:
            output["_critique"] = {"approved": True, "scores": {}, "issues": []}
            return output
