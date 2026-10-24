from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.recommendation import ParkingOption


class ParkingCandidateInput(BaseModel):
    """
    Candidate parking facility metadata passed to Recommendation Engine.
    Enriched with ML prediction if available.
    """
    id: str = Field(..., min_length=1)
    name: str = Field(...)
    total_capacity: int = Field(..., ge=0, alias="totalCapacity")
    coordinates: List[float] = Field(..., min_length=2, max_length=2)
    coordinate_source: str = Field(default="database", alias="coordinateSource")
    data_source: str = Field(default="database", alias="dataSource")
    is_simulated: bool = Field(default=True, alias="isSimulated")
    
    # ML predicted occupancy information
    predicted_occupied_spaces: Optional[int] = Field(None, ge=0, alias="predictedOccupiedSpaces")
    predicted_free_spaces: Optional[int] = Field(None, ge=0, alias="predictedFreeSpaces")
    occupancy_percentage: Optional[float] = Field(None, ge=0.0, le=100.0, alias="occupancyPercentage")
    
    # Optional pre-calculated distance if known
    distance_km: Optional[float] = Field(None, ge=0.0, alias="distanceKm")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class RecommendationEngineRequest(BaseModel):
    """
    Typed request payload sent to the Recommendation Engine.
    The recommendation engine (PRD 4) is responsible for shortest path calculation
    (Dijkstra's algorithm), candidate filtering, and multi-criteria ranking.
    """
    destination: str = Field(..., min_length=1, description="Destination name, query or address")
    arrival_time: datetime = Field(..., alias="arrivalTime", description="Target arrival timestamp")
    candidates: List[ParkingCandidateInput] = Field(..., description="Eligible parking facility candidates")
    constraints: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional constraints (e.g. max walking distance, accessibility)"
    )

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class RecommendationEngineResponse(BaseModel):
    """
    Typed response returned by Recommendation Engine.
    Ranking and scoring are strictly outputs of the recommendation engine.
    """
    ranked_options: List[ParkingOption] = Field(..., alias="rankedOptions")
    algorithm: str = Field(default="dijkstra-multi-criteria", description="Graph algorithm / ranking rule applied")
    engine_source: str = Field(default="unspecified", alias="engineSource")
    routing_metadata: Optional[Dict[str, Any]] = Field(default=None, alias="routingMetadata")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
