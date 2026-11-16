from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from copy import deepcopy
from threading import RLock
from pymongo import ReturnDocument
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError
import logging
from app.models.parking import ParkingFacility, VehicleType
from app.core.errors import DuplicateEntityError, EntityNotFoundError

logger = logging.getLogger("parksmart.repositories")

# Fictional campus simulation data; initial occupied vehicles are seeded as cars
# because no vehicle-type breakdown was supplied.
DEFAULT_PARKING_FIXTURES: List[Dict[str, Any]] = [
    {
        "id": "P1",
        "name": "North Parking",
        "totalCapacity": 50,
        "acceptedVehicleTypes": ["car", "two-wheeler"],
        "isSimulated": True,
        "dataSource": "simulated-campus-v1",
        "currentOccupancy": {
            "occupiedSpaces": 15,
            "freeSpaces": 35,
            "vehicleCounts": {"car": 15, "two-wheeler": 0},
            "occupancyPercentage": 30.0,
        },
        "createdAt": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        "updatedAt": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "P2",
        "name": "Library Parking",
        "totalCapacity": 30,
        "acceptedVehicleTypes": ["car"],
        "isSimulated": True,
        "dataSource": "simulated-campus-v1",
        "currentOccupancy": {
            "occupiedSpaces": 18,
            "freeSpaces": 12,
            "vehicleCounts": {"car": 18},
            "occupancyPercentage": 60.0,
        },
        "createdAt": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        "updatedAt": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "P3",
        "name": "South Parking",
        "totalCapacity": 40,
        "acceptedVehicleTypes": ["car", "two-wheeler"],
        "isSimulated": True,
        "dataSource": "simulated-campus-v1",
        "currentOccupancy": {
            "occupiedSpaces": 35,
            "freeSpaces": 5,
            "vehicleCounts": {"car": 35, "two-wheeler": 0},
            "occupancyPercentage": 87.5,
        },
        "createdAt": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        "updatedAt": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "P4",
        "name": "Sports Parking",
        "totalCapacity": 60,
        "acceptedVehicleTypes": ["car", "two-wheeler"],
        "isSimulated": True,
        "dataSource": "simulated-campus-v1",
        "currentOccupancy": {
            "occupiedSpaces": 20,
            "freeSpaces": 40,
            "vehicleCounts": {"car": 20, "two-wheeler": 0},
            "occupancyPercentage": 33.3,
        },
        "createdAt": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        "updatedAt": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    },
]

LEGACY_SIMULATED_FIXTURE_IDS = (
    "fixture-riverfront",
    "fixture-market",
    "fixture-garden",
)


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

    @abstractmethod
    def record_vehicle_entry(
        self, parking_id: str, vehicle_type: VehicleType
    ) -> Optional[Dict[str, Any]]:
        """Atomically add one vehicle if the facility has capacity."""
        pass

    @abstractmethod
    def record_vehicle_exit(
        self, parking_id: str, vehicle_type: VehicleType
    ) -> Optional[Dict[str, Any]]:
        """Atomically remove one parked vehicle of the specified type."""
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

    def _record_vehicle_event(
        self, parking_id: str, vehicle_type: VehicleType, entering: bool
    ) -> Optional[Dict[str, Any]]:
        if self.db is None:
            raise RuntimeError("Database connection is not initialized")

        vehicle_count_path = f"currentOccupancy.vehicleCounts.{vehicle_type}"
        delta = 1 if entering else -1
        query: Dict[str, Any] = {
            "id": parking_id,
            "acceptedVehicleTypes": vehicle_type,
        }
        if entering:
            query["$expr"] = {
                "$lt": [
                    "$currentOccupancy.occupiedSpaces",
                    "$totalCapacity",
                ]
            }
        else:
            query[vehicle_count_path] = {"$gt": 0}

        now = datetime.now(timezone.utc)
        occupied_after = {
            "$add": ["$currentOccupancy.occupiedSpaces", delta]
        }
        update_pipeline = [
            {
                "$set": {
                    "currentOccupancy.occupiedSpaces": occupied_after,
                    "currentOccupancy.freeSpaces": {
                        "$subtract": ["$currentOccupancy.freeSpaces", delta]
                    },
                    vehicle_count_path: {
                        "$add": [
                            {"$ifNull": [f"${vehicle_count_path}", 0]},
                            delta,
                        ]
                    },
                    "currentOccupancy.occupancyPercentage": {
                        "$cond": [
                            {"$gt": ["$totalCapacity", 0]},
                            {
                                "$round": [
                                    {
                                        "$multiply": [
                                            {
                                                "$divide": [
                                                    occupied_after,
                                                    "$totalCapacity",
                                                ]
                                            },
                                            100,
                                        ]
                                    },
                                    1,
                                ]
                            },
                            0.0,
                        ]
                    },
                    "updatedAt": now,
                }
            }
        ]
        return self.db.parking.find_one_and_update(
            query,
            update_pipeline,
            projection={"_id": 0},
            return_document=ReturnDocument.AFTER,
        )

    def record_vehicle_entry(
        self, parking_id: str, vehicle_type: VehicleType
    ) -> Optional[Dict[str, Any]]:
        return self._record_vehicle_event(parking_id, vehicle_type, entering=True)

    def record_vehicle_exit(
        self, parking_id: str, vehicle_type: VehicleType
    ) -> Optional[Dict[str, Any]]:
        return self._record_vehicle_event(parking_id, vehicle_type, entering=False)


