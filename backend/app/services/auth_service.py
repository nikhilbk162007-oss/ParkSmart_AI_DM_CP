from datetime import datetime, timedelta, timezone
import secrets
from typing import Any, Dict

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError

from app.core.errors import AppException
from app.repositories.auth_repository import AuthRepository

TOKEN_ISSUER = "parksmart-ai"
PASSWORD_HASHER = PasswordHasher()
DUMMY_PASSWORD_HASH = PASSWORD_HASHER.hash(secrets.token_urlsafe(32))


def public_user(user: Dict[str, Any]) -> Dict[str, str]:
    return {"username": user["username"], "role": user["role"]}


class AuthService:
    def __init__(
        self,
        repository: AuthRepository,
        signing_secret: str,
        token_ttl_minutes: int = 60,
    ):
        self._repository = repository
        self._signing_secret = signing_secret
        self._token_ttl_minutes = token_ttl_minutes

    @staticmethod
    def normalize_username(username: str) -> str:
        return username.strip().lower()

    def register_user(self, username: str, password: str) -> Dict[str, str]:
        normalized_username = self.normalize_username(username)
        user = self._repository.create({
            "username": normalized_username,
            "passwordHash": PASSWORD_HASHER.hash(password),
            "role": "user",
        })
        return public_user(user)

    def provision_admin(self, username: str, password: str) -> bool:
        normalized_username = self.normalize_username(username)
        existing = self._repository.get_by_username(normalized_username)
        if existing:
            if existing["role"] != "admin":
                raise AppException(
                    "The configured admin username already belongs to a regular user.",
                    status_code=409,
                    error_type="account_conflict",
                )
            return False
        self._repository.create({
            "username": normalized_username,
            "passwordHash": PASSWORD_HASHER.hash(password),
            "role": "admin",
        })
        return True

    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        self._ensure_signing_secret()
        normalized_username = self.normalize_username(username)
        user = self._repository.get_by_username(normalized_username)
        hash_to_check = user["passwordHash"] if user else DUMMY_PASSWORD_HASH
        try:
            password_matches = PASSWORD_HASHER.verify(hash_to_check, password)
        except (VerifyMismatchError, InvalidHash):
            password_matches = False
        if not user or not password_matches:
            raise AppException(
                "Invalid username or password.",
                status_code=401,
                error_type="invalid_credentials",
            )

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self._token_ttl_minutes)
        access_token = jwt.encode(
            {
                "sub": user["username"],
                "role": user["role"],
                "jti": secrets.token_urlsafe(24),
                "iss": TOKEN_ISSUER,
                "iat": now,
                "exp": expires_at,
            },
            self._signing_secret,
            algorithm="HS256",
        )
        return {
            "accessToken": access_token,
            "tokenType": "bearer",
            "expiresIn": self._token_ttl_minutes * 60,
            "user": public_user(user),
        }

    def get_authenticated_user(self, token: str) -> Dict[str, str]:
        claims = self._decode_token(token)
        user = self._repository.get_by_username(claims["sub"])
        if (
            not user
            or claims["role"] != user["role"]
            or self._repository.is_token_revoked(claims["jti"])
        ):
            raise AppException(
                "Authentication is required.",
                status_code=401,
                error_type="authentication_required",
            )
        return public_user(user)

    def revoke_token(self, token: str) -> None:
        claims = self._decode_token(token)
        user = self._repository.get_by_username(claims["sub"])
        if (
            not user
            or claims["role"] != user["role"]
            or self._repository.is_token_revoked(claims["jti"])
        ):
            raise AppException(
                "Authentication is required.",
                status_code=401,
                error_type="authentication_required",
            )
        expires_at = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
        self._repository.revoke_token(claims["jti"], expires_at)

    def _decode_token(self, token: str) -> Dict[str, Any]:
        self._ensure_signing_secret()
        try:
            return jwt.decode(
                token,
                self._signing_secret,
                algorithms=["HS256"],
                issuer=TOKEN_ISSUER,
                options={"require": ["exp", "iat", "iss", "jti", "sub", "role"]},
            )
        except jwt.InvalidTokenError as exc:
            raise AppException(
                "Authentication is required.",
                status_code=401,
                error_type="authentication_required",
            ) from exc

    def _ensure_signing_secret(self) -> None:
        if len(self._signing_secret.encode("utf-8")) < 32:
            raise AppException(
                "Authentication is not configured. Set AUTH_JWT_SECRET to a random value of at least 32 bytes.",
                status_code=503,
                error_type="authentication_unavailable",
            )
