from app.db.mongodb import mongodb_client
from app.repositories.parking_repository import ParkingRepository, MongoParkingRepository
from app.core.errors import DatabaseConnectionError


def get_parking_repository() -> ParkingRepository:
    """
    Default repository provider for FastAPI dependency injection.
    Uses MongoParkingRepository backed by PyMongo database instance.
    Tests can override this dependency with an InMemoryParkingRepository.
    """
    if mongodb_client.db is None:
        raise DatabaseConnectionError()
    return MongoParkingRepository(db=mongodb_client.db)
