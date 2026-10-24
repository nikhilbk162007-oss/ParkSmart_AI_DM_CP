from fastapi.testclient import TestClient
from unittest.mock import patch
from app.repositories.dependencies import get_parking_repository
from app.repositories.parking_repository import InMemoryParkingRepository
from app.core.config import settings
from app.main import app


def test_get_recommendations_success(client: TestClient):
    """Ensure recommendations comply strictly with frontend contract."""
    payload = {
        "destination": "Riverfront, Pune",
        "arrivalTime": "2026-10-25T14:30:00"
    }
    response = client.post("/api/recommendations", json=payload)
    assert response.status_code == 200
    results = response.json()

    assert isinstance(results, list)
    assert len(results) >= 3

    seen_ids = set()
    has_recommended = False

    for opt in results:
        assert "id" in opt and opt["id"]
        assert opt["id"] not in seen_ids
        seen_ids.add(opt["id"])

        assert "name" in opt and isinstance(opt["name"], str)
        assert "totalCapacity" in opt and isinstance(opt["totalCapacity"], int)
        assert "predictedOccupiedSpaces" in opt and isinstance(opt["predictedOccupiedSpaces"], int)
        assert "predictedFreeSpaces" in opt and isinstance(opt["predictedFreeSpaces"], int)
        assert "distanceKm" in opt and isinstance(opt["distanceKm"], (int, float))
        assert "coordinates" in opt and len(opt["coordinates"]) == 2

        # Pune / Maharashtra coordinate bounding check
        lat, lon = opt["coordinates"]
        assert 6.5 <= lat <= 35.7
        assert 68.1 <= lon <= 97.4

        # Strict occupancy invariant required by frontend
        assert opt["predictedOccupiedSpaces"] + opt["predictedFreeSpaces"] == opt["totalCapacity"]

        if opt.get("recommendationStatus") == "Recommended":
            has_recommended = True

    assert has_recommended is True


def test_get_recommendations_with_timezone_timestamp(client: TestClient):
    """Accept ISO-8601 with timezone offsets or UTC Z."""
    payload = {
        "destination": "Market Street, Pune",
        "arrivalTime": "2026-10-25T14:30:00+05:30"
    }
    response = client.post("/api/recommendations", json=payload)
    assert response.status_code == 200
    assert len(response.json()) >= 3


def test_get_recommendations_invalid_timestamp_returns_422(client: TestClient):
    """Ensure invalid timestamp string produces a 422 error."""
    payload = {
        "destination": "Riverfront, Pune",
        "arrivalTime": "not-a-valid-timestamp"
    }
    response = client.post("/api/recommendations", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["type"] == "validation_error"


def test_get_recommendations_empty_destination_returns_422(client: TestClient):
    """Ensure empty or whitespace-only destination produces a 422 error."""
    payload = {
        "destination": "   ",
        "arrivalTime": "2026-10-25T14:30:00"
    }
    response = client.post("/api/recommendations", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["type"] == "validation_error"


def test_get_recommendations_when_no_parking_available_returns_empty_list(client: TestClient):
    """When the database has zero records, returns [] without crashing."""
    empty_repo = InMemoryParkingRepository([])
    app.dependency_overrides[get_parking_repository] = lambda: empty_repo
    try:
        payload = {
            "destination": "Riverfront, Pune",
            "arrivalTime": "2026-10-25T14:30:00"
        }
        response = client.post("/api/recommendations", json=payload)
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


def test_get_recommendations_when_engine_unavailable_returns_503(client: TestClient):
    """When REC_ADAPTER_MODE is 'module' and engine is unconfigured, return 503."""
    with patch.object(settings, "REC_ADAPTER_MODE", "module"):
        payload = {
            "destination": "Riverfront, Pune",
            "arrivalTime": "2026-10-25T14:30:00"
        }
        response = client.post("/api/recommendations", json=payload)
        assert response.status_code == 503
        data = response.json()
        assert "error" in data
        assert data["error"]["type"] == "integration_unavailable"
        assert "Recommendation Engine" in data["error"]["message"]
