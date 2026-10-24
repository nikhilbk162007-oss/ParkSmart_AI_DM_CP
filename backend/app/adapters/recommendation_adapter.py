from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional
import math
import logging
import httpx
from app.schemas.recommendation import ParkingOption
from app.integrations.recommendation_contract import (
    RecommendationEngineRequest,
    RecommendationEngineResponse,
    ParkingCandidateInput
)
from app.core.errors import IntegrationUnavailableError
from app.core.config import settings

logger = logging.getLogger("parksmart.adapters.recommendation")


class BaseRecommendationAdapter(ABC):
    @abstractmethod
    async def rank_parking_options(
        self,
        destination: str,
        target_time: datetime,
        candidates: List[Dict[str, Any]]
    ) -> List[ParkingOption]:
        """Rank parking candidates and assign recommendation status and explanations."""
        pass


def haversine_distance(coord1: List[float], coord2: List[float]) -> float:
    """Calculate approximate great-circle distance in kilometers between two [lat, lon] points."""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    R = 6371.0  # Earth radius in km

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 1)


PUNE_DESTINATION_WAYPOINTS = {
    "riverfront": [18.5204, 73.8567],
    "market": [18.5314, 73.8446],
    "garden": [18.5074, 73.8077],
    "pune": [18.5204, 73.8567],
    "deccan": [18.5173, 73.8415],
    "shivajinagar": [18.5314, 73.8446],
    "kothrud": [18.5074, 73.8077]
}


class MockRecommendationAdapter(BaseRecommendationAdapter):
    """
    Mock baseline adapter applying multi-criteria scoring for demonstration.
    Conforms strictly to Frontend ParkingCard requirements without replacing the
    external Discrete Math recommendation engine.
    """
    async def rank_parking_options(
        self,
        destination: str,
        target_time: datetime,
        candidates: List[Dict[str, Any]]
    ) -> List[ParkingOption]:
        if not candidates:
            return []

        dest_lower = destination.lower()
        ref_coord = [18.5204, 73.8567]
        for key, coord in PUNE_DESTINATION_WAYPOINTS.items():
            if key in dest_lower:
                ref_coord = coord
                break

        options = []
        for cand in candidates:
            coords = cand.get("coordinates", [18.5204, 73.8567])
            dist = cand.get("distanceKm")
            if dist is None:
                dist = haversine_distance(coords, ref_coord)
                if dist == 0.0:
                    dist = 0.5

            cap = cand.get("totalCapacity", 100)
            occupied = cand.get("predictedOccupiedSpaces", 0)
            free = cand.get("predictedFreeSpaces", cap - occupied)

            options.append({
                "id": str(cand["id"]),
                "name": cand.get("name", f"Parking {cand['id']}"),
                "total_capacity": cap,
                "predicted_occupied_spaces": occupied,
                "predicted_free_spaces": free,
                "distance_km": float(dist),
                "coordinates": coords,
                "coordinate_source": cand.get("coordinateSource", "simulated-development"),
                "data_source": cand.get("dataSource", "simulated-development"),
            })

        # Baseline demo scoring
        def score_option(opt):
            cap = opt["total_capacity"] or 1
            avail_ratio = opt["predicted_free_spaces"] / cap
            dist_score = 1.0 / (opt["distance_km"] + 0.5)
            return (avail_ratio * 60) + (dist_score * 40)

        options.sort(key=score_option, reverse=True)

        results: List[ParkingOption] = []
        for i, opt in enumerate(options):
            if i == 0:
                status = "Recommended"
                explanation = f"Optimal balance: {opt['predicted_free_spaces']} spaces free and {opt['distance_km']} km away"
            elif i <= 2:
                status = "Alternative option"
                explanation = f"Secondary alternative with {opt['predicted_free_spaces']} estimated available spaces"
            else:
                status = "Alternative option"
                explanation = f"Located {opt['distance_km']} km from destination"

            results.append(ParkingOption(
                id=opt["id"],
                name=opt["name"],
                total_capacity=opt["total_capacity"],
                predicted_occupied_spaces=opt["predicted_occupied_spaces"],
                predicted_free_spaces=opt["predicted_free_spaces"],
                distance_km=opt["distance_km"],
                coordinates=opt["coordinates"],
                coordinate_source=opt["coordinate_source"],
                data_source=opt["data_source"],
                recommendation_status=status,
                recommendation_explanation=explanation
            ))

        return results


