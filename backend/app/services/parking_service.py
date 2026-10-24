from typing import List, Optional, Dict, Any
from app.repositories.parking_repository import ParkingRepository
from app.models.parking import ParkingFacility
from app.schemas.parking import ParkingCreate, ParkingUpdate
from app.core.errors import EntityNotFoundError


class ParkingService:
    """Service layer managing parking facility business logic."""

    def __init__(self, repository: ParkingRepository):
        self.repository = repository

    def list_all(self, filter_simulated: Optional[bool] = None) -> List[Dict[str, Any]]:
        return self.repository.get_all(filter_simulated=filter_simulated)

    def get_by_id(self, parking_id: str) -> Dict[str, Any]:
        record = self.repository.get_by_id(parking_id)
        if not record:
            raise EntityNotFoundError("Parking facility", parking_id)
        return record

    def create(self, payload: ParkingCreate) -> Dict[str, Any]:
        # Use by_alias=True so aliased field names (e.g. totalCapacity) are passed;
        # ParkingFacility has populate_by_name=True, accepting both forms, but
        # aliases are the primary keys for cross-model consistency.
        facility = ParkingFacility(**payload.model_dump(by_alias=True))
        return self.repository.create(facility)

    def update(self, parking_id: str, payload: ParkingUpdate) -> Dict[str, Any]:
        updates = payload.model_dump(exclude_unset=True, by_alias=True)
        return self.repository.update(parking_id, updates)

    def delete(self, parking_id: str) -> bool:
        return self.repository.delete(parking_id)
