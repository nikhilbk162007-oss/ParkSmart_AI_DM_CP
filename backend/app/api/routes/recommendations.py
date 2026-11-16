from typing import List
from fastapi import APIRouter, Depends
from app.api.dependencies.auth import get_current_user
from app.schemas.recommendation import (
    CampusParkingRecommendation,
    RecommendationRequest,
)
from app.services.parking_service import ParkingService
from app.services.dependencies import get_parking_service
from app.adapters.recommendation_adapter import get_recommendation_adapter
from app.core.config import settings

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


@router.post("", response_model=List[CampusParkingRecommendation])
async def get_recommendations(
    req: RecommendationRequest,
    current_user: dict = Depends(get_current_user),
    parking_service: ParkingService = Depends(get_parking_service)
):
    """
    Recommend compatible campus parking from current simulated occupancy.
    The route deliberately does not call the ML predictor: occupancy comes from
    the parking repository's vehicle entry/exit state.
    """
    parking_lots = parking_service.list_all()
    if not parking_lots:
        return []

    rec_adapter = get_recommendation_adapter(settings.REC_ADAPTER_MODE)
    return await rec_adapter.rank_campus_parking_options(
        destination=req.destination,
        entry_gate=req.entry_gate,
        vehicle_type=req.vehicle_type,
        candidates=parking_lots,
    )
