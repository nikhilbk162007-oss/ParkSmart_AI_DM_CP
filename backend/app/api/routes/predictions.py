from datetime import datetime
from fastapi import APIRouter, Depends, Query
from app.schemas.prediction import PredictionResponse
from app.services.parking_service import ParkingService
from app.services.dependencies import get_parking_service
from app.adapters.ml_adapter import get_ml_adapter
from app.core.config import settings

router = APIRouter(prefix="/api/predictions", tags=["Predictions"])


@router.get("/{parking_id}", response_model=PredictionResponse)
async def get_prediction(
    parking_id: str,
    target_time: datetime = Query(
        default_factory=datetime.now,
        description="Target arrival timestamp in ISO-8601 format (e.g. 2026-10-25T14:30:00)"
    ),
    parking_service: ParkingService = Depends(get_parking_service)
):
    """
    Retrieve parking occupancy prediction for a given facility at target arrival time.
    Calls the configured ML integration adapter.
    If the ML module is not configured or unavailable, returns a structured 503 error
    (never inventing a prediction and presenting it as a real model output).
    """
    parking = parking_service.get_by_id(parking_id)
    capacity = parking.get("totalCapacity", 0)
    
    ml_adapter = get_ml_adapter(settings.ML_ADAPTER_MODE)
    prediction = await ml_adapter.predict_occupancy(
        parking_id=parking_id,
        total_capacity=capacity,
        target_time=target_time
    )

    return PredictionResponse(
        parkingId=parking_id,
        targetTime=target_time,
        totalCapacity=capacity,
        predictedOccupiedSpaces=prediction.predicted_occupied_spaces,
        predictedFreeSpaces=prediction.predicted_free_spaces,
        occupancyPercentage=prediction.occupancy_percentage,
        confidenceScore=prediction.confidence_score,
        modelSource=prediction.model_source
    )
