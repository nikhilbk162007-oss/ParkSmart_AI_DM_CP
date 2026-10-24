from fastapi.testclient import TestClient
from app.repositories.dependencies import get_parking_repository
from app.repositories.parking_repository import InMemoryParkingRepository
from app.main import app


def test_list_parking_locations(client: TestClient):
    """Ensure parking locations are listed conforming to frontend contract."""
    response = client.get("/api/parking")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3

    first = data[0]
    assert "id" in first
    assert "name" in first
    assert "totalCapacity" in first
    assert "coordinates" in first
    assert len(first["coordinates"]) == 2


def test_list_parking_with_filters(client: TestClient):
    """Test optional documented filters on /api/parking."""
    # Filter by isSimulated=True
    res_sim = client.get("/api/parking?isSimulated=true")
    assert res_sim.status_code == 200
    assert len(res_sim.json()) >= 3

    # Filter by high minCapacity
    res_cap = client.get("/api/parking?minCapacity=500")
    assert res_cap.status_code == 200
    items = res_cap.json()
    assert all(item["totalCapacity"] >= 500 for item in items)

    # Filter with limit
    res_lim = client.get("/api/parking?limit=1")
    assert res_lim.status_code == 200
    assert len(res_lim.json()) == 1


def test_list_parking_empty_results_returns_empty_array(client: TestClient):
    """When no records match, endpoint returns [], never fake fallback records."""
    empty_repo = InMemoryParkingRepository([])
    app.dependency_overrides[get_parking_repository] = lambda: empty_repo
    try:
        response = client.get("/api/parking")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


def test_get_existing_parking(client: TestClient):
    """Ensure existing facility lookup returns full valid schema."""
    response = client.get("/api/parking/fixture-riverfront")
    assert response.status_code == 200
    item = response.json()
    assert item["id"] == "fixture-riverfront"
    assert item["name"] == "Riverfront Parking House"
    assert item["totalCapacity"] == 420
    assert item["coordinates"] == [18.5204, 73.8567]


def test_get_nonexistent_parking_returns_standard_error(client: TestClient):
    """Ensure non-existent ID returns standardized 404 JSON error."""
    response = client.get("/api/parking/nonexistent-lot-999")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["type"] == "not_found"
    assert "nonexistent-lot-999" in data["error"]["message"]
