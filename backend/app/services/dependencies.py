from fastapi import Depends
from app.repositories.parking_repository import ParkingRepository
from app.repositories.dependencies import get_parking_repository
from app.services.parking_service import ParkingService


def get_parking_service(
    repo: ParkingRepository = Depends(get_parking_repository)
) -> ParkingService:
    """Dependency provider for ParkingService."""
    return ParkingService(repository=repo)
