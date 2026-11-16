from concurrent.futures import ThreadPoolExecutor

import pytest
from pymongo import ReturnDocument

from app.core.errors import BadRequestError
from app.repositories.parking_repository import (
    DEFAULT_PARKING_FIXTURES,
    InMemoryParkingRepository,
    MongoParkingRepository,
)
from app.services.parking_service import ParkingService


def _assert_occupancy_invariants(parking):
    occupancy = parking["currentOccupancy"]
    assert occupancy["occupiedSpaces"] >= 0
    assert occupancy["occupiedSpaces"] <= parking["totalCapacity"]
    assert parking["availableSpaces"] == (
        parking["totalCapacity"] - occupancy["occupiedSpaces"]
    )
    assert occupancy["occupiedSpaces"] == sum(occupancy["vehicleCounts"].values())


def test_initial_campus_facilities_are_explicitly_simulated(client):
    response = client.get("/api/parking")
    assert response.status_code == 200
    facilities = {
        item["id"]: item
        for item in response.json()
    }

    assert {
        parking_id: (
            facility["name"],
            facility["totalCapacity"],
            facility["currentOccupancy"]["occupiedSpaces"],
            facility["acceptedVehicleTypes"],
        )
        for parking_id, facility in facilities.items()
    } == {
        "P1": ("North Parking", 50, 15, ["car", "two-wheeler"]),
        "P2": ("Library Parking", 30, 18, ["car"]),
        "P3": ("South Parking", 40, 35, ["car", "two-wheeler"]),
        "P4": ("Sports Parking", 60, 20, ["car", "two-wheeler"]),
    }
    assert all(facility["isSimulated"] for facility in facilities.values())
    assert all(facility["dataSource"] == "simulated-campus-v1" for facility in facilities.values())


def test_successful_vehicle_entry_updates_only_matching_count(client):
    response = client.post("/api/parking/P1/entry", json={"vehicleType": "two-wheeler"})
    assert response.status_code == 200
    parking = response.json()
    assert parking["currentOccupancy"]["occupiedSpaces"] == 16
    assert parking["currentOccupancy"]["freeSpaces"] == 34
    assert parking["currentOccupancy"]["vehicleCounts"] == {
        "car": 15,
        "two-wheeler": 1,
    }
    assert parking["availableSpaces"] == 34
    _assert_occupancy_invariants(parking)


def test_successful_vehicle_exit_updates_only_matching_count(client):
    response = client.post("/api/parking/P1/exit", json={"vehicleType": "car"})
    assert response.status_code == 200
    parking = response.json()
    assert parking["currentOccupancy"]["occupiedSpaces"] == 14
    assert parking["currentOccupancy"]["freeSpaces"] == 36
    assert parking["currentOccupancy"]["vehicleCounts"] == {
        "car": 14,
        "two-wheeler": 0,
    }
    _assert_occupancy_invariants(parking)


def test_entry_is_rejected_when_facility_is_full(client):
    for _ in range(12):
        response = client.post("/api/parking/P2/entry", json={"vehicleType": "car"})
        assert response.status_code == 200

    response = client.post("/api/parking/P2/entry", json={"vehicleType": "car"})
    assert response.status_code == 400
    assert "full" in response.json()["error"]["message"].lower()
    parking = client.get("/api/parking/P2").json()
    assert parking["currentOccupancy"]["occupiedSpaces"] == 30
    assert parking["availableSpaces"] == 0
    _assert_occupancy_invariants(parking)


def test_exit_is_rejected_when_no_matching_vehicle_is_parked(client):
    response = client.post("/api/parking/P1/exit", json={"vehicleType": "two-wheeler"})
    assert response.status_code == 400
    assert "no parked" in response.json()["error"]["message"].lower()
    assert client.get("/api/parking/P1").json()["currentOccupancy"]["occupiedSpaces"] == 15


