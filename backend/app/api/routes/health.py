from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.db.mongodb import mongodb_client

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health")
def health_check():
    """
    Check the health of the API application and live database connectivity.
    Returns:
    - 200 OK when both API and MongoDB are healthy.
    - 503 Service Unavailable when database dependency is unreachable.
    """
    db_alive = mongodb_client.check_health()
    status_code = status.HTTP_200_OK if db_alive else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if db_alive else "degraded",
            "api": "online",
            "database": {
                "status": "connected" if db_alive else "disconnected",
                "type": "mongodb",
                "ping": db_alive
            },
            "version": "1.0.0"
        }
    )
