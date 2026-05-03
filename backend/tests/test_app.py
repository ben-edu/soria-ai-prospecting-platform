"""Tests for app import and health endpoint."""

from fastapi.testclient import TestClient

from app.main import app


def test_app_import():
    """Verify the FastAPI app imports and has expected title."""
    assert app.title == "SORIA AI Prospecting Platform"


def test_health_endpoint():
    """Verify the health endpoint returns OK."""
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "SORIA AI Prospecting Platform"
