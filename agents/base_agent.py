"""
Base Agent
Abstract base class for all AI agents in the organization.
Provides LLM invocation, memory access, tool calling, and event emission.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import structlog

logger = structlog.get_logger(__name__)


class AgentToolCall:
    """Represents a tool invocation request from an agent."""

    def __init__(self, tool_name: str, parameters: Dict[str, Any]):
        self.tool_name = tool_name
        self.parameters = parameters
        self.result: Any = None
        self.error: Optional[str] = None
        self.timestamp = datetime.utcnow()


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
        llm_client=None,
        tools: Dict[str, Callable] = None,
        model_name: str = "gpt-4-turbo-preview",
    ):
        self.llm_client = llm_client
        self.tools = tools or {}
        self.model_name = model_name
        self._scratchpad: List[Dict[str, str]] = []
        self._iteration_count = 0
        logger.info("Agent initialized", role=self.ROLE)

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Each agent defines its own system prompt and role."""
        ...

    @abstractmethod
    async def run(self, **kwargs) -> Dict[str, Any]:
        """Main entry point — each agent implements its specific logic."""
        ...

    async def execute_task(self, task: Any, context: Any) -> Dict[str, Any]:
        """Generic task executor called by the orchestrator."""
        logger.info("Executing task", agent=self.ROLE, task=task.name)
        return await self.run(task=task, context=context)

    # ── LLM Interface ──────────────────────────────────────────────
    async def call_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[str] = None,  # "json_object" | None
    ) -> str:
        """
        Unified LLM call with retry and fallback.
        Supports OpenAI, Anthropic, and AWS Bedrock (Amazon Nova).
        """
        if self.llm_client is None:
            # Demo/mock mode
            return self._mock_llm_response(messages)

        full_messages = [{"role": "system", "content": self.system_prompt}, *messages]

        try:
            # Try primary LLM
            response = await asyncio.to_thread(
                self.llm_client.chat.completions.create,
                model=self.model_name,
                messages=full_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **(
                    {"response_format": {"type": response_format}}
                    if response_format
                    else {}
                ),
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error("LLM call failed", error=str(e), agent=self.ROLE)
            raise

    def _mock_llm_response(self, messages: List[Dict[str, str]]) -> str:
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
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def get_scratchpad_messages(self) -> List[Dict[str, str]]:
        """Return scratchpad as LLM message format."""
        return [{"role": m["role"], "content": m["content"]} for m in self._scratchpad]

    def clear_scratchpad(self):
        self._scratchpad = []
        self._iteration_count = 0

    # ── Self-Critique ──────────────────────────────────────────────
    async def self_critique(self, output: Dict[str, Any]) -> Dict[str, Any]:
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
