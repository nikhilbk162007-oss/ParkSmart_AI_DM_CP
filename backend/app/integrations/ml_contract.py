from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


class MLPredictionRequest(BaseModel):
    """
    Typed request sent to ML model integration:
    - parking_id: Target facility identifier.
    - total_capacity: Physical capacity of parking location.
    - target_time: Arrival timestamp to forecast occupancy for.
    - features: Optional contextual features (e.g. day of week, hour, historical occupancy).
    """
    parking_id: str = Field(..., min_length=1, alias="parkingId", description="Target facility identifier")
    total_capacity: int = Field(..., ge=0, alias="totalCapacity", description="Total physical parking capacity")
    target_time: datetime = Field(..., alias="targetTime", description="Forecast target timestamp (ISO-8601)")
    features: Optional[Dict[str, Any]] = Field(default=None, description="Optional feature dictionary")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class MLPredictionResult(BaseModel):
    """
    Typed prediction response received from ML model:
    - predicted_occupied_spaces: Estimated occupied spaces within [0, total_capacity].
    - predicted_free_spaces: Estimated free spaces within [0, total_capacity].
    - occupancy_percentage: Percentage within [0.0, 100.0].
    - confidence_score: Confidence estimate [0.0, 1.0] if provided by model, else None.
    - model_source: Provenance string (e.g. 'random-forest-regressor-v1' or 'simulated-baseline').
    - predicted_at: Timestamp when prediction was computed.
    - target_time: Forecast target timestamp.
    """
    predicted_occupied_spaces: int = Field(..., ge=0, alias="predictedOccupiedSpaces")
    predicted_free_spaces: int = Field(..., ge=0, alias="predictedFreeSpaces")
    occupancy_percentage: float = Field(..., ge=0.0, le=100.0, alias="occupancyPercentage")
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, alias="confidenceScore")
    model_source: str = Field(default="unspecified", alias="modelSource")
    predicted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), alias="predictedAt")
    target_time: Optional[datetime] = Field(default=None, alias="targetTime")

    @model_validator(mode="after")
    def validate_invariants(self) -> "MLPredictionResult":
        # Invariant: occupied + free must equal the sum
        calc_total = self.predicted_occupied_spaces + self.predicted_free_spaces
        if calc_total > 0:
            calc_percentage = round((self.predicted_occupied_spaces / calc_total) * 100.0, 1)
            # Allow minor floating-point difference (up to 1.0%)
            if abs(calc_percentage - self.occupancy_percentage) > 1.5:
                # Recalculate if inconsistent
                self.occupancy_percentage = calc_percentage
        return self

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
