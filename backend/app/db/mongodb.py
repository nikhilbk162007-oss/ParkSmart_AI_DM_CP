import logging
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from app.core.config import settings

logger = logging.getLogger("parksmart.db")


class MongoDBClient:
    """
    Manages the PyMongo database client lifecycle and connectivity checks.
    Never fabricates connection status; strictly reports ping verification.
    """
    def __init__(self):
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None

    def connect(self) -> None:
        """Initialize the PyMongo client without raising on startup if offline."""
        try:
            self._client = MongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS
            )
            self._db = self._client[settings.MONGODB_DB_NAME]
            # Perform immediate ping to verify connectivity
            self._client.admin.command("ping")
            logger.info("Successfully connected to MongoDB at %s", settings.MONGODB_URI)
        except (PyMongoError, ServerSelectionTimeoutError, Exception) as e:
            logger.warning(
                "MongoDB is not currently reachable at %s (%s). API will report DB offline.",
                settings.MONGODB_URI,
                str(e)
            )

    def disconnect(self) -> None:
        """Cleanly close PyMongo client connections."""
        if self._client:
            try:
                self._client.close()
                logger.info("MongoDB connection closed cleanly.")
            except Exception as e:
                logger.error("Error closing MongoDB connection: %s", e)
            finally:
                self._client = None
                self._db = None

    def check_health(self) -> bool:
        """Run an actual ping command against the server. No fabrication."""
        if not self._client:
            return False
        try:
            self._client.admin.command("ping")
            return True
        except Exception:
            return False

    @property
    def db(self) -> Optional[Database]:
        return self._db

    @property
    def client(self) -> Optional[MongoClient]:
        return self._client


mongodb_client = MongoDBClient()


def get_mongo_db() -> Optional[Database]:
    """FastAPI Dependency for obtaining the MongoDB database instance."""
    return mongodb_client.db
