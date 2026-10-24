import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.models.parking import ParkingFacility, CurrentOccupancyMeasured
from app.schemas.parking import ParkingCreate, ParkingUpdate
from app.repositories.parking_repository import InMemoryParkingRepository
from app.repositories.dependencies import get_parking_repository
from app.main import app


# -----------------------------------------------------------------------------
# 1. Unit Tests for Model Validation (Bounds, Invariants, Missing Fields)
# -----------------------------------------------------------------------------

def test_valid_parking_facility_model():
    """Valid record with correct capacity, coordinates, and metadata."""
    facility = ParkingFacility(
        id="lot-test-1",
        name="Central Mall Parking",
        totalCapacity=200,
        coordinates=[18.5204, 73.8567],
        isSimulated=False,
        coordinateSource="gps-sensor",
        dataSource="city-registry",
        address="FC Road, Pune",
        currentOccupancy=CurrentOccupancyMeasured(
            occupiedSpaces=150,
            freeSpaces=50
        )
    )
    assert facility.id == "lot-test-1"
    assert facility.total_capacity == 200
    assert facility.current_occupancy.occupancy_percentage == 75.0
    assert facility.is_simulated is False


def test_invalid_negative_capacity():
    """Negative totalCapacity must fail validation."""
    with pytest.raises(ValidationError) as exc_info:
        ParkingFacility(
            id="lot-negative-cap",
            name="Negative Capacity Lot",
            totalCapacity=-10,
            coordinates=[18.5204, 73.8567]
        )
    assert "totalCapacity" in str(exc_info.value) or "total_capacity" in str(exc_info.value)


def test_invalid_coordinates_out_of_range():
    """Latitude > 90 or Longitude > 180 must fail validation."""
    with pytest.raises(ValidationError) as exc_info_lat:
        ParkingFacility(
            id="lot-bad-lat",
            name="Bad Lat Lot",
            totalCapacity=100,
            coordinates=[95.0, 73.8567]  # lat > 90
        )
    assert "Latitude must be between -90.0 and 90.0" in str(exc_info_lat.value)

    with pytest.raises(ValidationError) as exc_info_lon:
        ParkingFacility(
            id="lot-bad-lon",
            name="Bad Lon Lot",
            totalCapacity=100,
            coordinates=[18.5204, 200.0]  # lon > 180
        )
    assert "Longitude must be between -180.0 and 180.0" in str(exc_info_lon.value)


def test_missing_required_fields():
    """Missing required name or id must fail validation."""
    with pytest.raises(ValidationError):
        ParkingFacility(
            id="lot-missing-name",
            # name is missing!
            totalCapacity=100,
            coordinates=[18.5204, 73.8567]
        )

    with pytest.raises(ValidationError):
        ParkingFacility(
            # id is missing!
            name="No ID Lot",
            totalCapacity=100,
            coordinates=[18.5204, 73.8567]
        )


def test_measured_occupancy_invariant_check():
    """Measured occupied + free must equal totalCapacity."""
    with pytest.raises(ValidationError) as exc_info:
        ParkingFacility(
            id="lot-inconsistent-occ",
            name="Inconsistent Lot",
            totalCapacity=100,
            coordinates=[18.5204, 73.8567],
            currentOccupancy=CurrentOccupancyMeasured(
                occupiedSpaces=80,
                freeSpaces=30  # 80 + 30 = 110 != 100
            )
        )
    assert "must equal totalCapacity" in str(exc_info.value)


# -----------------------------------------------------------------------------
# 2. Repository Layer Tests (CRUD, Duplicate IDs, Empty Results)
# -----------------------------------------------------------------------------

def test_repository_duplicate_id_handling():
    """Inserting duplicate ID must raise DuplicateEntityError."""
    repo = InMemoryParkingRepository([])
    facility = ParkingFacility(
        id="duplicate-id-1",
        name="Original Lot",
        totalCapacity=100,
        coordinates=[18.5204, 73.8567]
    )
    repo.create(facility)

    # Attempt second insertion with same ID
    from app.core.errors import DuplicateEntityError
    with pytest.raises(DuplicateEntityError) as exc_info:
        repo.create(facility)
    assert "already exists" in str(exc_info.value)


def test_repository_empty_results():
    """Empty repository returns empty list without errors."""
    empty_repo = InMemoryParkingRepository([])
    assert empty_repo.get_all() == []
    assert empty_repo.get_by_id("nonexistent") is None


# -----------------------------------------------------------------------------
# 3. HTTP Endpoints Tests (CRUD, Status Codes, Standardized Errors)
# -----------------------------------------------------------------------------

def test_api_create_duplicate_id_returns_409(client: TestClient):
    """POST /api/parking with existing ID returns standardized 409 Conflict."""
    payload = {
        "id": "fixture-riverfront",  # already exists in fixtures
        "name": "Duplicate Riverfront",
        "totalCapacity": 500,
        "coordinates": [18.5204, 73.8567]
    }
    response = client.post("/api/parking", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert "error" in data
    assert data["error"]["type"] == "duplicate_entity"


def test_api_create_and_delete_parking(client: TestClient):
    """POST and DELETE flow works cleanly."""
    payload = {
        "id": "new-test-garage",
        "name": "New Test Garage",
        "totalCapacity": 150,
        "coordinates": [18.5100, 73.8200],
        "isSimulated": True
    }
    # Create
    create_res = client.post("/api/parking", json=payload)
    assert create_res.status_code == 201
    assert create_res.json()["id"] == "new-test-garage"

    # Get
    get_res = client.get("/api/parking/new-test-garage")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "New Test Garage"

    # Delete
    del_res = client.delete("/api/parking/new-test-garage")
    assert del_res.status_code == 204

    # Verify not found
    after_res = client.get("/api/parking/new-test-garage")
    assert after_res.status_code == 404
