"""Health and availability tests."""
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    res = await client.get("/")
    assert res.status_code == 200

@pytest.mark.asyncio
async def test_openapi_docs_accessible(client: AsyncClient):
    res = await client.get("/api/docs")
    assert res.status_code == 200