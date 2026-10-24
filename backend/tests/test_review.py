"""
Comprehensive code-review test suite for ParkSmart AI backend.
Covers every requirement from the review checklist:
  1. Invalid JSON and schema validation errors
  2. Missing required fields
  3. Negative capacity, occupied/free > capacity, invalid coordinates (via HTTP API)
  4. Duplicate IDs, unknown IDs
  5. Empty database results
  6. Predicted vs Measured occupancy separation
  7. Unavailable integrations → no fabricated success output
  8. Database errors handled (no internal leakage)
  9. CORS configuration
 10. Config defaults and secret handling
 11. Unique IDs across all returned records
 12. Response schemas match documented contracts
 13. Update (PATCH) and delete of missing resource
 14. Deterministic, no live MongoDB required
"""
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.core.config import settings
from app.core.errors import EntityNotFoundError, DuplicateEntityError
from app.db.mongodb import mongodb_client, MongoDBClient
from app.models.parking import ParkingFacility, CurrentOccupancyMeasured
from app.schemas.parking import ParkingCreate, ParkingBaseResponse
from app.schemas.prediction import PredictionResponse
from app.schemas.recommendation import ParkingOption
from app.repositories.parking_repository import (
    InMemoryParkingRepository,
    MongoParkingRepository,
)
from app.repositories.dependencies import get_parking_repository
from app.services.parking_service import ParkingService


VALID_FIXTURE_ID = "fixture-riverfront"


def _cleanup():
    app.dependency_overrides.clear()


# ===========================================================================
# 1. CONFIG / DEFAULTS / SECRET HANDLING
# ===========================================================================

class TestConfigDefaults:
    def test_mongodb_uri_has_default(self):
        assert settings.MONGODB_URI
        assert settings.MONGODB_URI.startswith("mongodb://")

    def test_environment_default_is_valid(self):
        assert settings.ENVIRONMENT in ("development", "test", "production")

    def test_cors_origins_is_list(self):
        assert isinstance(settings.CORS_ORIGINS, list)
        assert len(settings.CORS_ORIGINS) >= 1

    def test_cors_origins_from_comma_string(self):
        from app.core.config import Settings
        s = Settings(CORS_ORIGINS="http://a.com,http://b.com")
        assert s.CORS_ORIGINS == ["http://a.com", "http://b.com"]

    def test_cors_origins_from_json_array_string(self):
        from app.core.config import Settings
        s = Settings(CORS_ORIGINS='["http://a.com","http://b.com"]')
        assert s.CORS_ORIGINS == ["http://a.com", "http://b.com"]

    def test_adapter_modes_valid(self):
        assert settings.ML_ADAPTER_MODE in ("mock", "module", "http")
        assert settings.REC_ADAPTER_MODE in ("mock", "module", "http")

    def test_timeouts_positive(self):
        assert settings.ML_TIMEOUT_SECONDS > 0
        assert settings.REC_TIMEOUT_SECONDS > 0

    def test_mongodb_selection_timeout_positive(self):
        assert settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS > 0


# ===========================================================================
# 2. CORS CONFIGURATION
# ===========================================================================

class TestCORSConfiguration:
    def test_cors_get_request_reflects_origin(self, client: TestClient):
        res = client.get(
            "/api/parking",
            headers={"Origin": "http://localhost:5173"},
        )
        assert res.status_code == 200
        assert "access-control-allow-origin" in res.headers


# ===========================================================================
# 3. MODEL VALIDATION — ParkingFacility (unit)
# ===========================================================================

