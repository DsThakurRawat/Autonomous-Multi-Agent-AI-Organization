"""
MoE Rust Scoring HTTP Client
============================
Drop-in async client for the Rust moe-scoring service.
Python router.py calls this when MOE_RUST_URL env var is set.
Falls back to pure-Python scoring if the service is unavailable.
"""

import os
import time
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger(__name__)

# Try aiohttp first (preferred), fall back to httpx
try:
    import aiohttp

    _HTTP_LIB = "aiohttp"
except ImportError:
    try:
        import httpx

        _HTTP_LIB = "httpx"
    except ImportError:
        _HTTP_LIB = None
        logger.warning(
            "No async HTTP library available (aiohttp or httpx). Install one for Rust MoE support."
        )


class RustMoeClient:
    """
    Async HTTP client for the Rust MoE scoring microservice.

    Usage:
        client = RustMoeClient()
        decision = await client.route(task_type="backend_development", ...)
        if decision:
            expert = decision["selected_expert"]
    """

    def __init__(self, base_url: Optional[str] = None, timeout_sec: float = 2.0):
        self.base_url = (
            base_url or os.getenv("MOE_RUST_URL", "http://localhost:8090")
        ).rstrip("/")
        self.timeout = timeout_sec
        self._available: Optional[bool] = None  # None = not yet checked
        self._session = None

    async def _get_session(self):
        """Lazily create and reuse HTTP session."""
        if _HTTP_LIB == "aiohttp" and self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session

    async def health_check(self) -> bool:
        """Check if Rust service is reachable."""
        try:
            result = await self._get("/health")
            up = result.get("status") == "ok"
            if up != self._available:
                if up:
                    logger.info("Rust MoE service is UP", url=self.base_url)
                else:
                    logger.warning("Rust MoE service returned non-ok status")
            self._available = up
            return up
        except Exception:
            if self._available is not False:
                logger.warning(
                    "Rust MoE service unreachable — falling back to Python scorer",
                    url=self.base_url,
                )
            self._available = False
            return False

    async def route(
        self,
        task_id: str,
        task_type: str,
        task_name: str,
        project_id: str,
        input_context: str = "",
        required_skills: List[str] = None,
        priority: str = "medium",
        force_ensemble: bool = False,
        trace_id: str = "",
        experts: Optional[Dict[str, Any]] = None,
        stats: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Route a task via the Rust service.
        Returns the RouteResponse dict or None if the service is unavailable.
        """
        if self._available is False:
            return None  # Fast path: don't even try

        payload = {
            "task_id": task_id,
            "task_type": task_type,
            "task_name": task_name,
            "project_id": project_id,
            "input_context": input_context,
            "required_skills": required_skills or [],
            "priority": priority,
            "force_ensemble": force_ensemble,
            "trace_id": trace_id,
        }
        if experts:
            payload["experts"] = experts
        if stats:
            payload["stats"] = stats

        try:
            t0 = time.monotonic()
            result = await self._post("/route", payload)
            latency = (time.monotonic() - t0) * 1000
            self._available = True
            logger.debug(
                "Rust MoE routing complete",
                expert=result.get("selected_expert"),
                score=result.get("routing_score"),
                latency_ms=round(latency, 2),
            )
            return result
        except Exception as e:
            logger.warning("Rust MoE route failed", error=str(e))
            self._available = False
            return None

    async def route_batch(
        self,
        tasks: List[Dict[str, Any]],
        experts: Optional[Dict[str, Any]] = None,
        stats: Optional[Dict[str, Any]] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Route multiple tasks in a single HTTP call (much faster than N serial calls)."""
        if self._available is False:
            return None
        try:
            payload: Dict[str, Any] = {"tasks": tasks}
            if experts:
                payload["experts"] = experts
            if stats:
                payload["stats"] = stats
            result = await self._post("/route/batch", payload)
            return result.get("decisions", [])
        except Exception as e:
            logger.warning("Rust MoE batch route failed", error=str(e))
            self._available = False
            return None

    async def close(self):
        """Close the underlying HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    # ── Internal HTTP helpers ───────────────────────────────────────────

    async def _get(self, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if _HTTP_LIB == "aiohttp":
            session = await self._get_session()
            async with session.get(url) as resp:
                resp.raise_for_status()
                return await resp.json()
        elif _HTTP_LIB == "httpx":
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.json()
        raise RuntimeError("No HTTP library available")

    async def _post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if _HTTP_LIB == "aiohttp":
            session = await self._get_session()
            async with session.post(url, json=data) as resp:
                resp.raise_for_status()
                return await resp.json()
        elif _HTTP_LIB == "httpx":
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=data)
                resp.raise_for_status()
                return resp.json()
        raise RuntimeError("No HTTP library available")


# ── Module-level singleton ────────────────────────────────────────────────────
# Shared client — reuses sessions for efficiency
_client: Optional[RustMoeClient] = None


def get_rust_client() -> Optional[RustMoeClient]:
    """
    Return module singleton, or None if MOE_RUST_URL is not configured.
    Lazy initialization on first call.
    """
    global _client
    if _client is None:
        url = os.getenv("MOE_RUST_URL")
        if url:
            _client = RustMoeClient(base_url=url)
            logger.info("RustMoeClient initialized", url=url)
    return _client
