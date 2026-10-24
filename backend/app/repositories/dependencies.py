from app.db.mongodb import mongodb_client
from app.repositories.parking_repository import ParkingRepository, MongoParkingRepository


def get_parking_repository() -> ParkingRepository:
    """
    Default repository provider for FastAPI dependency injection.
    Uses MongoParkingRepository backed by PyMongo database instance.
    Tests can override this dependency with an InMemoryParkingRepository.
    """
    return MongoParkingRepository(db=mongodb_client.db)
