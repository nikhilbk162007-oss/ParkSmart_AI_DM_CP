from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, Optional

from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.core.errors import DuplicateEntityError


class AuthRepository(ABC):
    @abstractmethod
    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def create(self, user: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def is_token_revoked(self, token_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def revoke_token(self, token_id: str, expires_at: datetime) -> None:
        raise NotImplementedError


class MongoAuthRepository(AuthRepository):
    def __init__(self, db: Database):
        self._collection = db.users
        self._revoked_tokens = db.revoked_tokens

    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        return self._collection.find_one({"username": username}, {"_id": 0})

    def create(self, user: Dict[str, Any]) -> Dict[str, Any]:
        document = deepcopy(user)
        document.setdefault("createdAt", datetime.now(timezone.utc))
        try:
            self._collection.insert_one(document)
        except DuplicateKeyError as exc:
            raise DuplicateEntityError("User", user["username"]) from exc
        return document

    def is_token_revoked(self, token_id: str) -> bool:
        return self._revoked_tokens.find_one({"jti": token_id}, {"_id": 1}) is not None

    def revoke_token(self, token_id: str, expires_at: datetime) -> None:
        self._revoked_tokens.update_one(
            {"jti": token_id},
            {"$setOnInsert": {"jti": token_id, "expiresAt": expires_at}},
            upsert=True,
        )


class InMemoryAuthRepository(AuthRepository):
    def __init__(self):
        self._users: Dict[str, Dict[str, Any]] = {}
        self._revoked_tokens: Dict[str, datetime] = {}
        self._lock = RLock()

    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            user = self._users.get(username)
            return deepcopy(user) if user is not None else None

    def create(self, user: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            username = user["username"]
            if username in self._users:
                raise DuplicateEntityError("User", username)
            document = deepcopy(user)
            document.setdefault("createdAt", datetime.now(timezone.utc))
            self._users[username] = document
            return deepcopy(document)

    def is_token_revoked(self, token_id: str) -> bool:
        with self._lock:
            return token_id in self._revoked_tokens

    def revoke_token(self, token_id: str, expires_at: datetime) -> None:
        with self._lock:
            self._revoked_tokens[token_id] = expires_at
