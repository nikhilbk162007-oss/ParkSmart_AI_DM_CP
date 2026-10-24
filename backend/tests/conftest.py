import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.repositories.dependencies import get_parking_repository
from app.repositories.parking_repository import InMemoryParkingRepository, DEFAULT_PARKING_FIXTURES


@pytest.fixture
def mock_parking_repo():
    """Create a fresh in-memory repository instance for testing."""
    return InMemoryParkingRepository(DEFAULT_PARKING_FIXTURES)


@pytest.fixture
def client(mock_parking_repo):
    """
    TestClient with dependency injection override so tests never require
    a real or live MongoDB server.
    """
    app.dependency_overrides[get_parking_repository] = lambda: mock_parking_repo
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
