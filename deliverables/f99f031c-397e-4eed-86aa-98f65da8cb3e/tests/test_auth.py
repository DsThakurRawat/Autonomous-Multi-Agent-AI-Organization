"""Authentication endpoint tests."""
import pytest
from httpx import AsyncClient

TEST_USER = {"email": "authtest@local.ai", "password": "password123", "full_name": "Auth Test"}

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    res = await client.post("/api/auth/register", json=TEST_USER)
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == TEST_USER["email"]
    assert "id" in data
    assert "hashed_password" not in data  # Never expose password

@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post("/api/auth/register", json=TEST_USER)
    res = await client.post("/api/auth/register", json=TEST_USER)
    assert res.status_code == 400

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/auth/register", json=TEST_USER)
    res = await client.post("/api/auth/login", json={
        "email": TEST_USER["email"], "password": TEST_USER["password"]
    })
    assert res.status_code == 200
    assert "access_token" in res.json()
    assert res.json()["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json=TEST_USER)
    res = await client.post("/api/auth/login", json={
        "email": TEST_USER["email"], "password": "wrongpassword"
    })
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    res = await client.post("/api/auth/login", json={
        "email": "nobody@example.com", "password": "anypassword"
    })
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    res = await client.post("/api/auth/register", json={
        "email": "not-an-email", "password": "password123"
    })
    assert res.status_code == 422

@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    res = await client.post("/api/auth/register", json={
        "email": "short@example.com", "password": "123"
    })
    assert res.status_code == 422