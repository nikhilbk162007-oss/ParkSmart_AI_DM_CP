from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


class RecommendationRequest(BaseModel):
    """
    Search criteria sent by Frontend search form:
    - destination: Required non-empty string.
    - arrivalTime: Required ISO-8601 timestamp.
    """
    destination: str = Field(..., min_length=1, description="Destination address or place")
    arrival_time: datetime = Field(..., alias="arrivalTime", description="Target arrival timestamp in ISO-8601 format")

    @field_validator("destination")
    @classmethod
    def validate_destination_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Destination cannot be empty or whitespace")
        return stripped

    @field_validator("arrival_time", mode="before")
    @classmethod
    def parse_and_validate_iso_timestamp(cls, v):
        if isinstance(v, str):
            # Parse ISO-8601 string
            try:
                # fromisoformat handles standard ISO 8601 (e.g. 2026-10-25T14:30:00 or with timezone)
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                return dt
            except Exception as e:
                raise ValueError(f"Invalid ISO-8601 timestamp format: '{v}'. Error: {e}")
        return v

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