class ModuleRecommendationAdapter(BaseRecommendationAdapter):
    """
    Python import adapter for the Dijkstra recommendation module (PRD 4).
    Dynamically checks if recommendation_engine package is installed.
    If not installed or configured, raises IntegrationUnavailableError.
    Does not substitute its own ranking.
    """
    async def rank_parking_options(
        self,
        destination: str,
        target_time: datetime,
        candidates: List[Dict[str, Any]]
    ) -> List[ParkingOption]:
        try:
            import importlib
            rec_pkg = importlib.import_module("recommendation_engine.dijkstra")
            rank_fn = getattr(rec_pkg, "rank_parking_candidates")
        except (ImportError, ModuleNotFoundError, AttributeError) as e:
            raise IntegrationUnavailableError(
                "Recommendation Engine",
                f"Module 'recommendation_engine.dijkstra' is not installed or configured: {e}"
            )

        try:
            # Pass typed candidate data
            req = RecommendationEngineRequest(
                destination=destination,
                arrival_time=target_time,
                candidates=[ParkingCandidateInput(**c) for c in candidates]
            )
            raw_response = rank_fn(req.model_dump(by_alias=True))
            # Validate output is a list of options
            if isinstance(raw_response, dict) and "rankedOptions" in raw_response:
                return [ParkingOption(**item) for item in raw_response["rankedOptions"]]
            elif isinstance(raw_response, list):
                return [ParkingOption(**item) for item in raw_response]
            else:
                raise ValueError("Recommendation engine returned invalid structure.")
        except Exception as e:
            raise IntegrationUnavailableError("Recommendation Engine", f"Execution failed: {e}")


class HttpRecommendationAdapter(BaseRecommendationAdapter):
    """
    HTTP integration adapter if Recommendation Engine runs as a dedicated service.
    Handles network timeouts, HTTP errors, and malformed outputs safely.
    """
    def __init__(self, service_url: Optional[str] = None, timeout: Optional[float] = None):
        self.service_url = (service_url or settings.REC_SERVICE_URL).rstrip("/")
        self.timeout = timeout or settings.REC_TIMEOUT_SECONDS

    async def rank_parking_options(
        self,
        destination: str,
        target_time: datetime,
        candidates: List[Dict[str, Any]]
    ) -> List[ParkingOption]:
        url = f"{self.service_url}/recommend"
        payload = {
            "destination": destination,
            "arrivalTime": target_time.isoformat(),
            "candidates": candidates
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload)
                if res.status_code != 200:
                    raise IntegrationUnavailableError(
                        "Recommendation Engine",
                        f"HTTP {res.status_code}: {res.text}"
                    )
                data = res.json()
                items = data.get("rankedOptions", data) if isinstance(data, dict) else data
                if not isinstance(items, list):
                    raise ValueError("Recommendation service did not return a results list.")
                return [ParkingOption(**opt) for opt in items]
        except httpx.TimeoutException:
            raise IntegrationUnavailableError("Recommendation Engine", f"Request timed out after {self.timeout}s")
        except httpx.RequestError as e:
            raise IntegrationUnavailableError(
                "Recommendation Engine",
                f"Failed to connect to recommendation service at {self.service_url}: {e}"
            )
        except Exception as e:
            raise IntegrationUnavailableError("Recommendation Engine", f"Invalid response: {e}")


def get_recommendation_adapter(mode: Optional[str] = None) -> BaseRecommendationAdapter:
    m = (mode or settings.REC_ADAPTER_MODE).lower()
    if m == "module":
        return ModuleRecommendationAdapter()
    elif m == "http":
        return HttpRecommendationAdapter()
    return MockRecommendationAdapter()
