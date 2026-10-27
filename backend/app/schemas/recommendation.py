from datetime import datetime
from typing import List, Optional
# pyrefly: ignore[missing-import]
from pydantic import BaseModel, ConfigDict, Field, model_validator

class RecommendationRequest(BaseModel):
    destination: str = Field(..., min_length=1, description="Destination address or place")
    arrival_time: datetime = Field(..., alias="arrivalTime", description="Target arrival timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True
    )

class ParkingOption(BaseModel):
    id: str = Field(..., description="Unique facility identifier")
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
