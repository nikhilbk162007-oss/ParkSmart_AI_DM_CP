from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import hashlib
import logging
import httpx
from app.integrations.ml_contract import MLPredictionRequest, MLPredictionResult
from app.core.errors import IntegrationUnavailableError, BadRequestError
from app.core.config import settings

logger = logging.getLogger("parksmart.adapters.ml")


class BaseMLAdapter(ABC):
    @abstractmethod
    async def predict_occupancy(
        self,
        parking_id: str,
        total_capacity: int,
        target_time: datetime,
        features: Optional[Dict[str, Any]] = None
    ) -> MLPredictionResult:
        """Estimate parking occupancy for a given location and target arrival time."""
        pass


class MockMLAdapter(BaseMLAdapter):
    """
    Deterministic simulated baseline model.
    Applies hour-of-day heuristic with lot-specific hash so predictions
    are realistic, time-sensitive, and reproducible.
    Explicitly labeled as 'simulated-baseline'.
    Never fabricates model accuracy metrics.
    """
    async def predict_occupancy(
        self,
        parking_id: str,
        total_capacity: int,
        target_time: datetime,
        features: Optional[Dict[str, Any]] = None
    ) -> MLPredictionResult:
        if total_capacity <= 0:
            return MLPredictionResult(
                predicted_occupied_spaces=0,
                predicted_free_spaces=0,
                occupancy_percentage=0.0,
                confidence_score=None,
                model_source="simulated-baseline",
                predicted_at=datetime.now(timezone.utc),
                target_time=target_time
            )

        # Baseline diurnal occupancy curve
        hour = target_time.hour
        if 9 <= hour <= 18:
            base_ratio = 0.65 + (0.15 * ((hour - 9) / 9.0))
        elif 19 <= hour <= 23:
            base_ratio = 0.50 - (0.25 * ((hour - 19) / 4.0))
        else:
            base_ratio = 0.20

        # Deterministic lot variance based on id hash
        hash_val = int(hashlib.md5(parking_id.encode()).hexdigest(), 16) % 20
        lot_variance = (hash_val - 10) / 100.0  # -0.10 to +0.09
        
        ratio = max(0.05, min(0.95, base_ratio + lot_variance))
        occupied = int(round(total_capacity * ratio))
        occupied = max(0, min(total_capacity, occupied))
        free = total_capacity - occupied
        percentage = round((occupied / total_capacity) * 100.0, 1)

        return MLPredictionResult(
            predicted_occupied_spaces=occupied,
            predicted_free_spaces=free,
            occupancy_percentage=percentage,
            confidence_score=None,  # No fabricated confidence metrics
            model_source="simulated-baseline",
            predicted_at=datetime.now(timezone.utc),
            target_time=target_time
        )


class ModuleMLAdapter(BaseMLAdapter):
    """
    Python import adapter for the scikit-learn module from ml-model/ (PRD 3).
    Inspects if ml_model package is present.
    If not installed or configured, raises IntegrationUnavailableError.
    Never fabricates predictions as actual model outputs.
    """
    async def predict_occupancy(
        self,
        parking_id: str,
        total_capacity: int,
        target_time: datetime,
        features: Optional[Dict[str, Any]] = None
    ) -> MLPredictionResult:
        try:
            # Inspection: try dynamic import without assuming existence
            import importlib
            ml_pkg = importlib.import_module("ml_model.predict")
            predict_fn = getattr(ml_pkg, "predict_occupancy")
        except (ImportError, ModuleNotFoundError, AttributeError) as e:
            raise IntegrationUnavailableError(
                "ML Model",
                f"Module 'ml_model.predict' is not installed or configured: {e}"
            )

        try:
            # Call agreed function signature
            raw_result = predict_fn(
                parking_data={"id": parking_id, "totalCapacity": total_capacity},
                target_time=target_time
            )
            # Validate output types and clamp within capacity bounds
            occupied = int(raw_result.get("predictedOccupiedSpaces", raw_result.get("occupied", 0)))
            if occupied < 0 or occupied > total_capacity:
                raise ValueError(f"Model output occupied ({occupied}) exceeds capacity bounds [0, {total_capacity}]")
            free = total_capacity - occupied
            percentage = round((occupied / total_capacity) * 100.0, 1) if total_capacity > 0 else 0.0

            return MLPredictionResult(
                predicted_occupied_spaces=occupied,
                predicted_free_spaces=free,
                occupancy_percentage=percentage,
                confidence_score=raw_result.get("confidenceScore"),
                model_source=raw_result.get("modelSource", "ml-model-random-forest"),
                predicted_at=datetime.now(timezone.utc),
                target_time=target_time
            )
        except Exception as e:
            raise IntegrationUnavailableError("ML Model", f"Prediction execution failed: {e}")


class HttpMLAdapter(BaseMLAdapter):
    """
    HTTP integration adapter if the ML module runs as an independent microservice.
    Handles network timeouts, HTTP errors, and malformed responses safely.
    """
    def __init__(self, service_url: Optional[str] = None, timeout: Optional[float] = None):
        self.service_url = (service_url or settings.ML_SERVICE_URL).rstrip("/")
        self.timeout = timeout or settings.ML_TIMEOUT_SECONDS

    async def predict_occupancy(
        self,
        parking_id: str,
        total_capacity: int,
        target_time: datetime,
        features: Optional[Dict[str, Any]] = None
    ) -> MLPredictionResult:
        url = f"{self.service_url}/predict"
        payload = {
            "parkingId": parking_id,
            "totalCapacity": total_capacity,
            "targetTime": target_time.isoformat(),
            "features": features or {}
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload)
                if res.status_code != 200:
                    raise IntegrationUnavailableError(
                        "ML Service",
                        f"HTTP {res.status_code}: {res.text}"
                    )
                data = res.json()
                
                occupied = int(data["predictedOccupiedSpaces"])
                if occupied < 0 or occupied > total_capacity:
                    raise ValueError(f"HTTP ML output occupied ({occupied}) out of capacity bounds [0, {total_capacity}]")
                free = total_capacity - occupied
                percentage = round((occupied / total_capacity) * 100.0, 1) if total_capacity > 0 else 0.0

                return MLPredictionResult(
                    predicted_occupied_spaces=occupied,
                    predicted_free_spaces=free,
                    occupancy_percentage=percentage,
                    confidence_score=data.get("confidenceScore"),
                    model_source=data.get("modelSource", "ml-http-service"),
                    predicted_at=datetime.now(timezone.utc),
                    target_time=target_time
                )
        except httpx.TimeoutException:
            raise IntegrationUnavailableError("ML Service", f"Request timed out after {self.timeout}s")
        except httpx.RequestError as e:
            raise IntegrationUnavailableError("ML Service", f"Failed to connect to ML service at {self.service_url}: {e}")
        except Exception as e:
            raise IntegrationUnavailableError("ML Service", f"Invalid response from ML service: {e}")


def get_ml_adapter(mode: Optional[str] = None) -> BaseMLAdapter:
    m = (mode or settings.ML_ADAPTER_MODE).lower()
    if m == "module":
        return ModuleMLAdapter()
    elif m == "http":
        return HttpMLAdapter()
    return MockMLAdapter()
