from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError
import logging
from app.models.parking import ParkingFacility
from app.core.errors import DuplicateEntityError, EntityNotFoundError

logger = logging.getLogger("parksmart.repositories")

# Verified base fixtures strictly matching Frontend/src/data/parkingFixtures.js
# Explicitly marked as simulated and non-production
DEFAULT_PARKING_FIXTURES: List[Dict[str, Any]] = [
    {
        "id": "fixture-riverfront",
        "name": "Riverfront Parking House",
        "totalCapacity": 420,
        "coordinates": [18.5204, 73.8567],
        "coordinateSource": "simulated-development",
        "dataSource": "simulated-development",
        "isSimulated": True,
        "address": "Riverfront Road, Pune",
        "metadata": {"city": "Pune", "type": "Multi-level garage"},
        "createdAt": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        "updatedAt": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "fixture-market",
        "name": "Market Street Garage",
        "totalCapacity": 310,
        "coordinates": [18.5314, 73.8446],
        "coordinateSource": "simulated-development",
        "dataSource": "simulated-development",
        "isSimulated": True,
        "address": "Market Street, Shivajinagar, Pune",
        "metadata": {"city": "Pune", "type": "Surface lot"},
        "createdAt": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        "updatedAt": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "fixture-garden",
        "name": "Garden District Parking",
        "totalCapacity": 560,
        "coordinates": [18.5074, 73.8077],
        "coordinateSource": "simulated-development",
        "dataSource": "simulated-development",
        "isSimulated": True,
        "address": "Garden Road, Kothrud, Pune",
        "metadata": {"city": "Pune", "type": "Underground parking"},
        "createdAt": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        "updatedAt": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    }
]


class ParkingRepository(ABC):
    """Abstract interface for parking data access with full CRUD & query methods."""

    @abstractmethod
    def get_all(self, filter_simulated: Optional[bool] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_by_id(self, parking_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def create(self, facility: ParkingFacility) -> Dict[str, Any]:
        """Insert a new facility, raising DuplicateEntityError if ID exists."""
        pass

    @abstractmethod
    def update(self, parking_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing facility, raising EntityNotFoundError if missing."""
        pass

    @abstractmethod
    def delete(self, parking_id: str) -> bool:
        """Delete facility by ID, raising EntityNotFoundError if missing."""
        pass

    @abstractmethod
    def upsert(self, parking_doc: Dict[str, Any]) -> bool:
        """Upsert convenience for idempotency."""
        pass


class MongoParkingRepository(ParkingRepository):
    """Production MongoDB repository implementation using PyMongo."""

    def __init__(self, db: Optional[Database]):
        self.db = db

    def get_all(self, filter_simulated: Optional[bool] = None) -> List[Dict[str, Any]]:
        if self.db is None:
            return []
        query: Dict[str, Any] = {}
        if filter_simulated is not None:
            query["isSimulated"] = filter_simulated
        try:
            return list(self.db.parking.find(query, {"_id": 0}))
        except Exception as e:
            logger.error("Error fetching parking records from MongoDB: %s", e)
            return []

    def get_by_id(self, parking_id: str) -> Optional[Dict[str, Any]]:
        if self.db is None:
            return None
        try:
            return self.db.parking.find_one({"id": parking_id}, {"_id": 0})
        except Exception as e:
            logger.error("Error fetching parking record '%s' from MongoDB: %s", parking_id, e)
            return None

    def create(self, facility: ParkingFacility) -> Dict[str, Any]:
        if self.db is None:
            raise RuntimeError("Database connection is not initialized")
        doc = facility.model_dump(by_alias=True)
        try:
            self.db.parking.insert_one(doc)
            return self.get_by_id(facility.id)  # type: ignore[return-value]
        except DuplicateKeyError:
            raise DuplicateEntityError("Parking facility", facility.id)
        except Exception as e:
            logger.error("Error creating parking facility '%s': %s", facility.id, e)
            raise

    def update(self, parking_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        if self.db is None:
            raise RuntimeError("Database connection is not initialized")
        updates["updatedAt"] = datetime.now(timezone.utc)
        result = self.db.parking.update_one(
            {"id": parking_id},
            {"$set": updates}
        )
        if result.matched_count == 0:
            raise EntityNotFoundError("Parking facility", parking_id)
        return self.get_by_id(parking_id)  # type: ignore[return-value]

    def delete(self, parking_id: str) -> bool:
        if self.db is None:
            raise RuntimeError("Database connection is not initialized")
        result = self.db.parking.delete_one({"id": parking_id})
        if result.deleted_count == 0:
            raise EntityNotFoundError("Parking facility", parking_id)
        return True

    def upsert(self, parking_doc: Dict[str, Any]) -> bool:
        if self.db is None:
            return False
        try:
            doc = dict(parking_doc)
            doc["updatedAt"] = datetime.now(timezone.utc)
            self.db.parking.update_one(
                {"id": doc["id"]},
                {"$set": doc},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error("Error upserting parking doc in MongoDB: %s", e)
            return False


class InMemoryParkingRepository(ParkingRepository):
    """
    Test and development fixture repository for dependency injection.
    Supports complete duplicate key and missing entity semantics.
    """

    def __init__(self, initial_data: Optional[List[Dict[str, Any]]] = None):
        data = initial_data if initial_data is not None else DEFAULT_PARKING_FIXTURES
        self._store: Dict[str, Dict[str, Any]] = {
            item["id"]: dict(item) for item in data
        }

    def get_all(self, filter_simulated: Optional[bool] = None) -> List[Dict[str, Any]]:
        results = [dict(v) for v in self._store.values()]
        if filter_simulated is not None:
            results = [r for r in results if r.get("isSimulated", True) == filter_simulated]
        return results

    def get_by_id(self, parking_id: str) -> Optional[Dict[str, Any]]:
        item = self._store.get(parking_id)
        return dict(item) if item else None

    def create(self, facility: ParkingFacility) -> Dict[str, Any]:
        if facility.id in self._store:
            raise DuplicateEntityError("Parking facility", facility.id)
        doc = facility.model_dump(by_alias=True)
        self._store[facility.id] = dict(doc)
        return dict(doc)

    def update(self, parking_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        if parking_id not in self._store:
            raise EntityNotFoundError("Parking facility", parking_id)
        existing = dict(self._store[parking_id])
        existing.update(updates)
        existing["updatedAt"] = datetime.now(timezone.utc)
        self._store[parking_id] = existing
        return dict(existing)

    def delete(self, parking_id: str) -> bool:
        if parking_id not in self._store:
            raise EntityNotFoundError("Parking facility", parking_id)
        del self._store[parking_id]
        return True

    def upsert(self, parking_doc: Dict[str, Any]) -> bool:
        doc = dict(parking_doc)
        doc["updatedAt"] = datetime.now(timezone.utc)
        self._store[doc["id"]] = doc
        return True
