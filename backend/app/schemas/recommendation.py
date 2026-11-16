from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


class RecommendationRequest(BaseModel):
    """
    Campus recommendation criteria. arrivalTime remains optional for older clients;
    campus routes are static and do not depend on arrival time.
    """
    destination: str = Field(..., min_length=1, description="Destination address or place")
    arrival_time: Optional[datetime] = Field(
        default=None,
        alias="arrivalTime",
        description="Optional legacy field; campus routes are not time-dependent",
    )
    vehicle_type: Literal["car", "two-wheeler"] = Field(
        default="car", alias="vehicleType"
    )
    entry_gate: Literal["gate_north", "gate_south"] = Field(
        default="gate_north", alias="entryGate"
    )

    @field_validator("destination")
    @classmethod
    def validate_destination_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Destination cannot be empty or whitespace")
        allowed_destinations = {
            "library",
            "academic block",
            "canteen",
            "auditorium",
            "sports complex",
            "dest_library",
            "dest_academic_block",
            "dest_canteen",
            "dest_auditorium",
            "dest_sports_complex",
        }
        if stripped.casefold() not in allowed_destinations:
            raise ValueError("Destination must be a supported campus destination")
        return stripped

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True
    )


class ParkingOption(BaseModel):
    """
    Individual parking recommendation option conforming strictly to
    Frontend ParkingCard and validateApiResults contracts.
    """
    id: str = Field(..., min_length=1, description="Unique facility identifier")
    name: str = Field(..., description="Facility name")
    total_capacity: int = Field(..., ge=0, alias="totalCapacity")
    predicted_occupied_spaces: int = Field(..., ge=0, alias="predictedOccupiedSpaces")
    predicted_free_spaces: int = Field(..., ge=0, alias="predictedFreeSpaces")
    distance_km: float = Field(..., ge=0.0, alias="distanceKm")
    coordinates: List[float] = Field(..., min_length=2, max_length=2, description="[latitude, longitude]")
    coordinate_source: str = Field(default="simulated-development", alias="coordinateSource")
    data_source: str = Field(default="simulated-development", alias="dataSource")
    recommendation_status: Optional[str] = Field(default=None, alias="recommendationStatus")
    recommendation_explanation: Optional[str] = Field(default=None, alias="recommendationExplanation")

    @model_validator(mode="after")
    def validate_invariants(self) -> "ParkingOption":
        if self.predicted_occupied_spaces + self.predicted_free_spaces != self.total_capacity:
            raise ValueError(
                f"predictedOccupiedSpaces ({self.predicted_occupied_spaces}) + "
                f"predictedFreeSpaces ({self.predicted_free_spaces}) must equal "
                f"totalCapacity ({self.total_capacity})"
            )
        return self

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True
    )


class CampusRouteSegment(BaseModel):
    segment: Literal["entry-to-parking", "parking-to-destination"]
    distance_meters: int = Field(..., ge=0, alias="distanceMeters")
    path: List[str]

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class CampusParkingRecommendation(BaseModel):
    id: str = Field(..., min_length=1)
    name: str
    total_capacity: int = Field(..., ge=1, alias="totalCapacity")
    available_spaces: int = Field(..., ge=1, alias="availableSpaces")
    occupied_spaces: int = Field(..., ge=0, alias="occupiedSpaces")
    accepted_vehicle_types: List[Literal["car", "two-wheeler"]] = Field(
        ..., alias="acceptedVehicleTypes"
    )
    is_simulated: bool = Field(..., alias="isSimulated")
    data_source: str = Field(..., alias="dataSource")
    entry_gate: str = Field(..., alias="entryGate")
    destination: str
    route_distance_meters: int = Field(..., ge=0, alias="routeDistanceMeters")
    walking_distance_meters: int = Field(..., ge=0, alias="walkingDistanceMeters")
    total_distance_meters: int = Field(..., ge=0, alias="totalDistanceMeters")
    entry_route_path: List[str] = Field(..., alias="entryRoutePath")
    walking_route_path: List[str] = Field(..., alias="walkingRoutePath")
    route_path: List[str] = Field(..., alias="routePath")
    route_details: List[CampusRouteSegment] = Field(..., alias="routeDetails")
    score: float = Field(..., ge=0.0, le=1.0)
    recommendation_reason: str = Field(..., alias="recommendationReason")
    recommendation_status: Literal["Recommended", "Alternative option"] = Field(
        ..., alias="recommendationStatus"
    )

    @model_validator(mode="after")
    def validate_occupancy_and_route(self) -> "CampusParkingRecommendation":
        if self.available_spaces + self.occupied_spaces != self.total_capacity:
            raise ValueError("availableSpaces + occupiedSpaces must equal totalCapacity")
        if self.route_distance_meters + self.walking_distance_meters != self.total_distance_meters:
            raise ValueError("Route segment distances must sum to totalDistanceMeters")
        return self

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
