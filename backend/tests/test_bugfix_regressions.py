from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.errors import BadRequestError
from app.db.mongodb import mongodb_client
from app.main import app
from app.repositories.dependencies import get_parking_repository
from app.repositories.parking_repository import InMemoryParkingRepository, DEFAULT_PARKING_FIXTURES
from app.schemas.parking import ParkingUpdate
from app.services.parking_service import ParkingService


VALID_CREATE = {
    "id": "test-lot",
    "name": "Test Lot",
    "totalCapacity": 100,
    "coordinates": [18.52, 73.85],
}


@pytest.mark.parametrize(
    "field",
    ["name", "totalCapacity", "coordinateSource", "dataSource", "isSimulated", "acceptedVehicleTypes", "metadata", "currentOccupancy"],
)
def test_patch_explicit_null_rejected_without_changing_record(client, field):
    before = client.get("/api/parking/P1").json()
    response = client.patch("/api/parking/P1", json={field: None})
    assert response.status_code == 422
    assert client.get("/api/parking").status_code == 200
    assert client.get("/api/parking/P1").json() == before


def test_patch_blank_name_rejected(client):
    assert client.patch("/api/parking/P1", json={"name": "  "}).status_code == 422


def test_patch_cors_preflight_allows_patch(client):
    response = client.options(
        "/api/parking/P1",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PATCH",
        },
    )
    assert response.status_code == 200
    assert "PATCH" in response.headers["access-control-allow-methods"]


def test_mongodb_outage_returns_503_for_parking_prediction_and_recommendations():
    app.dependency_overrides.clear()
    with patch("app.db.mongodb.MongoDBClient.connect"), patch.object(mongodb_client, "_db", None):
        with TestClient(app) as client:
            requests = [
                client.get("/api/parking"),
                client.get("/api/parking/not-found"),
                client.post("/api/parking", json=VALID_CREATE),
                client.patch("/api/parking/not-found", json={"name": "Changed"}),
                client.delete("/api/parking/not-found"),
                client.get("/api/predictions/P1"),
                client.post("/api/recommendations", json={
                    "destination": "Library",
                    "arrivalTime": "2026-10-25T14:30:00",
                }),
            ]
    assert all(response.status_code == 503 for response in requests)
    assert all(response.json()["error"]["type"] == "database_unavailable" for response in requests)


def test_naive_and_india_offset_arrival_times_produce_same_prediction(client):
    naive = client.get(
        "/api/predictions/P1",
        params={"target_time": "2026-10-25T14:30:00"},
    ).json()
    aware = client.get(
        "/api/predictions/P1",
        params={"target_time": "2026-10-25T14:30:00+05:30"},
    ).json()
    assert naive["predictedOccupiedSpaces"] == aware["predictedOccupiedSpaces"]
    assert naive["predictedFreeSpaces"] == aware["predictedFreeSpaces"]


def test_patch_capacity_below_measured_occupancy_is_rejected_without_mutation():
    record = dict(DEFAULT_PARKING_FIXTURES[0])
    record["currentOccupancy"] = {
        "occupiedSpaces": 300,
        "freeSpaces": 120,
        "vehicleCounts": {"car": 300},
    }
    repository = InMemoryParkingRepository([record])
    before = repository.get_by_id(record["id"])
    service = ParkingService(repository)
    with pytest.raises(BadRequestError) as exc_info:
        service.update(record["id"], ParkingUpdate(totalCapacity=250))
    assert "constraints" in str(exc_info.value).lower()
    assert repository.get_by_id(record["id"]) == before


def test_parking_response_includes_simulation_metadata(client):
    response = client.get("/api/parking/P1")
    assert response.status_code == 200
    assert response.json()["dataSource"] == "simulated-campus-v1"
    assert response.json()["isSimulated"] is True


def test_test_client_lifespan_does_not_attempt_mongo_connect():
    app.dependency_overrides.clear()
    with patch("app.db.mongodb.MongoDBClient.connect") as connect:
        with TestClient(app):
            pass
    connect.assert_called_once()


def test_recommendations_use_repository_occupancy_without_calling_ml(client):
    response = client.post("/api/recommendations", json={
        "destination": "Library",
        "entryGate": "gate_north",
        "vehicleType": "car",
    })
    assert response.status_code == 200
    p1 = next(option for option in response.json() if option["id"] == "P1")
    assert p1["occupiedSpaces"] == 15
    assert p1["availableSpaces"] == 35
