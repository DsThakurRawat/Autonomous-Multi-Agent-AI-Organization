"""Security-focused tests - adversarial inputs."""
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_sql_injection_in_email(client: AsyncClient):
    """SQL injection attempt should be rejected safely."""
    res = await client.post("/api/auth/login", json={
        "email": "admin@test.com\' OR 1=1; --",
        "password": "anything"
    })
    assert res.status_code in (401, 422)

@pytest.mark.asyncio
async def test_jwt_tamper_rejected(client: AsyncClient):
    """Tampered JWT must be rejected."""
    res = await client.get("/api/items",
        headers={"Authorization": "Bearer tampered.invalid.jwt"})
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_access_other_users_item(client: AsyncClient, auth_headers):
    """Users cannot access items belonging to other users."""
    other_item_id = "00000000-0000-0000-0000-000000000001"
    res = await client.get(f"/api/items/{other_item_id}", headers=auth_headers)
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_xss_in_item_title(client: AsyncClient, auth_headers):
    """XSS payload should be stored safely (not executed)."""
    xss_payload = "<script>alert('xss')</script>"
    res = await client.post("/api/items",
        json={"title": xss_payload}, headers=auth_headers)
    assert res.status_code == 201
    # Verify it's stored as plain text, not causing server errors
    assert res.json()["title"] == xss_payload

@pytest.mark.asyncio
async def test_large_payload_rejected(client: AsyncClient, auth_headers):
    """Excessively large payloads should be handled gracefully."""
    huge_title = "A" * 10000
    res = await client.post("/api/items",
        json={"title": huge_title}, headers=auth_headers)
    assert res.status_code == 422  # Exceeds max_length=255