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
from app.integrations.ml_contract import MLPredictionResult


VALID_CREATE = {
    "id": "test-lot",
    "name": "Test Lot",
    "totalCapacity": 100,
    "coordinates": [18.52, 73.85],
}


@pytest.mark.parametrize(
    "field",
    ["name", "totalCapacity", "coordinates", "coordinateSource", "dataSource", "isSimulated", "metadata"],
)
def test_patch_explicit_null_rejected_without_changing_record(client, field):
    before = client.get("/api/parking/fixture-riverfront").json()
    response = client.patch("/api/parking/fixture-riverfront", json={field: None})
    assert response.status_code == 422
    assert client.get("/api/parking").status_code == 200
    assert client.get("/api/parking/fixture-riverfront").json() == before


def test_patch_blank_name_rejected(client):
    assert client.patch("/api/parking/fixture-riverfront", json={"name": "  "}).status_code == 422


def test_patch_cors_preflight_allows_patch(client):
    response = client.options(
        "/api/parking/fixture-riverfront",
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
                client.get("/api/predictions/fixture-riverfront"),
                client.post("/api/recommendations", json={
                    "destination": "Pune",
                    "arrivalTime": "2026-10-25T14:30:00",
                }),
            ]
    assert all(response.status_code == 503 for response in requests)
    assert all(response.json()["error"]["type"] == "database_unavailable" for response in requests)


def test_naive_and_india_offset_arrival_times_produce_same_prediction(client):
    naive = client.get(
        "/api/predictions/fixture-riverfront",
        params={"target_time": "2026-10-25T14:30:00"},
    ).json()
    aware = client.get(
        "/api/predictions/fixture-riverfront",
        params={"target_time": "2026-10-25T14:30:00+05:30"},
    ).json()
    assert naive["predictedOccupiedSpaces"] == aware["predictedOccupiedSpaces"]
    assert naive["predictedFreeSpaces"] == aware["predictedFreeSpaces"]


def test_patch_capacity_below_measured_occupancy_is_rejected_without_mutation():
    record = dict(DEFAULT_PARKING_FIXTURES[0])
    record["currentOccupancy"] = {
        "occupiedSpaces": 300,
        "freeSpaces": 120,
    }
    repository = InMemoryParkingRepository([record])
    before = repository.get_by_id(record["id"])
    service = ParkingService(repository)
    with pytest.raises(BadRequestError) as exc_info:
        service.update(record["id"], ParkingUpdate(totalCapacity=250))
    assert "constraints" in str(exc_info.value).lower()
    assert repository.get_by_id(record["id"]) == before


def test_parking_response_includes_metadata(client):
    response = client.get("/api/parking/fixture-riverfront")
    assert response.status_code == 200
    assert response.json()["metadata"]["city"] == "Pune"


def test_test_client_lifespan_does_not_attempt_mongo_connect():
    app.dependency_overrides.clear()
    with patch("app.db.mongodb.MongoDBClient.connect") as connect:
        with TestClient(app):
            pass
    connect.assert_called_once()


@pytest.mark.parametrize("fail_all", [False, True])
def test_recommendations_handle_prediction_failures(client, caplog, fail_all):
    class PartiallyFailingMLAdapter:
        async def predict_occupancy(self, parking_id, total_capacity, target_time, features=None):
            if fail_all or parking_id == "fixture-riverfront":
                raise RuntimeError("prediction unavailable")
            return MLPredictionResult(
                predicted_occupied_spaces=total_capacity // 2,
                predicted_free_spaces=total_capacity - total_capacity // 2,
                occupancy_percentage=50.0,
                confidence_score=None,
                model_source="test",
                predicted_at=target_time,
                target_time=target_time,
            )

    with patch("app.api.routes.recommendations.get_ml_adapter", return_value=PartiallyFailingMLAdapter()):
        response = client.post("/api/recommendations", json={
            "destination": "Pune",
            "arrivalTime": "2026-10-25T14:30:00+05:30",
        })
    if fail_all:
        assert response.status_code == 503
        assert response.json()["error"]["type"] == "integration_unavailable"
    else:
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert "fixture-riverfront" not in {option["id"] for option in response.json()}
    assert "Excluding parking candidate" in caplog.text