def test_vehicle_type_not_accepted_by_facility_is_rejected(client):
    response = client.post("/api/parking/P2/entry", json={"vehicleType": "two-wheeler"})
    assert response.status_code == 400
    assert "does not accept" in response.json()["error"]["message"].lower()


@pytest.mark.parametrize("event", ["entry", "exit"])
def test_unsupported_vehicle_type_is_rejected(client, event):
    response = client.post(
        f"/api/parking/P1/{event}",
        json={"vehicleType": "bus"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("event", ["entry", "exit"])
def test_unknown_facility_is_rejected(client, event):
    response = client.post(
        f"/api/parking/unknown/{event}",
        json={"vehicleType": "car"},
    )
    assert response.status_code == 404


def test_vehicle_counts_cannot_become_negative_or_exceed_capacity():
    repository = InMemoryParkingRepository(DEFAULT_PARKING_FIXTURES)
    service = ParkingService(repository)

    for _ in range(15):
        with pytest.raises(BadRequestError):
            service.vehicle_exit("P1", "two-wheeler")
    for _ in range(35):
        service.vehicle_entry("P1", "car")
    with pytest.raises(BadRequestError):
        service.vehicle_entry("P1", "car")
    for _ in range(50):
        service.vehicle_exit("P1", "car")
    with pytest.raises(BadRequestError):
        service.vehicle_exit("P1", "car")

    parking = repository.get_by_id("P1")
    assert parking["currentOccupancy"]["occupiedSpaces"] == 0
    assert parking["currentOccupancy"]["vehicleCounts"] == {
        "car": 0,
        "two-wheeler": 0,
    }
    assert parking["currentOccupancy"]["freeSpaces"] == 50
    _assert_occupancy_invariants({
        **parking,
        "availableSpaces": 50,
    })


def test_concurrent_entries_never_exceed_capacity():
    repository = InMemoryParkingRepository(DEFAULT_PARKING_FIXTURES)
    service = ParkingService(repository)

    def enter_vehicle(_):
        try:
            service.vehicle_entry("P1", "car")
            return True
        except BadRequestError:
            return False

    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(executor.map(enter_vehicle, range(100)))

    parking = repository.get_by_id("P1")
    assert sum(results) == 35
    assert parking["currentOccupancy"]["occupiedSpaces"] == 50
    assert parking["currentOccupancy"]["vehicleCounts"]["car"] == 50
    assert parking["currentOccupancy"]["freeSpaces"] == 0
    _assert_occupancy_invariants({**parking, "availableSpaces": 0})


@pytest.mark.parametrize(
    ("method_name", "vehicle_type", "expected_delta"),
    [
        ("record_vehicle_entry", "car", 1),
        ("record_vehicle_exit", "two-wheeler", -1),
    ],
)
def test_mongo_vehicle_events_use_atomic_conditional_updates(
    method_name, vehicle_type, expected_delta
):
    class FakeParkingCollection:
        def find_one_and_update(self, query, update, **kwargs):
            self.query = query
            self.update = update
            self.kwargs = kwargs
            return {"id": "P1"}

    class FakeDatabase:
        def __init__(self):
            self.parking = FakeParkingCollection()

    database = FakeDatabase()
    repository = MongoParkingRepository(database)
    result = getattr(repository, method_name)("P1", vehicle_type)

    assert result == {"id": "P1"}
    assert database.parking.query["id"] == "P1"
    assert database.parking.query["acceptedVehicleTypes"] == vehicle_type
    update_fields = database.parking.update[0]["$set"]
    assert update_fields["currentOccupancy.occupiedSpaces"] == {
        "$add": ["$currentOccupancy.occupiedSpaces", expected_delta]
    }
    assert database.parking.kwargs["return_document"] == ReturnDocument.AFTER
    if expected_delta == 1:
        assert database.parking.query["$expr"] == {
            "$lt": ["$currentOccupancy.occupiedSpaces", "$totalCapacity"]
        }
    else:
        assert database.parking.query[
            "currentOccupancy.vehicleCounts.two-wheeler"
        ] == {"$gt": 0}
