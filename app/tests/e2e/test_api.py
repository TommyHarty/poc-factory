"""API endpoint tests."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def test_app():
    """Create a test FastAPI app instance."""
    from app.main import create_app
    return create_app()


@pytest.fixture
async def client(test_app):
    """Create an async HTTP test client."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as c:
        yield c


class TestHealthEndpoints:
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    async def test_root(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "POC Factory" in data["name"]


class TestRunCreation:
    async def test_create_run_basic(self, client):
        """Test creating a basic run."""
        with patch(
            "app.application.orchestrators.run_orchestrator.RunOrchestrator.create_run",
            new_callable=AsyncMock,
            return_value="test-run-id-001",
        ):
            with patch(
                "app.application.orchestrators.run_orchestrator.RunOrchestrator.start_run_background"
            ):
                response = await client.post(
                    "/runs",
                    json={
                        "phrase": "prompt injection guardrails",
                        "technologies": ["fastapi", "pydantic"],
                        "target_poc_count": 8,
                    },
                )

        assert response.status_code == 202
        data = response.json()
        assert data["run_id"] == "test-run-id-001"
        assert data["status"] == "running"

    async def test_create_run_validates_phrase(self, client):
        """Test that short phrases are rejected."""
        response = await client.post(
            "/runs",
            json={"phrase": "ab"},  # Too short
        )
        assert response.status_code == 422

    async def test_create_run_validates_poc_count_low(self, client):
        """Test that poc count below 8 is rejected."""
        response = await client.post(
            "/runs",
            json={
                "phrase": "prompt injection guardrails",
                "target_poc_count": 3,
            },
        )
        assert response.status_code == 422

    async def test_create_run_validates_poc_count_high(self, client):
        """Test that poc count above 15 is rejected."""
        response = await client.post(
            "/runs",
            json={
                "phrase": "prompt injection guardrails",
                "target_poc_count": 20,
            },
        )
        assert response.status_code == 422

    async def test_create_run_with_starter_repo(self, client):
        """Test creating a run with a starter repo."""
        with patch(
            "app.application.orchestrators.run_orchestrator.RunOrchestrator.create_run",
            new_callable=AsyncMock,
            return_value="test-run-id-002",
        ):
            with patch(
                "app.application.orchestrators.run_orchestrator.RunOrchestrator.start_run_background"
            ):
                response = await client.post(
                    "/runs",
                    json={
                        "phrase": "tool calling reliability",
                        "technologies": ["langgraph", "fastapi"],
                        "target_poc_count": 10,
                        "starter_repo": {
                            "provider": "github",
                            "repo_url": "https://github.com/org/starter.git",
                            "branch": "main",
                        },
                    },
                )

        assert response.status_code == 202

    async def test_create_run_dry_run_flag(self, client):
        """Test creating a run with dry_run flag."""
        with patch(
            "app.application.orchestrators.run_orchestrator.RunOrchestrator.create_run",
            new_callable=AsyncMock,
            return_value="dry-run-id",
        ):
            with patch(
                "app.application.orchestrators.run_orchestrator.RunOrchestrator.start_run_background"
            ):
                response = await client.post(
                    "/runs",
                    json={
                        "phrase": "monitoring and observability",
                        "dry_run": True,
                    },
                )

        assert response.status_code == 202


class TestRunStatus:
    async def test_get_run_status_not_found(self, client):
        """Test getting status of non-existent run."""
        with patch(
            "app.application.orchestrators.run_orchestrator.RunOrchestrator.get_run_status",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = await client.get("/runs/nonexistent-id")

        assert response.status_code == 404

    async def test_get_run_status_found(self, client):
        """Test getting status of an existing run."""
        mock_state = {
            "run_id": "test-001",
            "phrase": "prompt injection guardrails",
            "normalized_phrase": "prompt injection guardrails",
            "slug": "prompt-injection-guardrails",
            "run_status": "running",
            "technologies": ["fastapi"],
            "optional_packages": [],
            "target_poc_count": 10,
            "selected_pocs": [],
            "poc_executions": [],
            "errors": [],
            "warnings": [],
            "started_at": None,
            "completed_at": None,
            "run_output_path": "/output/prompt-injection-guardrails",
        }

        with patch(
            "app.application.orchestrators.run_orchestrator.RunOrchestrator.get_run_status",
            new_callable=AsyncMock,
            return_value=mock_state,
        ):
            response = await client.get("/runs/test-001")

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == "test-001"
        assert data["run_status"] == "running"

    async def test_get_run_artifacts_not_found(self, client):
        """Test getting artifacts of non-existent run."""
        with patch(
            "app.application.orchestrators.run_orchestrator.RunOrchestrator.get_run_status",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = await client.get("/runs/nonexistent/artifacts")

        assert response.status_code == 404

    async def test_retry_failures_no_failures(self, client):
        """Test retrying when there are no failures."""
        mock_state = {
            "run_id": "test-001",
            "phrase": "test",
            "normalized_phrase": "test",
            "slug": "test",
            "run_status": "completed",
            "technologies": [],
            "optional_packages": [],
            "target_poc_count": 10,
            "selected_pocs": [],
            "poc_executions": [
                {"poc_slug": "01-test", "build_status": "succeeded"}
            ],
            "errors": [],
            "warnings": [],
        }

        with patch(
            "app.application.orchestrators.run_orchestrator.RunOrchestrator.get_run_status",
            new_callable=AsyncMock,
            return_value=mock_state,
        ):
            response = await client.post("/runs/test-001/retry-failures")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "no_failures"
