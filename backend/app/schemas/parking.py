from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator
from app.models.parking import (
    CurrentOccupancyMeasured,
    SUPPORTED_VEHICLE_TYPES,
    VehicleType,
)


class ParkingCreate(BaseModel):
    """Input validation model for creating new parking locations."""
    id: str = Field(..., min_length=1, description="Stable unique identifier for parking facility")
    name: str = Field(..., min_length=1, description="Facility display name")
    address: Optional[str] = Field(default=None, description="Street address or location note")
    total_capacity: int = Field(..., ge=0, alias="totalCapacity", description="Total physical parking capacity")
    coordinates: Optional[List[float]] = Field(None, min_length=2, max_length=2, description="[latitude, longitude]")
    coordinate_source: str = Field(default="simulated-development", alias="coordinateSource")
    data_source: str = Field(default="simulated-development", alias="dataSource")
    is_simulated: bool = Field(default=True, alias="isSimulated")
    accepted_vehicle_types: List[VehicleType] = Field(
        default_factory=lambda: list(SUPPORTED_VEHICLE_TYPES),
        min_length=1,
        alias="acceptedVehicleTypes",
    )
    current_occupancy: Optional[CurrentOccupancyMeasured] = Field(default=None, alias="currentOccupancy")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def validate_id_not_blank(cls, v: str) -> str:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("Parking facility id cannot be empty or whitespace")
        return v_stripped

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, v: str) -> str:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("Parking facility name cannot be empty or whitespace")
        return v_stripped

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is None:
            return None
        lat, lon = v[0], v[1]
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            raise ValueError("Coordinates must be valid [latitude between -90 and 90, longitude between -180 and 180]")
        return v

    @model_validator(mode="after")
    def validate_capacity_and_occupancy(self) -> "ParkingCreate":
        if len(self.accepted_vehicle_types) != len(set(self.accepted_vehicle_types)):
            raise ValueError("acceptedVehicleTypes cannot contain duplicates")
        if self.current_occupancy is not None:
            occ = self.current_occupancy
            if occ.occupied_spaces > self.total_capacity:
                raise ValueError(
                    f"Measured occupiedSpaces ({occ.occupied_spaces}) cannot exceed totalCapacity ({self.total_capacity})"
                )
            if occ.occupied_spaces + occ.free_spaces != self.total_capacity:
                raise ValueError(
                    f"Measured occupiedSpaces ({occ.occupied_spaces}) + freeSpaces ({occ.free_spaces}) "
                    f"must equal totalCapacity ({self.total_capacity})"
                )
            if set(occ.vehicle_counts) - set(self.accepted_vehicle_types):
                raise ValueError("Vehicle counts cannot include unaccepted vehicle types")
        return self

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class ParkingUpdate(BaseModel):
    """Input validation model for partial update of parking facility."""
    name: Optional[str] = None
    address: Optional[str] = None
    total_capacity: Optional[int] = Field(None, ge=0, alias="totalCapacity")
    coordinates: Optional[List[float]] = Field(None, min_length=2, max_length=2)
    coordinate_source: Optional[str] = Field(None, alias="coordinateSource")
    data_source: Optional[str] = Field(None, alias="dataSource")
    is_simulated: Optional[bool] = Field(None, alias="isSimulated")
    accepted_vehicle_types: Optional[List[VehicleType]] = Field(None, min_length=1, alias="acceptedVehicleTypes")
    current_occupancy: Optional[CurrentOccupancyMeasured] = Field(None, alias="currentOccupancy")
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is not None:
            lat, lon = v[0], v[1]
            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                raise ValueError("Coordinates must be valid [lat, lon]")
        return v

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> "ParkingUpdate":
        required_when_supplied = (
            "name",
            "total_capacity",
            "coordinate_source",
            "data_source",
            "is_simulated",
            "accepted_vehicle_types",
            "metadata",
            "current_occupancy",
        )
        for field_name in required_when_supplied:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        if self.name is not None and not self.name.strip():
            raise ValueError("Parking facility name cannot be empty or whitespace")
        if (
            self.accepted_vehicle_types is not None
            and len(self.accepted_vehicle_types) != len(set(self.accepted_vehicle_types))
        ):
            raise ValueError("acceptedVehicleTypes cannot contain duplicates")
        return self

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class ParkingBaseResponse(BaseModel):
    """
    Standard serialized response model consumed by Frontend components.
    Guarantees exact field names: id, name, totalCapacity, coordinates, coordinateSource, dataSource, isSimulated.
    """
    id: str = Field(..., description="Unique facility identifier")
    name: str = Field(..., description="Name of the parking location")
    total_capacity: int = Field(..., ge=0, alias="totalCapacity", description="Total physical capacity")
    coordinates: Optional[List[float]] = Field(default=None, min_length=2, max_length=2, description="[latitude, longitude]")
    coordinate_source: str = Field(default="database", alias="coordinateSource")
    data_source: str = Field(default="database", alias="dataSource")
    is_simulated: bool = Field(default=True, alias="isSimulated")
    accepted_vehicle_types: List[VehicleType] = Field(
        default_factory=lambda: list(SUPPORTED_VEHICLE_TYPES),
        alias="acceptedVehicleTypes",
    )
    address: Optional[str] = None
    current_occupancy: Optional[CurrentOccupancyMeasured] = Field(default=None, alias="currentOccupancy")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True
    )

    @computed_field(alias="availableSpaces")
    @property
    def available_spaces(self) -> int:
        occupied = self.current_occupancy.occupied_spaces if self.current_occupancy else 0
        return self.total_capacity - occupied


class VehicleEventRequest(BaseModel):
    vehicle_type: VehicleType = Field(..., alias="vehicleType")

    model_config = ConfigDict(populate_by_name=True)
