from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.repositories.dependencies import get_parking_repository
from app.repositories.parking_repository import InMemoryParkingRepository


def _request(**overrides):
    return {
        "destination": "Library",
        "entryGate": "gate_north",
        "vehicleType": "car",
        **overrides,
    }


def test_get_campus_recommendations_returns_current_state_and_routes(client: TestClient):
    response = client.post("/api/recommendations", json=_request())
    assert response.status_code == 200
    results = response.json()

    assert results
    assert results[0]["recommendationStatus"] == "Recommended"
    assert results[0]["id"] == "P1"
    assert results[0]["availableSpaces"] == 35
    assert results[0]["occupiedSpaces"] == 15
    assert results[0]["totalCapacity"] == 50
    assert results[0]["routeDistanceMeters"] == 170
    assert results[0]["walkingDistanceMeters"] == 390
    assert results[0]["routePath"][0] == "gate_north"
    assert results[0]["routePath"][-1] == "dest_library"
    assert results[0]["recommendationReason"]
    assert results[0]["isSimulated"] is True
    assert all("predictedOccupiedSpaces" not in option for option in results)
    for option in results:
        assert option["availableSpaces"] + option["occupiedSpaces"] == option["totalCapacity"]
        assert option["routeDistanceMeters"] + option["walkingDistanceMeters"] == option["totalDistanceMeters"]


def test_both_entry_gates_are_accepted(client: TestClient):
    for gate in ("gate_north", "gate_south"):
        response = client.post(
            "/api/recommendations",
            json=_request(entryGate=gate, destination="Sports Complex"),
        )
        assert response.status_code == 200
        assert response.json()[0]["entryGate"] == gate


def test_all_supported_destinations_are_accepted(client: TestClient):
    for destination in (
        "Library",
        "Academic Block",
        "Canteen",
        "Auditorium",
        "Sports Complex",
    ):
        response = client.post(
            "/api/recommendations",
            json=_request(destination=destination),
        )
        assert response.status_code == 200
        assert response.json()


def test_recommendations_use_current_simulated_occupancy_after_events(client: TestClient):
    entry = client.post("/api/parking/P1/entry", json={"vehicleType": "car"})
    assert entry.status_code == 200
    response = client.post("/api/recommendations", json=_request())
    p1 = next(item for item in response.json() if item["id"] == "P1")
    assert p1["availableSpaces"] == 34
    assert p1["occupiedSpaces"] == 16


def test_full_facility_and_vehicle_incompatible_facility_are_excluded(client: TestClient):
    repository = InMemoryParkingRepository([
        {
            "id": "P1",
            "name": "North Parking",
            "totalCapacity": 1,
            "acceptedVehicleTypes": ["car", "two-wheeler"],
            "isSimulated": True,
            "dataSource": "simulated-campus-v1",
            "currentOccupancy": {
                "occupiedSpaces": 1,
                "freeSpaces": 0,
                "vehicleCounts": {"car": 1, "two-wheeler": 0},
            },
        },
        {
            "id": "P2",
            "name": "Library Parking",
            "totalCapacity": 30,
            "acceptedVehicleTypes": ["car"],
            "isSimulated": True,
            "dataSource": "simulated-campus-v1",
            "currentOccupancy": {
                "occupiedSpaces": 18,
                "freeSpaces": 12,
                "vehicleCounts": {"car": 18},
            },
        },
    ])
    app.dependency_overrides[get_parking_repository] = lambda: repository
    try:
        response = client.post(
            "/api/recommendations",
            json=_request(vehicleType="two-wheeler"),
        )
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


def test_no_eligible_facilities_returns_empty_array(client: TestClient):
    empty_repo = InMemoryParkingRepository([])
    app.dependency_overrides[get_parking_repository] = lambda: empty_repo
    try:
        response = client.post("/api/recommendations", json=_request())
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


def test_unknown_destination_and_gate_are_rejected(client: TestClient):
    destination_response = client.post(
        "/api/recommendations",
        json=_request(destination="Pune"),
    )
    gate_response = client.post(
        "/api/recommendations",
        json=_request(entryGate="west_gate"),
    )
    assert destination_response.status_code == 422
    assert gate_response.status_code == 422


def test_unsupported_vehicle_type_is_rejected(client: TestClient):
    response = client.post(
        "/api/recommendations",
        json=_request(vehicleType="bus"),
    )
    assert response.status_code == 422


def test_existing_request_shape_defaults_vehicle_and_gate(client: TestClient):
    response = client.post("/api/recommendations", json={"destination": "Library"})
    assert response.status_code == 200
    assert response.json()[0]["entryGate"] == "gate_north"


def test_module_mode_reports_missing_campus_engine(client: TestClient):
    with patch.dict(
        "sys.modules",
        {"recommendation_engine.campus_recommendation": None},
    ):
        with patch.object(settings, "REC_ADAPTER_MODE", "module"):
            response = client.post("/api/recommendations", json=_request())
    assert response.status_code == 503
    assert response.json()["error"]["type"] == "integration_unavailable"