class TestParkingFacilityModelValidation:
    def test_whitespace_only_id_rejected(self):
        with pytest.raises(ValidationError, match="cannot be empty or whitespace"):
            ParkingFacility(
                id="   ", name="Test", totalCapacity=100,
                coordinates=[18.52, 73.85],
            )

    def test_whitespace_only_name_rejected(self):
        with pytest.raises(ValidationError, match="cannot be empty or whitespace"):
            ParkingFacility(
                id="lot-x", name="\t\n ", totalCapacity=100,
                coordinates=[18.52, 73.85],
            )

    def test_negative_total_capacity_rejected(self):
        with pytest.raises(ValidationError):
            ParkingFacility(
                id="lot-neg", name="Negative", totalCapacity=-1,
                coordinates=[18.52, 73.85],
            )

    def test_latitude_above_90_rejected(self):
        with pytest.raises(ValidationError, match="Latitude"):
            ParkingFacility(id="x", name="X", totalCapacity=10, coordinates=[91.0, 73.85])

    def test_latitude_below_minus90_rejected(self):
        with pytest.raises(ValidationError, match="Latitude"):
            ParkingFacility(id="x", name="X", totalCapacity=10, coordinates=[-91.0, 73.85])

    def test_longitude_above_180_rejected(self):
        with pytest.raises(ValidationError, match="Longitude"):
            ParkingFacility(id="x", name="X", totalCapacity=10, coordinates=[18.52, 181.0])

    def test_longitude_below_minus180_rejected(self):
        with pytest.raises(ValidationError, match="Longitude"):
            ParkingFacility(id="x", name="X", totalCapacity=10, coordinates=[18.52, -181.0])

    def test_missing_coordinates_rejected(self):
        with pytest.raises(ValidationError):
            ParkingFacility(id="x", name="X", totalCapacity=100)

    def test_occupied_exceeds_capacity_rejected(self):
        with pytest.raises(ValidationError, match="cannot exceed totalCapacity"):
            ParkingFacility(
                id="x", name="X", totalCapacity=100,
                coordinates=[18.52, 73.85],
                currentOccupancy=CurrentOccupancyMeasured(occupiedSpaces=110, freeSpaces=0),
            )

    def test_occupied_plus_free_not_equal_capacity_rejected(self):
        with pytest.raises(ValidationError, match="must equal totalCapacity"):
            ParkingFacility(
                id="x", name="X", totalCapacity=100,
                coordinates=[18.52, 73.85],
                currentOccupancy=CurrentOccupancyMeasured(occupiedSpaces=60, freeSpaces=50),
            )

    def test_zero_capacity_without_occupancy_is_valid(self):
        f = ParkingFacility(id="lot-zero", name="Closed", totalCapacity=0,
                            coordinates=[18.52, 73.85])
        assert f.total_capacity == 0
        assert f.current_occupancy is None

    def test_facility_model_has_no_predicted_fields(self):
        """ParkingFacility must NOT contain any 'predicted' occupancy fields."""
        facility_fields = set(ParkingFacility.model_fields.keys())
        for field_name in facility_fields:
            assert "predict" not in field_name.lower(), (
                f"ParkingFacility has a predicted field '{field_name}'; "
                "predictions belong in PredictionResponse, not the facility model."
            )

    def test_measured_occupancy_auto_computes_percentage(self):
        occ = CurrentOccupancyMeasured(occupiedSpaces=75, freeSpaces=25)
        assert occ.occupancy_percentage == 75.0

    def test_is_simulated_defaults_to_true(self):
        f = ParkingFacility(id="lot-def", name="Default", totalCapacity=50,
                            coordinates=[18.52, 73.85])
        assert f.is_simulated is True


# ===========================================================================
# 4. PredictionResponse — predicted vs measured separation
# ===========================================================================

class TestPredictionVsMeasuredSeparation:
    def test_prediction_response_has_no_current_occupancy(self):
        pred = PredictionResponse(
            parkingId="lot-1",
            targetTime="2026-10-25T14:30:00+00:00",
            totalCapacity=100,
            predictedOccupiedSpaces=60,
            predictedFreeSpaces=40,
            occupancyPercentage=60.0,
            modelSource="simulated-baseline",
        )
        assert not hasattr(pred, "current_occupancy")
        assert not hasattr(pred, "currentOccupancy")

    def test_prediction_invariant_violated_raises(self):
        with pytest.raises(ValidationError):
            PredictionResponse(
                parkingId="lot-1",
                targetTime="2026-10-25T14:30:00+00:00",
                totalCapacity=100,
                predictedOccupiedSpaces=60,
                predictedFreeSpaces=50,  # 110 != 100
                occupancyPercentage=60.0,
            )

    def test_parking_base_response_has_no_predicted_fields(self):
        response_fields = set(ParkingBaseResponse.model_fields.keys())
        assert "predicted_occupied_spaces" not in response_fields
        assert "predicted_free_spaces" not in response_fields

    def test_recommendation_option_has_predicted_not_measured(self):
        option_fields = set(ParkingOption.model_fields.keys())
        assert "predicted_occupied_spaces" in option_fields
        assert "predicted_free_spaces" in option_fields
        assert "current_occupancy" not in option_fields


