from fastapi import Depends
from pymongo.database import Database

from app.core.config import settings
from app.core.errors import DatabaseConnectionError
from app.db.mongodb import get_mongo_db
from app.repositories.auth_repository import AuthRepository, MongoAuthRepository
from app.services.auth_service import AuthService


def get_auth_repository(db: Database = Depends(get_mongo_db)) -> AuthRepository:
    if db is None:
        raise DatabaseConnectionError()
    return MongoAuthRepository(db)


def get_auth_service(
    repository: AuthRepository = Depends(get_auth_repository),
) -> AuthService:
    return AuthService(
        repository=repository,
        signing_secret=settings.AUTH_JWT_SECRET,
        token_ttl_minutes=settings.AUTH_TOKEN_TTL_MINUTES,
    )
