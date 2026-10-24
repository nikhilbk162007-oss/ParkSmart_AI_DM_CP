import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from app.adapters.ml_adapter import (
    MockMLAdapter,
    ModuleMLAdapter,
    HttpMLAdapter,
    get_ml_adapter
)
from app.adapters.recommendation_adapter import (
    MockRecommendationAdapter,
    ModuleRecommendationAdapter,
    HttpRecommendationAdapter,
    get_recommendation_adapter
)
from app.core.errors import IntegrationUnavailableError
from app.integrations.ml_contract import MLPredictionResult
from app.schemas.recommendation import ParkingOption


# -----------------------------------------------------------------------------
# 1. ML Adapter Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_ml_adapter_capacity_boundary_zero():
    """When capacity is 0, adapter returns 0 occupied/free and 0% occupancy."""
    adapter = MockMLAdapter()
    res = await adapter.predict_occupancy(
        parking_id="zero-cap-lot",
        total_capacity=0,
        target_time=datetime(2026, 10, 25, 14, 0, tzinfo=timezone.utc)
    )
    assert res.predicted_occupied_spaces == 0
    assert res.predicted_free_spaces == 0
    assert res.occupancy_percentage == 0.0
    assert res.model_source == "simulated-baseline"


@pytest.mark.asyncio
async def test_mock_ml_adapter_bounds_and_invariants():
    """Verify that predictions never exceed physical capacity."""
    adapter = MockMLAdapter()
    for cap in [1, 50, 100, 500]:
        res = await adapter.predict_occupancy(
            parking_id="test-lot",
            total_capacity=cap,
            target_time=datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
        )
        assert 0 <= res.predicted_occupied_spaces <= cap
        assert 0 <= res.predicted_free_spaces <= cap
        assert res.predicted_occupied_spaces + res.predicted_free_spaces == cap


@pytest.mark.asyncio
async def test_module_ml_adapter_when_unconfigured_raises_integration_error():
    """Uninstalled or unconfigured Python module raises IntegrationUnavailableError."""
    adapter = ModuleMLAdapter()
    with pytest.raises(IntegrationUnavailableError) as exc_info:
        await adapter.predict_occupancy("lot-1", 100, datetime.now(timezone.utc))
    assert "ML Model" in str(exc_info.value)
    assert "not installed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_http_ml_adapter_connection_failure():
    """HTTP adapter with unreachable host raises IntegrationUnavailableError."""
    adapter = HttpMLAdapter(service_url="http://127.0.0.1:59999", timeout=0.2)
    with pytest.raises(IntegrationUnavailableError) as exc_info:
        await adapter.predict_occupancy("lot-1", 100, datetime.now(timezone.utc))
    assert "Failed to connect" in str(exc_info.value) or "timed out" in str(exc_info.value)


@pytest.mark.asyncio
async def test_http_ml_adapter_capacity_boundary_violation():
    """If remote HTTP service returns count > totalCapacity, raises IntegrationUnavailableError."""
    adapter = HttpMLAdapter(service_url="http://mock-ml-service", timeout=1.0)
    
    class FakeResponse:
        status_code = 200
        def json(self):
            return {
                "predictedOccupiedSpaces": 150,  # exceeds capacity 100!
                "predictedFreeSpaces": 0
            }
        @property
        def text(self):
            return "ok"

    with patch("httpx.AsyncClient.post", return_value=FakeResponse()):
        with pytest.raises(IntegrationUnavailableError) as exc_info:
            await adapter.predict_occupancy("lot-1", 100, datetime.now(timezone.utc))
        assert "out of capacity bounds" in str(exc_info.value) or "Invalid response" in str(exc_info.value)


# -----------------------------------------------------------------------------
# 2. Recommendation Adapter Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_recommendation_adapter_empty_candidates():
    """Empty candidate list safely returns empty list."""
    adapter = MockRecommendationAdapter()
    results = await adapter.rank_parking_options(
        destination="Pune",
        target_time=datetime.now(timezone.utc),
        candidates=[]
    )
    assert results == []


@pytest.mark.asyncio
async def test_module_recommendation_adapter_unconfigured_raises_error():
    """Uninstalled recommendation module raises IntegrationUnavailableError."""
    adapter = ModuleRecommendationAdapter()
    with pytest.raises(IntegrationUnavailableError) as exc_info:
        await adapter.rank_parking_options(
            destination="Pune",
            target_time=datetime.now(timezone.utc),
            candidates=[{"id": "lot-1", "totalCapacity": 100}]
        )
    assert "Recommendation Engine" in str(exc_info.value)
    assert "not installed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_http_recommendation_adapter_timeout_handling():
    """HTTP recommendation adapter raises IntegrationUnavailableError on timeout."""
    import httpx
    adapter = HttpRecommendationAdapter(service_url="http://mock-rec-service", timeout=0.1)
    
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Read timed out")):
        with pytest.raises(IntegrationUnavailableError) as exc_info:
            await adapter.rank_parking_options(
                destination="Pune",
                target_time=datetime.now(timezone.utc),
                candidates=[{"id": "lot-1", "totalCapacity": 100}]
            )
        assert "timed out" in str(exc_info.value)


@pytest.mark.asyncio
async def test_http_recommendation_adapter_malformed_response():
    """HTTP recommendation service returning non-list raises IntegrationUnavailableError."""
    adapter = HttpRecommendationAdapter(service_url="http://mock-rec-service", timeout=1.0)

    class BadResponse:
        status_code = 200
        def json(self):
            return "not-a-list-or-dict"
        @property
        def text(self):
            return ""

    with patch("httpx.AsyncClient.post", return_value=BadResponse()):
        with pytest.raises(IntegrationUnavailableError) as exc_info:
            await adapter.rank_parking_options(
                destination="Pune",
                target_time=datetime.now(timezone.utc),
                candidates=[{"id": "lot-1", "totalCapacity": 100}]
            )
        assert "Invalid response" in str(exc_info.value)