# ===========================================================================
# 5. HTTP API — Invalid JSON & Schema Validation
# ===========================================================================

class TestAPISchemaValidation:
    def test_post_parking_invalid_json_returns_422(self, client: TestClient):
        res = client.post(
            "/api/parking",
            content=b"{not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert res.status_code == 422

    def test_post_parking_missing_id_returns_422(self, client: TestClient):
        res = client.post("/api/parking", json={
            "name": "Missing ID", "totalCapacity": 100, "coordinates": [18.52, 73.85]
        })
        assert res.status_code == 422
        assert res.json()["error"]["type"] == "validation_error"

    def test_post_parking_missing_name_returns_422(self, client: TestClient):
        res = client.post("/api/parking", json={
            "id": "lot-no-name", "totalCapacity": 100, "coordinates": [18.52, 73.85]
        })
        assert res.status_code == 422

    def test_post_parking_missing_coordinates_returns_422(self, client: TestClient):
        res = client.post("/api/parking", json={
            "id": "lot-no-coords", "name": "No Coords", "totalCapacity": 100
        })
        assert res.status_code == 422

    def test_post_parking_negative_capacity_returns_422(self, client: TestClient):
        res = client.post("/api/parking", json={
            "id": "lot-neg", "name": "Neg Cap", "totalCapacity": -50,
            "coordinates": [18.52, 73.85]
        })
        assert res.status_code == 422
        assert res.json()["error"]["type"] == "validation_error"

    def test_post_parking_invalid_lat_returns_422(self, client: TestClient):
        res = client.post("/api/parking", json={
            "id": "lot-badlat", "name": "Bad Lat", "totalCapacity": 100,
            "coordinates": [200.0, 73.85]
        })
        assert res.status_code == 422

    def test_post_parking_invalid_lon_returns_422(self, client: TestClient):
        res = client.post("/api/parking", json={
            "id": "lot-badlon", "name": "Bad Lon", "totalCapacity": 100,
            "coordinates": [18.52, -200.0]
        })
        assert res.status_code == 422

    def test_post_parking_whitespace_id_returns_422(self, client: TestClient):
        res = client.post("/api/parking", json={
            "id": "   ", "name": "Whitespace ID", "totalCapacity": 100,
            "coordinates": [18.52, 73.85]
        })
        assert res.status_code == 422

    def test_post_parking_occupied_exceeds_capacity_returns_422(self, client: TestClient):
        res = client.post("/api/parking", json={
            "id": "lot-overflow", "name": "Overflow", "totalCapacity": 100,
            "coordinates": [18.52, 73.85],
            "currentOccupancy": {"occupiedSpaces": 150, "freeSpaces": 0}
        })
        assert res.status_code == 422

    def test_post_parking_occupied_plus_free_mismatch_returns_422(self, client: TestClient):
        res = client.post("/api/parking", json={
            "id": "lot-mismatch", "name": "Mismatch", "totalCapacity": 100,
            "coordinates": [18.52, 73.85],
            "currentOccupancy": {"occupiedSpaces": 60, "freeSpaces": 60}
        })
        assert res.status_code == 422

    def test_post_parking_extra_fields_ignored_not_500(self, client: TestClient):
        res = client.post("/api/parking", json={
            "id": "lot-extra", "name": "Extra Fields", "totalCapacity": 50,
            "coordinates": [18.52, 73.85],
            "unknownField": "should-be-ignored",
        })
        assert res.status_code in (201, 422)
        if res.status_code == 201:
            assert "unknownField" not in res.json()


# ===========================================================================
# 6. HTTP API — Parking CRUD & ID Uniqueness
# ===========================================================================

class TestParkingCRUD:
    def test_all_returned_ids_unique(self, client: TestClient):
        res = client.get("/api/parking")
        assert res.status_code == 200
        ids = [item["id"] for item in res.json()]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"

    def test_create_returns_201_with_required_schema_fields(self, client: TestClient):
        res = client.post("/api/parking", json={
            "id": "lot-create-review", "name": "Create Review Lot",
            "totalCapacity": 300, "coordinates": [18.52, 73.85], "isSimulated": True
        })
        assert res.status_code == 201
        data = res.json()
        assert data["id"] == "lot-create-review"
        assert data["totalCapacity"] == 300
        assert "isSimulated" in data
        assert "dataSource" in data
        assert "coordinateSource" in data
        # Must NOT have prediction fields in a parking record
        assert "predictedOccupiedSpaces" not in data
        assert "predictedFreeSpaces" not in data

    def test_create_duplicate_returns_409_with_structured_error(self, client: TestClient):
        res = client.post("/api/parking", json={
            "id": VALID_FIXTURE_ID, "name": "Dupe",
            "totalCapacity": 100, "coordinates": [18.52, 73.85]
        })
        assert res.status_code == 409
        data = res.json()
        assert data["error"]["type"] == "duplicate_entity"
        assert VALID_FIXTURE_ID in data["error"]["message"]
        assert data["error"]["status_code"] == 409

    def test_get_unknown_id_returns_structured_404(self, client: TestClient):
        res = client.get("/api/parking/does-not-exist-xyz")
        assert res.status_code == 404
        data = res.json()
        assert data["error"]["type"] == "not_found"
        assert "does-not-exist-xyz" in data["error"]["message"]

    def test_no_internal_fields_in_response(self, client: TestClient):
        res = client.get(f"/api/parking/{VALID_FIXTURE_ID}")
        assert res.status_code == 200
        data = res.json()
        assert "_id" not in data
        assert "$oid" not in str(data)

    def test_delete_unknown_returns_404(self, client: TestClient):
        res = client.delete("/api/parking/ghost-id-999")
        assert res.status_code == 404
        assert res.json()["error"]["type"] == "not_found"

    def test_patch_unknown_returns_404(self, client: TestClient):
        res = client.patch("/api/parking/ghost-id-999", json={"name": "Updated"})
        assert res.status_code == 404
        assert res.json()["error"]["type"] == "not_found"

    def test_patch_existing_updates_name(self, client: TestClient):
        res = client.patch(f"/api/parking/{VALID_FIXTURE_ID}", json={"name": "Renamed"})
        assert res.status_code == 200
        assert res.json()["name"] == "Renamed"

    def test_patch_invalid_capacity_returns_422(self, client: TestClient):
        res = client.patch(f"/api/parking/{VALID_FIXTURE_ID}", json={"totalCapacity": -999})
        assert res.status_code == 422

    def test_filter_min_capacity(self, client: TestClient):
        res = client.get("/api/parking?minCapacity=500")
        assert res.status_code == 200
        assert all(item["totalCapacity"] >= 500 for item in res.json())

    def test_filter_limit(self, client: TestClient):
        res = client.get("/api/parking?limit=1")
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_empty_db_returns_empty_array_not_fallback(self, client: TestClient):
        empty_repo = InMemoryParkingRepository([])
        app.dependency_overrides[get_parking_repository] = lambda: empty_repo
        try:
            res = client.get("/api/parking")
            assert res.status_code == 200
            assert res.json() == []
        finally:
            _cleanup()

    def test_ids_are_stable_strings_not_objectid(self, client: TestClient):
        res = client.get("/api/parking")
        assert res.status_code == 200
        for item in res.json():
            assert isinstance(item["id"], str)
            assert len(item["id"]) > 0
            assert "$oid" not in str(item["id"])


# ===========================================================================
# 7. HTTP API — Predictions
# ===========================================================================

class TestPredictionsAPI:
    def test_prediction_response_has_predicted_not_measured_fields(self, client: TestClient):
        res = client.get(f"/api/predictions/{VALID_FIXTURE_ID}?target_time=2026-10-25T12:00:00")
        assert res.status_code == 200
        data = res.json()
        # Correct predicted fields present
        assert "predictedOccupiedSpaces" in data
        assert "predictedFreeSpaces" in data
        assert "occupancyPercentage" in data
        assert "modelSource" in data
        assert "parkingId" in data
        assert "totalCapacity" in data
        # Measured fields must NOT appear at top level
        assert "occupiedSpaces" not in data
        assert "currentOccupancy" not in data
        assert "freeSpaces" not in data

    def test_prediction_invariant(self, client: TestClient):
        res = client.get(f"/api/predictions/{VALID_FIXTURE_ID}?target_time=2026-10-25T12:00:00")
        assert res.status_code == 200
        data = res.json()
        assert data["predictedOccupiedSpaces"] + data["predictedFreeSpaces"] == data["totalCapacity"]

    def test_prediction_percentage_in_bounds(self, client: TestClient):
        res = client.get(f"/api/predictions/{VALID_FIXTURE_ID}?target_time=2026-10-25T12:00:00")
        assert res.status_code == 200
        pct = res.json()["occupancyPercentage"]
        assert 0.0 <= pct <= 100.0

    def test_mock_prediction_labeled_simulated_baseline(self, client: TestClient):
        res = client.get(f"/api/predictions/{VALID_FIXTURE_ID}?target_time=2026-10-25T12:00:00")
        assert res.status_code == 200
        assert res.json()["modelSource"] == "simulated-baseline"

    def test_prediction_unknown_id_returns_404(self, client: TestClient):
        res = client.get("/api/predictions/nonexistent-id")
        assert res.status_code == 404
        assert res.json()["error"]["type"] == "not_found"

    def test_ml_module_unavailable_returns_503_not_fabricated_200(self, client: TestClient):
        """When ML module is missing → 503, never a fabricated successful prediction."""
        with patch.object(settings, "ML_ADAPTER_MODE", "module"):
            res = client.get(f"/api/predictions/{VALID_FIXTURE_ID}")
        assert res.status_code == 503
        data = res.json()
        assert data["error"]["type"] == "integration_unavailable"
        assert "predictedOccupiedSpaces" not in data
        assert "predictedFreeSpaces" not in data

    def test_ml_http_unavailable_returns_503(self, client: TestClient):
        with patch.object(settings, "ML_ADAPTER_MODE", "http"), \
             patch.object(settings, "ML_SERVICE_URL", "http://127.0.0.1:59998"):
            res = client.get(f"/api/predictions/{VALID_FIXTURE_ID}?target_time=2026-10-25T12:00:00")
        assert res.status_code == 503

    def test_prediction_is_deterministic(self, client: TestClient):
        url = f"/api/predictions/{VALID_FIXTURE_ID}?target_time=2026-10-25T14:00:00"
        r1 = client.get(url).json()
        r2 = client.get(url).json()
        assert r1["predictedOccupiedSpaces"] == r2["predictedOccupiedSpaces"]
        assert r1["predictedFreeSpaces"] == r2["predictedFreeSpaces"]


# ===========================================================================
# 8. HTTP API — Recommendations
# ===========================================================================

class TestRecommendationsAPI:
    def test_recommendations_ids_unique(self, client: TestClient):
        res = client.post("/api/recommendations", json={
            "destination": "Pune", "arrivalTime": "2026-10-25T14:30:00"
        })
        assert res.status_code == 200
        ids = [item["id"] for item in res.json()]
        assert len(ids) == len(set(ids))

    def test_recommendation_schema_fields(self, client: TestClient):
        res = client.post("/api/recommendations", json={
            "destination": "Riverfront, Pune", "arrivalTime": "2026-10-25T09:00:00"
        })
        assert res.status_code == 200
        for opt in res.json():
            assert "id" in opt
            assert "name" in opt
            assert "totalCapacity" in opt
            assert "predictedOccupiedSpaces" in opt
            assert "predictedFreeSpaces" in opt
            assert "distanceKm" in opt
            assert "coordinates" in opt
            # Must be predicted, not measured
            assert "occupiedSpaces" not in opt
            assert "currentOccupancy" not in opt

    def test_recommendation_invariant(self, client: TestClient):
        res = client.post("/api/recommendations", json={
            "destination": "Pune", "arrivalTime": "2026-10-25T14:30:00"
        })
        assert res.status_code == 200
        for opt in res.json():
            assert (opt["predictedOccupiedSpaces"] + opt["predictedFreeSpaces"]
                    == opt["totalCapacity"])

    def test_recommendation_missing_destination_returns_422(self, client: TestClient):
        res = client.post("/api/recommendations", json={"arrivalTime": "2026-10-25T14:30:00"})
        assert res.status_code == 422

    def test_recommendation_missing_arrival_time_returns_422(self, client: TestClient):
        res = client.post("/api/recommendations", json={"destination": "Pune"})
        assert res.status_code == 422

    def test_recommendation_invalid_json_returns_422(self, client: TestClient):
        res = client.post(
            "/api/recommendations",
            content=b"not-json",
            headers={"Content-Type": "application/json"},
        )
        assert res.status_code == 422

    def test_recommendation_whitespace_destination_returns_422(self, client: TestClient):
        res = client.post("/api/recommendations", json={
            "destination": "   ", "arrivalTime": "2026-10-25T14:30:00"
        })
        assert res.status_code == 422

    def test_rec_engine_unavailable_returns_503_not_fabricated_200(self, client: TestClient):
        """Recommendation engine missing → 503, never fabricated 200 list."""
        with patch.object(settings, "REC_ADAPTER_MODE", "module"):
            res = client.post("/api/recommendations", json={
                "destination": "Pune", "arrivalTime": "2026-10-25T14:30:00"
            })
        assert res.status_code == 503
        data = res.json()
        assert data["error"]["type"] == "integration_unavailable"
        assert not isinstance(data, list)

    def test_recommendations_empty_db_returns_empty_list(self, client: TestClient):
        empty_repo = InMemoryParkingRepository([])
        app.dependency_overrides[get_parking_repository] = lambda: empty_repo
        try:
            res = client.post("/api/recommendations", json={
                "destination": "Pune", "arrivalTime": "2026-10-25T14:30:00"
            })
            assert res.status_code == 200
            assert res.json() == []
        finally:
            _cleanup()


# ===========================================================================
# 9. Error Response Structure & No Leakage
# ===========================================================================

class TestErrorResponseStructure:
    def test_404_structure(self, client: TestClient):
        res = client.get("/api/parking/no-such-lot")
        assert res.status_code == 404
        err = res.json()["error"]
        assert set(err.keys()) >= {"type", "message", "status_code"}
        assert err["status_code"] == 404

    def test_409_structure(self, client: TestClient):
        res = client.post("/api/parking", json={
            "id": VALID_FIXTURE_ID, "name": "Dup",
            "totalCapacity": 100, "coordinates": [18.52, 73.85]
        })
        assert res.status_code == 409
        err = res.json()["error"]
        assert err["type"] == "duplicate_entity"
        assert err["status_code"] == 409

    def test_422_structure_has_details(self, client: TestClient):
        res = client.post("/api/parking", json={"id": "x"})
        assert res.status_code == 422
        err = res.json()["error"]
        assert err["type"] == "validation_error"
        assert "details" in err
        assert isinstance(err["details"], list)

    def test_503_structure_for_integration(self, client: TestClient):
        with patch.object(settings, "ML_ADAPTER_MODE", "module"):
            res = client.get(f"/api/predictions/{VALID_FIXTURE_ID}")
        assert res.status_code == 503
        err = res.json()["error"]
        assert err["type"] == "integration_unavailable"
        assert err["status_code"] == 503

    def test_no_traceback_in_404_response(self, client: TestClient):
        res = client.get("/api/parking/fake-id")
        text = res.text
        assert "Traceback" not in text
        assert 'File "' not in text

    def test_no_traceback_in_503_response(self, client: TestClient):
        with patch.object(settings, "ML_ADAPTER_MODE", "module"):
            res = client.get(f"/api/predictions/{VALID_FIXTURE_ID}")
        text = res.text
        assert "Traceback" not in text

    def test_no_pymongo_internals_in_404(self, client: TestClient):
        res = client.get("/api/parking/fake-id")
        text = res.text.lower()
        assert "pymongo" not in text
        assert "serverselectiontimeouterror" not in text


# ===========================================================================
# 10. Health Endpoint
# ===========================================================================

class TestHealthEndpoint:
    def test_health_db_online_returns_200(self, client: TestClient):
        with patch.object(mongodb_client, "check_health", return_value=True):
            res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["api"] == "online"
        assert data["database"]["status"] == "connected"
        assert data["database"]["type"] == "mongodb"
        assert data["database"]["ping"] is True
        assert "version" in data

    def test_health_db_offline_returns_503(self, client: TestClient):
        with patch.object(mongodb_client, "check_health", return_value=False):
            res = client.get("/api/health")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "degraded"
        assert data["database"]["status"] == "disconnected"
        assert data["api"] == "online"

    def test_health_api_always_online_even_when_db_down(self, client: TestClient):
        with patch.object(mongodb_client, "check_health", return_value=False):
            res = client.get("/api/health")
        assert res.json()["api"] == "online"


# ===========================================================================
# 11. Repository Unit Tests — Database Error Simulation
# ===========================================================================

class TestRepositoryDatabaseErrors:
    def test_mongo_repo_get_all_none_db_returns_empty(self):
        repo = MongoParkingRepository(db=None)
        assert repo.get_all() == []

    def test_mongo_repo_get_by_id_none_db_returns_none(self):
        repo = MongoParkingRepository(db=None)
        assert repo.get_by_id("any-id") is None

    def test_mongo_repo_create_none_db_raises(self):
        repo = MongoParkingRepository(db=None)
        facility = ParkingFacility(
            id="test-id", name="Test", totalCapacity=100,
            coordinates=[18.52, 73.85],
        )
        with pytest.raises(RuntimeError, match="not initialized"):
            repo.create(facility)

    def test_mongo_repo_upsert_none_db_returns_false(self):
        repo = MongoParkingRepository(db=None)
        assert repo.upsert({"id": "test", "name": "T", "totalCapacity": 100}) is False

    def test_inmemory_repo_returns_defensive_copies(self):
        """Mutating returned records must not affect the internal store."""
        repo = InMemoryParkingRepository([{
            "id": "lot-a", "name": "Lot A", "totalCapacity": 100,
            "coordinates": [18.52, 73.85], "isSimulated": True,
        }])
        results = repo.get_all()
        results[0]["name"] = "MUTATED"
        assert repo.get_by_id("lot-a")["name"] == "Lot A"

    def test_service_raises_entity_not_found_not_none(self):
        service = ParkingService(repository=InMemoryParkingRepository([]))
        with pytest.raises(EntityNotFoundError):
            service.get_by_id("ghost-id")


# ===========================================================================
# 12. MongoDB Client Lifecycle
# ===========================================================================

class TestMongoDBClientLifecycle:
    def test_check_health_false_when_client_none(self):
        client_obj = MongoDBClient()
        assert client_obj.check_health() is False

    def test_disconnect_safe_when_never_connected(self):
        client_obj = MongoDBClient()
        client_obj.disconnect()  # must not raise

    def test_properties_none_when_not_connected(self):
        client_obj = MongoDBClient()
        assert client_obj.db is None
        assert client_obj.client is None

    def test_connect_does_not_raise_when_mongo_unreachable(self):
        from app.core.config import Settings
        bad_settings = Settings(
            MONGODB_URI="mongodb://127.0.0.1:59997",
            MONGODB_SERVER_SELECTION_TIMEOUT_MS=100,
        )
        client_obj = MongoDBClient()
        with patch("app.db.mongodb.settings", bad_settings):
            try:
                client_obj.connect()
            except Exception as e:
                pytest.fail(f"connect() raised unexpectedly: {e}")


# ===========================================================================
# 13. Stable String IDs
# ===========================================================================

class TestStableStringIDs:
    def test_facility_id_is_string(self):
        f = ParkingFacility(id="stable-id-123", name="Test",
                            totalCapacity=50, coordinates=[18.52, 73.85])
        assert isinstance(f.id, str)

    def test_api_list_ids_are_strings(self, client: TestClient):
        res = client.get("/api/parking")
        assert res.status_code == 200
        for item in res.json():
            assert isinstance(item["id"], str)
            assert len(item["id"]) > 0

    def test_fixture_ids_use_fixture_prefix(self, client: TestClient):
        res = client.get("/api/parking")
        ids = [i["id"] for i in res.json()]
        assert any(fid.startswith("fixture-") for fid in ids)
