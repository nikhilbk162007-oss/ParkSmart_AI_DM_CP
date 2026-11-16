from typing import List, Optional, Dict, Any
from app.repositories.parking_repository import ParkingRepository
from app.models.parking import ParkingFacility, VehicleType
from app.schemas.parking import ParkingCreate, ParkingUpdate
from app.core.errors import BadRequestError, EntityNotFoundError


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
        data = payload.model_dump(by_alias=True)
        if data.get("currentOccupancy") is None:
            data["currentOccupancy"] = {
                "occupiedSpaces": 0,
                "freeSpaces": data["totalCapacity"],
                "vehicleCounts": {
                    vehicle_type: 0
                    for vehicle_type in data["acceptedVehicleTypes"]
                },
            }
        facility = ParkingFacility(**data)
        return self.repository.create(facility)

    def update(self, parking_id: str, payload: ParkingUpdate) -> Dict[str, Any]:
        existing = self.repository.get_by_id(parking_id)
        if not existing:
            raise EntityNotFoundError("Parking facility", parking_id)
        updates = payload.model_dump(exclude_unset=True, by_alias=True)
        merged = {**existing, **updates}
        try:
            ParkingFacility(**merged)
        except ValueError as exc:
            raise BadRequestError(f"Parking update violates facility constraints: {exc}") from exc
        return self.repository.update(parking_id, updates)

    def delete(self, parking_id: str) -> bool:
        return self.repository.delete(parking_id)

    def vehicle_entry(self, parking_id: str, vehicle_type: VehicleType) -> Dict[str, Any]:
        self._get_facility_for_vehicle_event(parking_id, vehicle_type)
        record = self.repository.record_vehicle_entry(parking_id, vehicle_type)
        if record is not None:
            return record

        latest = self.get_by_id(parking_id)
        occupancy = latest.get("currentOccupancy") or {}
        if occupancy.get("occupiedSpaces", 0) >= latest.get("totalCapacity", 0):
            raise BadRequestError("Parking facility is full; vehicle entry was rejected.")
        if vehicle_type not in latest.get("acceptedVehicleTypes", []):
            raise BadRequestError(
                f"Parking facility does not accept vehicle type '{vehicle_type}'."
            )
        raise BadRequestError("Vehicle entry could not be recorded for this facility.")

    def vehicle_exit(self, parking_id: str, vehicle_type: VehicleType) -> Dict[str, Any]:
        self._get_facility_for_vehicle_event(parking_id, vehicle_type)
        record = self.repository.record_vehicle_exit(parking_id, vehicle_type)
        if record is not None:
            return record

        latest = self.get_by_id(parking_id)
        occupancy = latest.get("currentOccupancy") or {}
        counts = occupancy.get("vehicleCounts") or {}
        if vehicle_type not in latest.get("acceptedVehicleTypes", []):
            raise BadRequestError(
                f"Parking facility does not accept vehicle type '{vehicle_type}'."
            )
        if counts.get(vehicle_type, 0) <= 0:
            raise BadRequestError(
                f"No parked '{vehicle_type}' vehicle is available to exit."
            )
        raise BadRequestError("Vehicle exit could not be recorded for this facility.")

    def _get_facility_for_vehicle_event(
        self, parking_id: str, vehicle_type: VehicleType
    ) -> ParkingFacility:
        record = self.get_by_id(parking_id)
        facility = ParkingFacility(**record)
        if vehicle_type not in facility.accepted_vehicle_types:
            raise BadRequestError(
                f"Parking facility does not accept vehicle type '{vehicle_type}'."
            )
        if facility.current_occupancy is None:
            raise BadRequestError(
                "Vehicle events require initialized current occupancy and vehicle counts."
            )
        return facility
