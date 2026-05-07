"""
Semantic Cache — Vector-backed response caching with graceful degradation.

Uses Qdrant + Gemini text-embedding-004 when available.
Falls back to a no-op cache when Qdrant is unreachable, so the rest
of the system never crashes due to a missing vector store.
"""

import asyncio
import os
import uuid

import structlog

logger = structlog.get_logger(__name__)


class SemanticCache:
    """
    Vector-backed Semantic Cache.
    Hashes prompts using Gemini text-embedding-004 and stores responses in Qdrant.
    Prevents duplicate LLM calls by returning cached answers for cosine similarity > 0.98.

    Gracefully degrades to a no-op if Qdrant or the embedding model is unavailable.
    """

    def __init__(self, collection_name: str = "agent_semantic_cache"):
        self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.collection_name = collection_name
        self._client = None
        self._initialized = False
        self._genai_client = None
        self._unavailable = False  # Set once if Qdrant is confirmed down

    def _get_qdrant_client(self):
        """Lazy-init Qdrant client. Returns None if package not installed or unreachable."""
        if self._unavailable:
            return None
        if self._client is not None:
            return self._client
        try:
            from qdrant_client import AsyncQdrantClient
            self._client = AsyncQdrantClient(url=self.qdrant_url)
            return self._client
        except ImportError:
            logger.warning("qdrant-client not installed — semantic cache disabled")
            self._unavailable = True
            return None
        except Exception as e:
            logger.warning("Qdrant connection failed — semantic cache disabled", error=str(e))
            self._unavailable = True
            return None

    def _get_genai_client(self):
        if not self._genai_client:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                try:
                    from google import genai
                    self._genai_client = genai.Client(api_key=api_key)
                except Exception:
                    pass
        return self._genai_client

    async def _embed_text(self, text: str) -> list[float]:
        """Embeds text using the Google GenAI embedding model."""
        client = self._get_genai_client()
        if not client:
            raise ValueError("GEMINI_API_KEY is not set.")

        def _do_embed():
            result = client.models.embed_content(
                model="text-embedding-004",
                contents=text,
            )
            return result.embeddings[0].values

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _do_embed)

    async def _ensure_collection(self):
        if self._initialized or self._unavailable:
            return

        client = self._get_qdrant_client()
        if not client:
            return

        try:
            from qdrant_client.models import Distance, VectorParams
            exists = await client.collection_exists(self.collection_name)
            if not exists:
                await client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
                )
                logger.info(
                    "Created new semantic cache Qdrant collection",
                    collection=self.collection_name,
                )
            self._initialized = True
        except Exception as e:
            logger.warning("Failed to initialize semantic cache — disabling", error=str(e))
            self._unavailable = True

    async def get_cached_response(
        self, prompt: str, threshold: float = 0.98
    ) -> str | None:
        """Search Qdrant for a semantically identical prompt."""
        if self._unavailable:
            return None

        try:
            await self._ensure_collection()
            if not self._initialized:
                return None

            vector = await self._embed_text(prompt)
            client = self._get_qdrant_client()
            if not client:
                return None

            search_result = await client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=1,
                with_payload=True,
                score_threshold=threshold,
            )

            if search_result:
                best_match = search_result[0]
                logger.info("Semantic cache HIT", score=best_match.score)
                return best_match.payload.get("response")

            return None
        except Exception as e:
            logger.warning("Semantic cache lookup failed", error=str(e))
            return None

    async def cache_response(self, prompt: str, response: str):
        """Store the prompt and response pair in the semantic cache."""
        if self._unavailable:
            return

        try:
            await self._ensure_collection()
            if not self._initialized:
                return

            vector = await self._embed_text(prompt)
            point_id = str(uuid.uuid4())
            client = self._get_qdrant_client()
            if not client:
                return

            from qdrant_client.models import PointStruct
            await client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={"prompt": prompt, "response": response},
                    )
                ],
            )
            logger.debug("Added response to semantic cache", point_id=point_id)
        except Exception as e:
            logger.warning("Failed to write to semantic cache", error=str(e))
