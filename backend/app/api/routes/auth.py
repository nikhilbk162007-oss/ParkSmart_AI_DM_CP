from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies.auth import get_current_user, oauth2_scheme
from app.core.errors import AppException
from app.repositories.auth_dependencies import get_auth_service
from app.schemas.auth import CredentialsRequest, LoginResponse, PublicUser, RegistrationRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=PublicUser, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegistrationRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    return auth_service.register_user(
        payload.username,
        payload.password.get_secret_value(),
    )


@router.post("/login", response_model=LoginResponse)
def login(
    payload: CredentialsRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    return auth_service.authenticate(
        payload.username,
        payload.password.get_secret_value(),
    )


@router.get("/me", response_model=PublicUser)
def current_user(current_user=Depends(get_current_user)):
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
):
    if token is None:
        raise AppException(
            "Authentication is required.",
            status_code=401,
            error_type="authentication_required",
        )
    auth_service.revoke_token(token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
