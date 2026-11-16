import os

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

os.environ.setdefault("AUTH_JWT_SECRET", "test-secret-with-at-least-32-bytes")

from app.main import app
from app.repositories.dependencies import get_parking_repository
from app.repositories.parking_repository import InMemoryParkingRepository, DEFAULT_PARKING_FIXTURES
from app.repositories.auth_dependencies import get_auth_service
from app.repositories.auth_repository import InMemoryAuthRepository
from app.services.auth_service import AuthService


@pytest.fixture
def mock_parking_repo():
    """Create a fresh in-memory repository instance for testing."""
    return InMemoryParkingRepository(DEFAULT_PARKING_FIXTURES)


@pytest.fixture(scope="session")
def auth_service():
    repository = InMemoryAuthRepository()
    service = AuthService(repository, "test-secret-with-at-least-32-bytes", token_ttl_minutes=60)
    service.provision_admin("campus-admin", "test-admin-password-2026")
    service.register_user("campus-user", "test-user-password-2026")
    return service


@pytest.fixture(scope="session")
def admin_token(auth_service):
    return auth_service.authenticate(
        "campus-admin",
        "test-admin-password-2026",
    )["accessToken"]


@pytest.fixture
def client(mock_parking_repo, auth_service, admin_token):
    """
    TestClient with dependency injection override so tests never require
    a real or live MongoDB server.
    """
    app.dependency_overrides[get_parking_repository] = lambda: mock_parking_repo
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    with patch("app.db.mongodb.MongoDBClient.connect"):
        with TestClient(app) as test_client:
            test_client.headers.update({"Authorization": f"Bearer {admin_token}"})
            yield test_client
    app.dependency_overrides.clear()
