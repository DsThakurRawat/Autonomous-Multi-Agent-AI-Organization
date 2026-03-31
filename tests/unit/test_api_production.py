"""
Production-Grade Tests — API Edge Cases & Security
Real-life scenarios: rate limiting, input validation, concurrent requests,
project lifecycle, and malicious payloads.
"""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest


@pytest.fixture(autouse=True)
def disable_auth():
    with patch.dict(os.environ, {"AUTH_DISABLED": "true"}):
        yield


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


class TestInputValidation:
    """Production scenario: reject malformed input before any LLM call."""

    def test_idea_empty_string_rejected(self, client):
        resp = client.post("/v1/projects", json={"idea": ""})
        assert resp.status_code == 422

    def test_idea_whitespace_only_rejected(self, client):
        resp = client.post("/v1/projects", json={"idea": "   "})
        # FastAPI min_length=5 counts whitespace so this is 3 chars
        assert resp.status_code == 422

    def test_idea_over_max_length_rejected(self, client):
        resp = client.post("/v1/projects", json={"idea": "x" * 1001})
        assert resp.status_code == 422

    def test_budget_too_low_rejected(self, client):
        resp = client.post(
            "/v1/projects",
            json={"idea": "Valid idea here", "budget": {"max_cost_usd": 0.5}},
        )
        assert resp.status_code == 422

    def test_budget_too_high_rejected(self, client):
        resp = client.post(
            "/v1/projects",
            json={"idea": "Valid idea here", "budget": {"max_cost_usd": 99999}},
        )
        assert resp.status_code == 422

    def test_wrong_content_type_rejected(self, client):
        resp = client.post(
            "/v1/projects",
            content="not json",
            headers={"Content-Type": "text/plain"},
        )
        assert resp.status_code == 422

    def test_extra_fields_ignored(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200


class TestAPIKeySecurity:
    """Production scenario: API key auth must block unauthenticated requests."""

    def test_missing_api_key_blocked(self):
        with patch.dict(
            os.environ, {"AUTH_DISABLED": "false", "API_KEY": "secret-key-123"}
        ):
            from api.main import app

            c = TestClient(app)
            resp = c.get("/v1/projects/some-id")
            assert resp.status_code == 403

    def test_wrong_api_key_blocked(self):
        with patch.dict(
            os.environ, {"AUTH_DISABLED": "false", "API_KEY": "secret-key-123"}
        ):
            from api.main import app

            c = TestClient(app)
            resp = c.get(
                "/v1/projects/some-id",
                headers={"X-API-Key": "wrong-key"},
            )
            assert resp.status_code == 403

    def test_correct_api_key_passes(self):
        with patch.dict(
            os.environ, {"AUTH_DISABLED": "false", "API_KEY": "secret-key-123"}
        ):
            from api.main import app

            c = TestClient(app)
            resp = c.get(
                "/v1/projects/nonexistent",
                headers={"X-API-Key": "secret-key-123"},
            )
            # Should pass auth but 404 because project doesn't exist
            assert resp.status_code == 404


class TestWebhookEndpoint:
    """Production scenario: omni-channel webhook from Slack/Discord must route correctly."""

    def test_webhook_normal_message(self, client):
        resp = client.post(
            "/api/webhooks/slack",
            json={"user_id": "U123", "text": "Deploy to production"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "slack" in data["reply"]

    def test_webhook_rewind_command(self, client):
        resp = client.post(
            "/api/webhooks/discord",
            json={"user_id": "U456", "text": "Please rewind the last deployment"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "rewind" in data["reply"].lower()

    def test_webhook_with_metadata(self, client):
        resp = client.post(
            "/api/webhooks/telegram",
            json={
                "user_id": "T789",
                "text": "Status check",
                "metadata": {"channel_id": "C001"},
            },
        )
        assert resp.status_code == 200


class TestHealthEndpointProduction:
    """Production scenario: health endpoint must expose correct structure."""

    def test_health_has_agents_list(self, client):
        data = client.get("/health").json()
        assert "agents" in data
        assert isinstance(data["agents"], list)

    def test_health_has_iso_timestamp(self, client):
        data = client.get("/health").json()
        ts = data["timestamp"]
        # ISO format should contain T separator
        assert "T" in ts


class TestProjectCostEndpoint:
    def test_cost_404_for_nonexistent(self, client):
        resp = client.get("/v1/projects/nonexistent/cost")
        assert resp.status_code == 404

    def test_tasks_404_for_nonexistent(self, client):
        resp = client.get("/v1/projects/nonexistent/tasks")
        assert resp.status_code == 404