class InMemoryParkingRepository(ParkingRepository):
    """
    Test and development fixture repository for dependency injection.
    Supports complete duplicate key and missing entity semantics.
    """

    def __init__(self, initial_data: Optional[List[Dict[str, Any]]] = None):
        data = initial_data if initial_data is not None else DEFAULT_PARKING_FIXTURES
        self._store: Dict[str, Dict[str, Any]] = {
            item["id"]: deepcopy(item) for item in data
        }
        self._lock = RLock()

    def get_all(self, filter_simulated: Optional[bool] = None) -> List[Dict[str, Any]]:
        with self._lock:
            results = [deepcopy(v) for v in self._store.values()]
            if filter_simulated is not None:
                results = [r for r in results if r.get("isSimulated", True) == filter_simulated]
            return results

    def get_by_id(self, parking_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            item = self._store.get(parking_id)
            return deepcopy(item) if item else None

    def create(self, facility: ParkingFacility) -> Dict[str, Any]:
        with self._lock:
            if facility.id in self._store:
                raise DuplicateEntityError("Parking facility", facility.id)
            doc = facility.model_dump(by_alias=True)
            self._store[facility.id] = deepcopy(doc)
            return deepcopy(doc)

    def update(self, parking_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            if parking_id not in self._store:
                raise EntityNotFoundError("Parking facility", parking_id)
            existing = deepcopy(self._store[parking_id])
            existing.update(deepcopy(updates))
            existing["updatedAt"] = datetime.now(timezone.utc)
            self._store[parking_id] = existing
            return deepcopy(existing)

    def delete(self, parking_id: str) -> bool:
        with self._lock:
            if parking_id not in self._store:
                raise EntityNotFoundError("Parking facility", parking_id)
            del self._store[parking_id]
            return True

    def upsert(self, parking_doc: Dict[str, Any]) -> bool:
        with self._lock:
            doc = deepcopy(parking_doc)
            doc["updatedAt"] = datetime.now(timezone.utc)
            self._store[doc["id"]] = doc
            return True

    def _record_vehicle_event(
        self, parking_id: str, vehicle_type: VehicleType, entering: bool
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            record = self._store.get(parking_id)
            if record is None:
                return None

            occupancy = record.get("currentOccupancy")
            if not isinstance(occupancy, dict):
                return None
            vehicle_counts = occupancy.setdefault("vehicleCounts", {})
            delta = 1 if entering else -1
            if entering:
                if occupancy["occupiedSpaces"] >= record["totalCapacity"]:
                    return None
            elif vehicle_counts.get(vehicle_type, 0) <= 0:
                return None

            occupancy["occupiedSpaces"] += delta
            occupancy["freeSpaces"] -= delta
            vehicle_counts[vehicle_type] = vehicle_counts.get(vehicle_type, 0) + delta
            capacity = record["totalCapacity"]
            occupancy["occupancyPercentage"] = (
                round(occupancy["occupiedSpaces"] / capacity * 100.0, 1)
                if capacity
                else 0.0
            )
            now = datetime.now(timezone.utc)
            record["updatedAt"] = now
            ParkingFacility(**record)
            return deepcopy(record)

    def record_vehicle_entry(
        self, parking_id: str, vehicle_type: VehicleType
    ) -> Optional[Dict[str, Any]]:
        return self._record_vehicle_event(parking_id, vehicle_type, entering=True)

    def record_vehicle_exit(
        self, parking_id: str, vehicle_type: VehicleType
    ) -> Optional[Dict[str, Any]]:
        return self._record_vehicle_event(parking_id, vehicle_type, entering=False)
