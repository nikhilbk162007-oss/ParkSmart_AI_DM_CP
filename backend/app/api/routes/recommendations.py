from typing import List
from fastapi import APIRouter, Depends
from app.schemas.recommendation import RecommendationRequest, ParkingOption
from app.services.parking_service import ParkingService
from app.services.dependencies import get_parking_service
from app.adapters.ml_adapter import get_ml_adapter
from app.adapters.recommendation_adapter import get_recommendation_adapter
from app.core.config import settings

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


@router.post("", response_model=List[ParkingOption])
async def get_recommendations(
    req: RecommendationRequest,
    parking_service: ParkingService = Depends(get_parking_service)
):
    """
    Generate ranked parking recommendations for given destination and arrival time.
    1. Validates destination and arrivalTime (ISO-8601).
    2. Retrieves candidate parking records from the database layer.
    3. Obtains occupancy predictions from the ML adapter.
    4. Delegates candidate ranking to the recommendation adapter (Discrete Math engine).
    5. Returns ranked list strictly conforming to Frontend parkingResultsProvider format.
    """
    parking_lots = parking_service.list_all()
    if not parking_lots:
        return []

    ml_adapter = get_ml_adapter(settings.ML_ADAPTER_MODE)
    rec_adapter = get_recommendation_adapter(settings.REC_ADAPTER_MODE)

    candidates = []
    for lot in parking_lots:
        lot_id = lot.get("id")
        cap = lot.get("totalCapacity", 0)
        
        # 1. Obtain prediction for this candidate from ML adapter
        pred = await ml_adapter.predict_occupancy(lot_id, cap, req.arrival_time)
        
        candidate = dict(lot)
        candidate["predictedOccupiedSpaces"] = pred.predicted_occupied_spaces
        candidate["predictedFreeSpaces"] = pred.predicted_free_spaces
        candidate["occupancyPercentage"] = pred.occupancy_percentage
        candidates.append(candidate)

    # 2. Delegate ranking to recommendation adapter (Dijkstra / multi-criteria scoring)
    ranked_options = await rec_adapter.rank_parking_options(
        destination=req.destination,
        target_time=req.arrival_time,
        candidates=candidates
    )

    return ranked_options
