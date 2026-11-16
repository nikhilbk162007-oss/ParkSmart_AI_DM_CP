import os
import re
import sys

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.core.config import settings
from app.db.indexes import ensure_parking_indexes
from app.repositories.auth_repository import MongoAuthRepository
from app.services.auth_service import AuthService


def main() -> None:
    username = os.environ.get("INITIAL_ADMIN_USERNAME", "").strip()
    password = os.environ.get("INITIAL_ADMIN_PASSWORD", "")
    if not re.fullmatch(r"[A-Za-z0-9._-]{3,64}", username) or not 12 <= len(password) <= 128:
        raise SystemExit(
            "Set a valid INITIAL_ADMIN_USERNAME and an INITIAL_ADMIN_PASSWORD between 12 and 128 characters."
        )
    if not settings.AUTH_JWT_SECRET or len(settings.AUTH_JWT_SECRET.encode("utf-8")) < 32:
        raise SystemExit("Set AUTH_JWT_SECRET to a random value of at least 32 bytes before running.")
    client = MongoClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
    )
    try:
        client.admin.command("ping")
        db = client[settings.MONGODB_DB_NAME]
        ensure_parking_indexes(db)
        service = AuthService(
            MongoAuthRepository(db),
            settings.AUTH_JWT_SECRET,
            settings.AUTH_TOKEN_TTL_MINUTES,
        )
        created = service.provision_admin(username, password)
        print("Initial administrator account created." if created else "Administrator account already exists; unchanged.")
    except PyMongoError:
        print("Administrator provisioning failed; verify MongoDB connectivity and configuration.", file=sys.stderr)
        raise SystemExit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
