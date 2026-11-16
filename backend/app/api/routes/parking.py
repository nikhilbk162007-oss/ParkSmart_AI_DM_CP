from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from app.schemas.parking import (
    ParkingBaseResponse,
    ParkingCreate,
    ParkingUpdate,
    VehicleEventRequest,
)
from app.services.parking_service import ParkingService
from app.services.dependencies import get_parking_service
from app.core.errors import BadRequestError
from app.api.dependencies.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/parking", tags=["Parking"])


@router.get("", response_model=List[ParkingBaseResponse])
def list_parking_locations(
    is_simulated: Optional[bool] = Query(None, alias="isSimulated", description="Filter simulated vs verified real records"),
    min_capacity: Optional[int] = Query(None, ge=0, alias="minCapacity", description="Filter by minimum physical capacity"),
    limit: Optional[int] = Query(None, ge=1, le=200, description="Optional maximum number of records to return"),
    current_user: dict = Depends(get_current_user),
    parking_service: ParkingService = Depends(get_parking_service)
):
    """
    Retrieve all parking facilities conforming strictly to frontend format.
    Returns:
    - JSON array of parking records.
    - [] empty array when no records exist or match criteria (never fake fallback records).
    """
    records = parking_service.list_all(filter_simulated=is_simulated)
    
    if min_capacity is not None:
        records = [r for r in records if r.get("totalCapacity", 0) >= min_capacity]

    if limit is not None:
        records = records[:limit]

    return records


@router.get("/{parking_id}", response_model=ParkingBaseResponse)
def get_parking_location(
    parking_id: str,
    current_user: dict = Depends(get_current_user),
    parking_service: ParkingService = Depends(get_parking_service)
):
    """Retrieve a single parking facility by its unique ID. Returns 404 when missing."""
    return parking_service.get_by_id(parking_id)


@router.post("", response_model=ParkingBaseResponse, status_code=status.HTTP_201_CREATED)
def create_parking_location(
    payload: ParkingCreate,
    current_user: dict = Depends(require_admin),
    parking_service: ParkingService = Depends(get_parking_service)
):
    """Create a new parking facility. Rejects duplicate IDs with 409 Conflict."""
    return parking_service.create(payload)


@router.patch("/{parking_id}", response_model=ParkingBaseResponse)
def update_parking_location(
    parking_id: str,
    payload: ParkingUpdate,
    current_user: dict = Depends(require_admin),
    parking_service: ParkingService = Depends(get_parking_service)
):
    """Update parking facility fields."""
    return parking_service.update(parking_id, payload)


@router.delete("/{parking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_parking_location(
    parking_id: str,
    current_user: dict = Depends(require_admin),
    parking_service: ParkingService = Depends(get_parking_service)
):
    """Delete parking facility by ID. Returns 404 if not found."""
    parking_service.delete(parking_id)
    return None


@router.post("/{parking_id}/entry", response_model=ParkingBaseResponse)
def record_vehicle_entry(
    parking_id: str,
    payload: VehicleEventRequest,
    current_user: dict = Depends(require_admin),
    parking_service: ParkingService = Depends(get_parking_service),
):
    """Record one simulated vehicle entry and return updated occupancy."""
    return parking_service.vehicle_entry(parking_id, payload.vehicle_type)


@router.post("/{parking_id}/exit", response_model=ParkingBaseResponse)
def record_vehicle_exit(
    parking_id: str,
    payload: VehicleEventRequest,
    current_user: dict = Depends(require_admin),
    parking_service: ParkingService = Depends(get_parking_service),
):
    """Record one simulated vehicle exit and return updated occupancy."""
    return parking_service.vehicle_exit(parking_id, payload.vehicle_type)
