from fastapi.testclient import TestClient
from unittest.mock import patch
from app.db.mongodb import mongodb_client


def test_health_check_endpoint_when_db_online(client: TestClient):
    """Health check endpoint returns 200 OK when both API and DB are healthy."""
    with patch.object(mongodb_client, "check_health", return_value=True):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["api"] == "online"
        assert data["database"]["status"] == "connected"
        assert data["database"]["ping"] is True
        assert data["version"] == "1.0.0"


def test_health_check_endpoint_when_db_offline(client: TestClient):
    """Health check endpoint returns 503 Service Unavailable when DB is disconnected."""
    with patch.object(mongodb_client, "check_health", return_value=False):
        response = client.get("/api/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["api"] == "online"
        assert data["database"]["status"] == "disconnected"
        assert data["database"]["ping"] is False


def test_root_endpoint(client: TestClient):
    """Root endpoint returns basic project status and documentation path."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "ParkSmart AI"
    assert data["role"] == "Backend & Database Service"
    assert data["status"] == "online"
