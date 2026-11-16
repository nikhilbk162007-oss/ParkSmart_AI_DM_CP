from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.repositories.auth_repository import InMemoryAuthRepository
from app.services.auth_service import AuthService


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_regular_registration_cannot_assign_admin_role(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "new-user",
            "password": "valid-registration-password",
            "role": "admin",
        },
    )
    assert response.status_code == 422

    response = client.post(
        "/api/auth/register",
        json={"username": "new-user", "password": "valid-registration-password"},
    )
    assert response.status_code == 201
    assert response.json() == {"username": "new-user", "role": "user"}


def test_admin_provisioning_is_idempotent_and_passwords_are_argon2id_hashed():
    repository = InMemoryAuthRepository()
    service = AuthService(repository, "test-secret-with-at-least-32-bytes")
    assert service.provision_admin("audit-admin", "first-secure-password")
    assert not service.provision_admin("AUDIT-ADMIN", "different-password")
    admin = repository.get_by_username("audit-admin")
    assert admin["role"] == "admin"
    assert admin["passwordHash"].startswith("$argon2id$")
    assert "password" not in admin

    public_user = service.register_user("audit-user", "another-secure-password")
    user = repository.get_by_username("audit-user")
    assert public_user == {"username": "audit-user", "role": "user"}
    assert user["passwordHash"].startswith("$argon2id$")
    assert "password" not in user


def test_login_issues_token_for_admin_and_user(client, auth_service):
    for username, password, expected_role in (
        ("campus-admin", "test-admin-password-2026", "admin"),
        ("campus-user", "test-user-password-2026", "user"),
    ):
        response = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["user"] == {"username": username, "role": expected_role}
        assert payload["tokenType"] == "bearer"
        assert payload["expiresIn"] == 3600
        assert "password" not in payload and "passwordHash" not in payload
        assert client.get("/api/auth/me", headers=_bearer(payload["accessToken"])).json() == payload["user"]


def test_invalid_credentials_are_rejected(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "campus-admin", "password": "incorrect-password"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["type"] == "invalid_credentials"


@pytest.mark.parametrize("secret", ["", "too-short"])
def test_missing_or_short_signing_secret_prevents_startup(monkeypatch, secret):
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", secret)
    with patch("app.db.mongodb.MongoDBClient.connect") as connect:
        with pytest.raises(RuntimeError, match="AUTH_JWT_SECRET"):
            with TestClient(app):
                pass
    connect.assert_not_called()


def test_logout_revokes_the_access_token(client, auth_service):
    token = auth_service.authenticate("campus-user", "test-user-password-2026")["accessToken"]
    headers = _bearer(token)

    response = client.post("/api/auth/logout", headers=headers)
    assert response.status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_expired_and_invalid_tokens_are_rejected(client):
    now = datetime.now(timezone.utc)
    expired_token = jwt.encode(
        {
            "sub": "campus-user",
            "role": "user",
            "jti": "expired-test-token",
            "iss": "parksmart-ai",
            "iat": now - timedelta(minutes=2),
            "exp": now - timedelta(minutes=1),
        },
        "test-secret-with-at-least-32-bytes",
        algorithm="HS256",
    )
    assert client.get("/api/auth/me", headers=_bearer(expired_token)).status_code == 401
    assert client.get("/api/auth/me", headers=_bearer("not-a-valid-token")).status_code == 401


def test_unauthenticated_parking_and_recommendation_requests_are_rejected(client):
    headers = {"Authorization": ""}
    assert client.get("/api/parking", headers=headers).status_code == 401
    assert client.post(
        "/api/recommendations",
        headers=headers,
        json={"destination": "Library", "entryGate": "gate_north", "vehicleType": "car"},
    ).status_code == 401
    assert client.post("/api/auth/logout", headers=headers).status_code == 401


def test_regular_user_can_read_but_cannot_simulate_or_manage_parking(client, auth_service):
    token = auth_service.authenticate("campus-user", "test-user-password-2026")["accessToken"]
    headers = _bearer(token)
    assert client.get("/api/parking", headers=headers).status_code == 200
    assert client.post(
        "/api/recommendations",
        headers=headers,
        json={"destination": "Library", "entryGate": "gate_north", "vehicleType": "car"},
    ).status_code == 200
    assert client.post(
        "/api/parking/P1/entry",
        headers=headers,
        json={"vehicleType": "car"},
    ).status_code == 403
    assert client.post(
        "/api/parking/P1/exit",
        headers=headers,
        json={"vehicleType": "car"},
    ).status_code == 403
    assert client.delete("/api/parking/P1", headers=headers).status_code == 403


def test_admin_can_simulate_vehicle_events(client):
    response = client.post("/api/parking/P1/entry", json={"vehicleType": "car"})
    assert response.status_code == 200
    assert response.json()["currentOccupancy"]["occupiedSpaces"] == 16
    response = client.post("/api/parking/P1/exit", json={"vehicleType": "car"})
    assert response.status_code == 200
    assert response.json()["currentOccupancy"]["occupiedSpaces"] == 15


def test_unauthenticated_vehicle_events_are_rejected(client):
    headers = {"Authorization": ""}
    assert client.post(
        "/api/parking/P1/entry",
        headers=headers,
        json={"vehicleType": "car"},
    ).status_code == 401
    assert client.post(
        "/api/parking/P1/exit",
        headers=headers,
        json={"vehicleType": "car"},
    ).status_code == 401
