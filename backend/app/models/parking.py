from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CurrentOccupancyMeasured(BaseModel):
    """
    Measured / live sensor occupancy (ground truth from real sensors or lot counters).
    Explicitly separated from ML predictions.
    """
    occupied_spaces: int = Field(..., ge=0, alias="occupiedSpaces", description="Live measured occupied spaces")
    free_spaces: int = Field(..., ge=0, alias="freeSpaces", description="Live measured available free spaces")
    occupancy_percentage: Optional[float] = Field(None, ge=0.0, le=100.0, alias="occupancyPercentage")
    measured_at: Optional[datetime] = Field(None, alias="measuredAt", description="Timestamp of sensor measurement")

    @model_validator(mode="after")
    def compute_and_verify(self) -> "CurrentOccupancyMeasured":
        total = self.occupied_spaces + self.free_spaces
        if total > 0 and self.occupancy_percentage is None:
            self.occupancy_percentage = round((self.occupied_spaces / total) * 100.0, 1)
        return self

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class ParkingFacility(BaseModel):
    """
    Persistent parking location domain model and MongoDB schema representation.
    Designed for stability, strict bounds, explicit data provenance, and frontend compatibility.
    """
    id: str = Field(..., min_length=1, description="Stable unique identifier for parking facility")
    name: str = Field(..., min_length=1, description="Name of the parking location")
    address: Optional[str] = Field(default=None, description="Location description or street address")
    
    # Capacity bounds
    total_capacity: int = Field(..., ge=0, alias="totalCapacity", description="Total physical parking capacity")
    
    # Coordinates in [latitude, longitude]
    coordinates: List[float] = Field(..., min_length=2, max_length=2, description="[latitude, longitude]")
    coordinate_source: str = Field(default="simulated-development", alias="coordinateSource")
    
    # Data provenance and simulation flag (never claim simulated records are real)
    data_source: str = Field(default="simulated-development", alias="dataSource")
    is_simulated: bool = Field(default=True, alias="isSimulated", description="Explicit flag: True if synthetic/demo data")
    
    # Measured / live ground-truth occupancy (nullable when sensors not installed)
    # Strictly separated from calculated ML predictions!
    current_occupancy: Optional[CurrentOccupancyMeasured] = Field(
        default=None,
        alias="currentOccupancy",
        description="Current measured occupancy (if live sensors exist). Never stores ML predictions."
    )
    
    # Metadata & timestamps
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary facility attributes")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="createdAt"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="updatedAt"
    )

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
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"Latitude must be between -90.0 and 90.0, received {lat}")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"Longitude must be between -180.0 and 180.0, received {lon}")
        return v

    @model_validator(mode="after")
    def validate_capacity_and_occupancy(self) -> "ParkingFacility":
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

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
        extra="ignore"
    )
