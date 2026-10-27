
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.core.config import settings
import importlib


def test_get_prediction_existing_parking(client: TestClient):
    """Verify prediction endpoint calculates accurate invariants and schemas."""
    response = client.get(
        "/api/predictions/fixture-riverfront?target_time=2026-10-25T14:30:00"
    )
    assert response.status_code == 200
    pred = response.json()
    assert pred["parkingId"] == "fixture-riverfront"
    assert pred["totalCapacity"] == 420
    assert "predictedOccupiedSpaces" in pred
    assert "predictedFreeSpaces" in pred
    assert "occupancyPercentage" in pred
    assert (
        pred["predictedOccupiedSpaces"] + pred["predictedFreeSpaces"]
        == pred["totalCapacity"]
    )


def test_get_prediction_unknown_parking_returns_error(client: TestClient):
    """Ensure prediction for unknown ID produces standardized 404 JSON error."""
    response = client.get("/api/predictions/unknown-facility")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["type"] == "not_found"


def test_get_prediction_when_ml_module_unavailable_returns_503(
    client: TestClient,
):
    """A missing ML module must return 503, never a fabricated prediction."""
    real_import_module = importlib.import_module

    def import_module(name, package=None):
        if name == "ml_model.predict":
            raise ModuleNotFoundError(
                "No module named 'ml_model.predict'",
                name="ml_model.predict",
            )
        return real_import_module(name, package)

    with (
        patch.object(settings, "ML_ADAPTER_MODE", "module"),
        patch("importlib.import_module", side_effect=import_module),
    ):
        response = client.get("/api/predictions/fixture-riverfront")

    assert response.status_code == 503
    data = response.json()
    assert "error" in data
    assert data["error"]["type"] == "integration_unavailable"
    assert "ML Model" in data["error"]["message"]
