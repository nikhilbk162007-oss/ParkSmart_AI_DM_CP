from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class PredictionResponse(BaseModel):
    parking_id: str = Field(..., alias="parkingId")
    target_time: datetime = Field(..., alias="targetTime")
    total_capacity: int = Field(..., ge=0, alias="totalCapacity")
    predicted_occupied_spaces: int = Field(..., ge=0, alias="predictedOccupiedSpaces")
    predicted_free_spaces: int = Field(..., ge=0, alias="predictedFreeSpaces")
    occupancy_percentage: float = Field(..., ge=0.0, le=100.0, alias="occupancyPercentage")
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, alias="confidenceScore")
    model_source: str = Field(default="simulated-baseline", alias="modelSource")

    @model_validator(mode="after")
    def check_invariants(self) -> "PredictionResponse":
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
