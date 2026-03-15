import os
import pytest
from fastapi.testclient import TestClient

from api.main import app

@pytest.fixture
def api_key(monkeypatch):
    """Mock the API_KEY environment variable for the duration of the tests."""
    key = "test_integration_key"
    monkeypatch.setenv("API_KEY", key)
    return key

@pytest.fixture
def client():
    """Return a TestClient bound to our FastAPI app."""
    return TestClient(app)

def test_health(client):
    """Test standard unauthenticated healthcheck drops to base orchestrator API."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    
def test_start_project_unauthorized(client):
    """Test that unauthorized project dispatches are rejected (Security harding)."""
    response = client.post(
        "/v1/projects",
        json={"idea": "build a great AI app"}
    )
    # 403 Forbidden is expected for missing X-API-Key header
    assert response.status_code == 403

def test_start_project_validation(client, api_key):
    """Test that our strict Pydantic requirements properly enforce data format constraint (Issue #8)."""
    # Too short idea constraint (must be >= 5)
    response = client.post(
        "/v1/projects",
        headers={"X-API-Key": api_key},
        json={"idea": "bad"}
    )
    # 422 Unprocessable Entity - validation error triggered
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any(err["loc"] == ["body", "idea"] for err in data["detail"])
