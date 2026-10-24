# ParkSmart AI - Module Integration Contracts

This document specifies the exact typed interface contracts between the **Backend API**, the **AI/ML Occupancy Prediction Module** (PRD 3), and the **Discrete Mathematics Recommendation Engine** (PRD 4).

---

## 1. AI/ML Occupancy Prediction Module (PRD 3)

The ML module forecasts occupancy counts for a specific parking facility at a future arrival time.

### Invocation Modes
Configured via `ML_ADAPTER_MODE` in `.env`:
- `mock`: Deterministic diurnal baseline simulation (default for local development and offline testing).
- `module`: Direct Python function import (`from ml_model.predict import predict_occupancy`).
- `http`: Microservice POST request to `http://localhost:8001/predict`.

### Request Contract
```json
{
  "parkingId": "fixture-riverfront",
  "totalCapacity": 420,
  "targetTime": "2026-10-25T14:30:00+05:30",
  "features": {
    "dayOfWeek": 6,
    "hourOfDay": 14
  }
}
```

### Response Contract
The model must return occupancy estimates bounded by capacity:
```json
{
  "predictedOccupiedSpaces": 286,
  "predictedFreeSpaces": 134,
  "occupancyPercentage": 68.1,
  "confidenceScore": null,
  "modelSource": "random-forest-regressor-v1",
  "predictedAt": "2026-10-24T10:30:00Z",
  "targetTime": "2026-10-25T14:30:00+05:30"
}
```

### Invariants & Guardrails
1. `0 <= predictedOccupiedSpaces <= totalCapacity`
2. `predictedOccupiedSpaces + predictedFreeSpaces == totalCapacity`
3. `occupancyPercentage == (predictedOccupiedSpaces / totalCapacity) * 100`
4. Never return unrounded or negative counts.

---

## 2. Discrete Mathematics Recommendation Engine (PRD 4)

The Recommendation Engine executes graph shortest-path routing (Dijkstra's algorithm), candidate filtering, and multi-criteria scoring.

### Invocation Modes
Configured via `REC_ADAPTER_MODE` in `.env`:
- `mock`: Multi-criteria availability and distance balance for local development.
- `module`: Direct Python function import (`from recommendation_engine.dijkstra import rank_parking_candidates`).
- `http`: Microservice POST request to `http://localhost:8002/recommend`.

### Request Contract
```json
{
  "destination": "Riverfront Road, Pune",
  "arrivalTime": "2026-10-25T14:30:00+05:30",
  "candidates": [
    {
      "id": "fixture-riverfront",
      "name": "Riverfront Parking House",
      "totalCapacity": 420,
      "coordinates": [18.5204, 73.8567],
      "coordinateSource": "simulated-development",
      "dataSource": "simulated-development",
      "isSimulated": true,
      "predictedOccupiedSpaces": 286,
      "predictedFreeSpaces": 134,
      "occupancyPercentage": 68.1
    }
  ],
  "constraints": {
    "maxWalkingDistanceKm": 3.0
  }
}
```

### Response Contract
The engine returns ordered candidates with recommendation status and explanations:
```json
{
  "rankedOptions": [
    {
      "id": "fixture-riverfront",
      "name": "Riverfront Parking House",
      "totalCapacity": 420,
      "predictedOccupiedSpaces": 286,
      "predictedFreeSpaces": 134,
      "distanceKm": 0.7,
      "coordinates": [18.5204, 73.8567],
      "coordinateSource": "simulated-development",
      "dataSource": "simulated-development",
      "recommendationStatus": "Recommended",
      "recommendationExplanation": "Optimal balance: 134 spaces free and 0.7 km away"
    }
  ],
  "algorithm": "dijkstra-multi-criteria",
  "engineSource": "graph-engine-v1"
}
```

### Frontend Required Status Values
- `"Recommended"` (assigned to the top candidate)
- `"Alternative option"` (assigned to viable secondary alternatives)
- `"Preview option"` (optional demonstration status)
