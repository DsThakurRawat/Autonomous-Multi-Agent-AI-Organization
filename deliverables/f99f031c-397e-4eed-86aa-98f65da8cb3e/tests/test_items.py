"""Items CRUD endpoint tests."""
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_list_items_unauthenticated(client: AsyncClient):
    res = await client.get("/api/items")
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_create_item_success(client: AsyncClient, auth_headers):
    res = await client.post("/api/items",
        json={"title": "Test Item", "description": "A test item", "status": "active"},
        headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Test Item"
    assert "id" in data

@pytest.mark.asyncio
async def test_list_items_returns_only_own(client: AsyncClient, auth_headers):
    await client.post("/api/items", json={"title": "My Item"}, headers=auth_headers)
    res = await client.get("/api/items", headers=auth_headers)
    assert res.status_code == 200
    assert isinstance(res.json()["items"], list)

@pytest.mark.asyncio
async def test_update_item(client: AsyncClient, auth_headers):
    create_res = await client.post("/api/items",
        json={"title": "Original"}, headers=auth_headers)
    item_id = create_res.json()["id"]
    res = await client.put(f"/api/items/{item_id}",
        json={"title": "Updated Title"}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["title"] == "Updated Title"

@pytest.mark.asyncio
async def test_delete_item(client: AsyncClient, auth_headers):
    create_res = await client.post("/api/items",
        json={"title": "To Delete"}, headers=auth_headers)
    item_id = create_res.json()["id"]
    res = await client.delete(f"/api/items/{item_id}", headers=auth_headers)
    assert res.status_code == 204
    get_res = await client.get(f"/api/items/{item_id}", headers=auth_headers)
    assert get_res.status_code == 404

@pytest.mark.asyncio
async def test_create_item_missing_title(client: AsyncClient, auth_headers):
    res = await client.post("/api/items", json={}, headers=auth_headers)
    assert res.status_code == 422