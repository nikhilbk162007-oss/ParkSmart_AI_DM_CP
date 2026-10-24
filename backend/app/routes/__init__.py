from app.api.routes.health import router as health_router
from app.api.routes.parking import router as parking_router
from app.api.routes.predictions import router as predictions_router
from app.api.routes.recommendations import router as recommendations_router

__all__ = ["health_router", "parking_router", "predictions_router", "recommendations_router"]
