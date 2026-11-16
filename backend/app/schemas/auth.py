from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr

AuthRole = Literal["user", "admin"]


class CredentialsRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    password: SecretStr = Field(..., min_length=1, max_length=128)

    model_config = ConfigDict(extra="forbid")


class RegistrationRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    password: SecretStr = Field(..., min_length=12, max_length=128)

    model_config = ConfigDict(extra="forbid")


class PublicUser(BaseModel):
    username: str
    role: AuthRole


class LoginResponse(BaseModel):
    access_token: str = Field(..., alias="accessToken")
    token_type: Literal["bearer"] = Field(default="bearer", alias="tokenType")
    expires_in: int = Field(..., alias="expiresIn")
    user: PublicUser

    model_config = ConfigDict(populate_by_name=True)
