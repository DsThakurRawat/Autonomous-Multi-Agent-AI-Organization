import asyncio
import os
import uuid

from google import genai
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from structlog import get_logger

logger = get_logger(__name__)


class SemanticCache:
    """
    Vector-backed Semantic Cache.
    Hashes prompts using Gemini text-embedding-004 and stores responses in Qdrant.
    Prevents duplicate LLM calls by returning cached answers for cosine similarity > 0.98.
    """

    def __init__(self, collection_name: str = "agent_semantic_cache"):
        self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.collection_name = collection_name
        self._client = AsyncQdrantClient(url=self.qdrant_url)
        self._initialized = False
        self._genai_client = None

    def _get_genai_client(self):
        if not self._genai_client:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                self._genai_client = genai.Client(api_key=api_key)
        return self._genai_client

    async def _embed_text(self, text: str) -> list[float]:
        """Embeds text using the Google GenAI embedding model."""
        client = self._get_genai_client()
        if not client:
            raise ValueError("GEMINI_API_KEY is not set.")

        # The new google-genai SDK
        # We run it in a thread-pool because it is a sync call
        def _do_embed():
            result = client.models.embed_content(
                model="text-embedding-004",
                contents=text,
            )
            return result.embeddings[0].values

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _do_embed)

    async def _ensure_collection(self):
        if self._initialized:
            return

        try:
            exists = await self._client.collection_exists(self.collection_name)
            if not exists:
                # text-embedding-004 outputs 768 dimensions
                await self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
                )
                logger.info(
                    "Created new semantic cache Qdrant collection",
                    collection=self.collection_name,
                )
            self._initialized = True
        except Exception as e:
            logger.warning("Failed to initialize semantic cache", error=str(e))

    async def get_cached_response(
        self, prompt: str, threshold: float = 0.98
    ) -> str | None:
        """Search Qdrant for a semantically identical prompt."""
        try:
            await self._ensure_collection()
            if not self._initialized:
                return None

            vector = await self._embed_text(prompt)

            search_result = await self._client.search(
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
        try:
            await self._ensure_collection()
            if not self._initialized:
                return

            vector = await self._embed_text(prompt)
            point_id = str(uuid.uuid4())

            await self._client.upsert(
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
