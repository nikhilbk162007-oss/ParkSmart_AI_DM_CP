from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.models.parking import CurrentOccupancyMeasured


class ParkingCreate(BaseModel):
    """Input validation model for creating new parking locations."""
    id: str = Field(..., min_length=1, description="Stable unique identifier for parking facility")
    name: str = Field(..., min_length=1, description="Facility display name")
    address: Optional[str] = Field(default=None, description="Street address or location note")
    total_capacity: int = Field(..., ge=0, alias="totalCapacity", description="Total physical parking capacity")
    coordinates: List[float] = Field(..., min_length=2, max_length=2, description="[latitude, longitude]")
    coordinate_source: str = Field(default="simulated-development", alias="coordinateSource")
    data_source: str = Field(default="simulated-development", alias="dataSource")
    is_simulated: bool = Field(default=True, alias="isSimulated")
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
    def validate_coordinates(cls, v: List[float]) -> List[float]:
        lat, lon = v[0], v[1]
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            raise ValueError("Coordinates must be valid [latitude between -90 and 90, longitude between -180 and 180]")
        return v

    @model_validator(mode="after")
    def validate_capacity_and_occupancy(self) -> "ParkingCreate":
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

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class ParkingBaseResponse(BaseModel):
    """
    Standard serialized response model consumed by Frontend components.
    Guarantees exact field names: id, name, totalCapacity, coordinates, coordinateSource, dataSource, isSimulated.
    """
    id: str = Field(..., description="Unique facility identifier")
    name: str = Field(..., description="Name of the parking location")
    total_capacity: int = Field(..., ge=0, alias="totalCapacity", description="Total physical capacity")
    coordinates: List[float] = Field(..., min_length=2, max_length=2, description="[latitude, longitude]")
    coordinate_source: str = Field(default="database", alias="coordinateSource")
    data_source: str = Field(default="database", alias="dataSource")
    is_simulated: bool = Field(default=True, alias="isSimulated")
    address: Optional[str] = None
    current_occupancy: Optional[CurrentOccupancyMeasured] = Field(default=None, alias="currentOccupancy")
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True
    )
