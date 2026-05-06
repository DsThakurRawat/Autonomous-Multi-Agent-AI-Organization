"""
Base Agent Foundation
The core abstraction for all SARANG research agents.
Provides asynchronous LLM invocation, Redis telemetry, and semantic memory.
"""

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
import json
import os
from typing import Any, cast

from google.genai import types
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from agents.events import AgentEvent
from agents.memory import SemanticCache

logger = structlog.get_logger(__name__)

def _clean_json_response(text: str) -> str:
    """Strip Markdown formatting from LLM output."""
    text = cast(str, text).strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

class BaseAgent(ABC):
    """
    Abstract base class for all SARANG agents.
    Focuses on high-performance asynchronous telemetry and reliable LLM dispatch.
    """

    ROLE: str = "BaseAgent"

    def __init__(
        self,
        llm_client: Any | None = None,
        tools: dict[str, Callable] | None = None,
        model_name: str | None = None,
        provider: str = "google",
    ):
        self.llm_client = llm_client
        self.tools = tools or {}
        # Default to Gemini 2.0 Flash Lite for higher free-tier quota
        self.model_name = model_name or "gemini-2.0-flash-lite"
        self.provider = provider
        
        self._current_task_id: str | None = None
        self._semantic_cache = SemanticCache()
        self._redis_client: Any | None = None
        self.budget_limit = float(os.getenv("BUDGET_LIMIT_USD", "500.0"))

        logger.info("SARANG Agent Initialized", role=self.ROLE, model=self.model_name)

    @property
    def redis_client(self) -> Any:
        """Lazy Redis connection with a No-Op fallback for local stability."""
        if self._redis_client is None:
            import redis.asyncio as aioredis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            try:
                self._redis_client = aioredis.from_url(redis_url, decode_responses=True)
            except Exception:
                logger.warning("Redis unavailable, using no-op stub for telemetry")
                self._redis_client = _NoOpRedis()
        return self._redis_client

    async def _publish_event(self, event: AgentEvent):
        """Publish telemetry events to Redis for the Go Gateway to relay."""
        if not self._current_task_id:
            return
        
        try:
            channel = f"mission:{self._current_task_id}:events"
            payload = {
                "type": event.event_type,
                "agent": self.ROLE,
                "message": event.message,
                "level": event.level,
                "timestamp": datetime.now(UTC).isoformat(),
                "data": event.data
            }
            # Use the async publish method directly
            await self.redis_client.publish(channel, json.dumps(payload))
        except Exception as e:
            logger.debug("Telemetry publish skipped (Redis likely down)", error=str(e))

    def get_full_system_prompt(self) -> str:
        """Combines the agent's core mission with SARANG global instructions."""
        return (
            f"YOU ARE THE {self.ROLE} IN THE SARANG RESEARCH SWARM.\n"
            "SARANG is a high-performance, agentic AI laboratory for scientific discovery.\n"
            "Your output must be mathematically rigorous and pedagogically clear.\n\n"
            f"{self.system_prompt}"
        )

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Each agent defines its own core mission prompt."""
        ...

    @abstractmethod
    async def run(self, **kwargs) -> dict[str, Any]:
        """Main entry point for agent logic."""
        ...

    async def emit(
        self,
        context: Any,
        message: str,
        level: str = "info",
        data: dict[str, Any] | None = None,
        event_type: str = "thinking",
    ) -> None:
        """Emit a telemetry event to the context and Redis."""
        event = AgentEvent(
            event_type=event_type,
            agent_role=self.ROLE,
            message=message,
            level=level,
            data=data or {},
        )
        if context:
            await context.emit_event(event)
        await self._publish_event(event)

    # -- LLM Interface ----------------------------------------------
    async def call_llm(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 8192,
        response_format: str | None = None,
    ) -> str:
        """Asynchronous LLM dispatcher with semantic caching and budget gating."""
        if self.llm_client is None:
            return "LLM Client not configured. No-op response."

        prompt_text = "\n".join([m["content"] for m in messages])
        
        # 1. Cache Check
        try:
            cached = await self._semantic_cache.get_cached_response(prompt_text)
            if cached:
                logger.info("Serving from Semantic Cache", agent=self.ROLE)
                return cached
        except Exception: pass

        # 2. Provider Execution
        text, usage = await self._execute_google_provider(messages, temperature, max_tokens, response_format)

        # 3. Store Cache
        try:
            await self._semantic_cache.cache_response(prompt_text, text)
        except Exception: pass

        return text

    @retry(wait=wait_exponential_jitter(initial=1, max=10), stop=stop_after_attempt(3))
    async def _execute_google_provider(self, messages, temp, tokens, fmt):
        """Specifically optimized for the new google-genai SDK."""
        system_prompt = self.get_full_system_prompt()
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temp,
            max_output_tokens=tokens,
        )
        if fmt == "json_object":
            config.response_mime_type = "application/json"

        gemini_messages = []
        for m in messages:
            if m["role"] == "system": continue
            role = "model" if m["role"] == "assistant" else "user"
            gemini_messages.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))

        # Synchronous SDK call wrapped for async execution
        response = await asyncio.to_thread(
            self.llm_client.models.generate_content,
            model=self.model_name,
            contents=gemini_messages,
            config=config,
        )
        
        usage = {
            "prompt": getattr(response.usage_metadata, "prompt_token_count", 0),
            "completion": getattr(response.usage_metadata, "candidates_token_count", 0),
        }
        return response.text, usage

class _NoOpRedis:
    """Silently handles telemetry if Redis is missing."""
    async def publish(self, *args, **kwargs): return 0
    async def get(self, *args, **kwargs): return None
    async def set(self, *args, **kwargs): return True
