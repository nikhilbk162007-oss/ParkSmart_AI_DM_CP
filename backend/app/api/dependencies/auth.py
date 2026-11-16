from typing import Dict

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.errors import AppException
from app.repositories.auth_dependencies import get_auth_service
from app.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False,
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, str]:
    if token is None:
        raise AppException(
            "Authentication is required.",
            status_code=401,
            error_type="authentication_required",
        )
    return auth_service.get_authenticated_user(token)


def require_admin(
    current_user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, str]:
    if current_user["role"] != "admin":
        raise AppException(
            "Administrator access is required.",
            status_code=403,
            error_type="forbidden",
        )
    return current_user
