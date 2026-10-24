from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.db.mongodb import mongodb_client
from app.api.routes import health, parking, predictions, recommendations


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect to MongoDB
    mongodb_client.connect()
    yield
    # Shutdown: clean up DB client connection
    mongodb_client.disconnect()


def create_app() -> FastAPI:
    """FastAPI Application factory configuring routes, middleware, and errors."""
    app = FastAPI(
        title="ParkSmart AI - Backend API",
        description="API and Data Layer connecting Frontend, ML Prediction Model, and Graph Recommendation Engine.",
        version="1.0.0",
        lifespan=lifespan
    )

    # Register standardized error handlers
    register_error_handlers(app)

    # CORS configuration to support React/Vite development server securely
    allowed_origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=["*"],
    )

    # Include API Routers
    app.include_router(health.router)
    app.include_router(parking.router)
    app.include_router(predictions.router)
    app.include_router(recommendations.router)

    @app.get("/", tags=["Root"])
    def root():
        return {
            "project": "ParkSmart AI",
            "role": "Backend & Database Service",
            "environment": settings.ENVIRONMENT,
            "docs": "/docs",
            "status": "online"
        }

    return app


app = create_app()
