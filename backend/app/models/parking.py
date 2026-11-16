from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


VehicleType = Literal["car", "two-wheeler"]
SUPPORTED_VEHICLE_TYPES = ("car", "two-wheeler")


class CurrentOccupancyMeasured(BaseModel):
    """
    Simulated or measured occupancy, kept separate from ML predictions.
    """
    occupied_spaces: int = Field(..., ge=0, alias="occupiedSpaces")
    free_spaces: int = Field(..., ge=0, alias="freeSpaces")
    vehicle_counts: Dict[VehicleType, int] = Field(default_factory=dict, alias="vehicleCounts")
    occupancy_percentage: Optional[float] = Field(None, ge=0.0, le=100.0, alias="occupancyPercentage")
    measured_at: Optional[datetime] = Field(None, alias="measuredAt")

    @field_validator("vehicle_counts")
    @classmethod
    def validate_vehicle_counts(cls, counts: Dict[str, int]) -> Dict[str, int]:
        if any(type(count) is not int or count < 0 for count in counts.values()):
            raise ValueError("Vehicle counts must be non-negative integers")
        return counts

    @model_validator(mode="after")
    def compute_and_verify(self) -> "CurrentOccupancyMeasured":
        total = self.occupied_spaces + self.free_spaces
        if sum(self.vehicle_counts.values()) != self.occupied_spaces:
            raise ValueError("Vehicle counts must sum to occupiedSpaces")
        expected_percentage = round((self.occupied_spaces / total) * 100.0, 1) if total else 0.0
        if self.occupancy_percentage is None:
            self.occupancy_percentage = expected_percentage
        elif self.occupancy_percentage != expected_percentage:
            raise ValueError("occupancyPercentage must match occupiedSpaces and freeSpaces")
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
    
    # Campus fixtures do not invent geographic coordinates.
    coordinates: Optional[List[float]] = Field(default=None, min_length=2, max_length=2)
    coordinate_source: str = Field(default="simulated-development", alias="coordinateSource")
    
    # Data provenance and simulation flag.
    data_source: str = Field(default="simulated-development", alias="dataSource")
    is_simulated: bool = Field(default=True, alias="isSimulated", description="True for simulated records")
    accepted_vehicle_types: List[VehicleType] = Field(
        default_factory=lambda: list(SUPPORTED_VEHICLE_TYPES),
        min_length=1,
        alias="acceptedVehicleTypes",
    )
    
    # Current occupancy state, separate from calculated ML predictions.
    current_occupancy: Optional[CurrentOccupancyMeasured] = Field(
        default=None,
        alias="currentOccupancy",
        description="Current occupancy counts; campus simulation values are explicitly marked simulated."
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
    def validate_coordinates(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is None:
            return None
        lat, lon = v[0], v[1]
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"Latitude must be between -90.0 and 90.0, received {lat}")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"Longitude must be between -180.0 and 180.0, received {lon}")
        return v

    @field_validator("accepted_vehicle_types")
    @classmethod
    def validate_accepted_vehicle_types(cls, values: List[VehicleType]) -> List[VehicleType]:
        if len(values) != len(set(values)):
            raise ValueError("acceptedVehicleTypes cannot contain duplicates")
        return values

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
            unsupported_counts = set(occ.vehicle_counts) - set(self.accepted_vehicle_types)
            if unsupported_counts:
                raise ValueError(
                    "Vehicle counts include types not accepted by this facility: "
                    + ", ".join(sorted(unsupported_counts))
                )
        return self

    @property
    def available_spaces(self) -> int:
        occupied = self.current_occupancy.occupied_spaces if self.current_occupancy else 0
        return self.total_capacity - occupied

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
        extra="ignore"
    )
