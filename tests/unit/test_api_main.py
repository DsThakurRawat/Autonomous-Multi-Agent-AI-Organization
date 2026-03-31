"""
Unit Tests — API Main (FastAPI endpoints)
Tests health, root, agents listing, projects listing, and rate limiter.
"""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest


@pytest.fixture(autouse=True)
def disable_auth():
    """Disable API key auth for all tests."""
    with patch.dict(os.environ, {"AUTH_DISABLED": "true"}):
        yield


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


class TestRootEndpoint:
    def test_root_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_root_has_name(self, client):
        data = client.get("/").json()
        assert "name" in data
        assert "Organization" in data["name"]

    def test_root_has_version(self, client):
        data = client.get("/").json()
        assert data["version"] == "1.0.0"

    def test_root_has_docs_link(self, client):
        data = client.get("/").json()
        assert data["docs"] == "/api/docs"


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_status_healthy(self, client):
        data = client.get("/health").json()
        assert data["status"] == "healthy"

    def test_health_has_timestamp(self, client):
        data = client.get("/health").json()
        assert "timestamp" in data

    def test_health_has_agents(self, client):
        data = client.get("/health").json()
        assert "agents" in data
        assert isinstance(data["agents"], list)

    def test_healthz_alias(self, client):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


class TestAgentsEndpoint:
    def test_list_agents_returns_200(self, client):
        resp = client.get("/api/agents")
        assert resp.status_code == 200

    def test_list_agents_has_agents_key(self, client):
        data = client.get("/api/agents").json()
        assert "agents" in data
        assert isinstance(data["agents"], list)

    def test_agent_has_required_fields(self, client):
        data = client.get("/api/agents").json()
        for agent in data["agents"]:
            assert "role" in agent
            assert "description" in agent
            assert "registered" in agent

    def test_expected_roles_present(self, client):
        data = client.get("/api/agents").json()
        roles = {a["role"] for a in data["agents"]}
        assert "CEO" in roles
        assert "CTO" in roles
        assert "Engineer_Backend" in roles


class TestProjectsEndpoint:
    def test_list_projects_returns_200(self, client):
        resp = client.get("/api/projects")
        assert resp.status_code == 200

    def test_list_projects_empty_initially(self, client):
        data = client.get("/api/projects").json()
        assert data["total"] == 0
        assert data["projects"] == []


class TestProjectStatusEndpoint:
    def test_nonexistent_project_returns_404(self, client):
        resp = client.get("/v1/projects/nonexistent-id")
        assert resp.status_code == 404


class TestStartProjectValidation:
    def test_idea_too_short_returns_422(self, client):
        resp = client.post("/v1/projects", json={"idea": "hi"})
        assert resp.status_code == 422

    def test_missing_idea_returns_422(self, client):
        resp = client.post("/v1/projects", json={})
        assert resp.status_code == 422
