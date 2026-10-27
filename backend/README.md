# ParkSmart AI - Backend Service

FastAPI-based API and MongoDB data layer for the **ParkSmart AI** Smart Parking Recommendation System.

---

## Architecture & Directory Structure

```
backend/
  app/
    main.py                       # FastAPI application factory, lifespan, CORS & router mounting
    core/
      config.py                   # Pydantic v2 BaseSettings configuration
      errors.py                   # Custom exceptions & consistent JSON error handlers
    db/
      mongodb.py                  # PyMongo connection lifecycle, clean shutdown & ping verification
      indexes.py                  # Idempotent database index definitions
    models/
      parking.py                  # ParkingFacility domain model & measured occupancy invariants
    schemas/
      parking.py                  # Parking request/response schemas (ParkingCreate, ParkingBaseResponse)
      prediction.py               # Occupancy prediction response schema & invariants
      recommendation.py           # Multi-criteria recommendation schemas & ISO-8601 parsing
    repositories/
      parking_repository.py       # Abstract ParkingRepository, Mongo & In-Memory implementations
      dependencies.py             # Repository dependency provider
    services/
      parking_service.py          # Business logic and entity lookup service
      dependencies.py             # Service dependency provider
    api/
      routes/
        health.py                 # GET /api/health (200 / 503)
        parking.py                # GET /api/parking, GET /api/parking/{id}, CRUD
        predictions.py            # GET /api/predictions/{id}
        recommendations.py        # POST /api/recommendations (matches Frontend search form)
    integrations/
      __init__.py                 # Adapters interface uniting ML and Recommendation engines
    adapters/
      ml_adapter.py               # ML occupancy prediction adapter (mock baseline / live module)
      recommendation_adapter.py   # Multi-criteria ranking adapter (mock baseline / live graph engine)
  tests/
    conftest.py                   # Pytest fixtures and TestClient dependency injection overrides
    test_data_layer.py            # Tests data models, bounds, invariants, duplicate IDs & CRUD
    test_health.py                # Tests API health & DB online/offline status codes
    test_parking.py               # Tests parking endpoints, documented filters & empty [] returns
    test_predictions.py           # Tests occupancy predictions, invariants & 503 on unconfigured ML
    test_recommendations.py       # Tests ranking contract, ISO-8601 timezone parsing & 503 handling
  scripts/
    init_indexes.py               # Safe, repeatable database index migration script
    seed_db.py                    # Local synthetic demonstration data seeder
  requirements.txt                # Production and development dependencies
  pytest.ini                      # Pytest runner configuration
  .env.example                    # Sample environment variables
  README.md                       # Setup and operating documentation
```

---

## API Endpoints & Contract Specification

### 1. `GET /api/health`
Checks API and live MongoDB connectivity separately.

**Response Status Codes:**
- `200 OK`: When both API and MongoDB are healthy.
- `503 Service Unavailable`: When MongoDB ping fails or database is unreachable.

**Response Body (200 OK):**
```json
{
  "status": "healthy",
  "api": "online",
  "database": {
    "status": "connected",
    "type": "mongodb",
    "ping": true
  },
  "version": "1.0.0"
}
```

**Response Body (503 Service Unavailable):**
```json
{
  "status": "degraded",
  "api": "online",
  "database": {
    "status": "disconnected",
    "type": "mongodb",
    "ping": false
  },
  "version": "1.0.0"
}
```

---

### 2. `GET /api/parking`
Returns a JSON array of parking records in the agreed frontend-compatible format. Returns `[]` if no records match (never fake fallback records).

**Query Parameters (Optional):**
- `isSimulated` (`bool`): Filter simulated records (`true` or `false`).
- `minCapacity` (`int`): Minimum total physical capacity.
- `limit` (`int`): Maximum number of records to return ($1 \le \text{limit} \le 200$).

**Response Body (200 OK):**
```json
[
  {
    "id": "fixture-riverfront",
    "name": "Riverfront Parking House",
    "totalCapacity": 420,
    "coordinates": [18.5204, 73.8567],
    "coordinateSource": "simulated-development",
    "dataSource": "simulated-development",
    "isSimulated": true,
    "address": "Riverfront Road, Pune",
    "currentOccupancy": null,
    "createdAt": "2026-01-01T00:00:00Z",
    "updatedAt": "2026-01-01T00:00:00Z"
  }
]
```

---

### 3. `GET /api/parking/{parking_id}`
Returns a single parking record or a structured 404 error.

**Response Body (404 Not Found):**
```json
{
  "error": {
    "type": "not_found",
    "message": "Parking facility with id 'unknown-id' not found.",
    "status_code": 404
  }
}
```

---

### 4. `GET /api/predictions/{parking_id}`
Calls the ML integration adapter to estimate occupancy at a target arrival time.
- Guarantees invariant: `predictedOccupiedSpaces + predictedFreeSpaces == totalCapacity`.
- If `ML_ADAPTER_MODE=module` and the ML module is not configured or fails, returns `503 Service Unavailable` with a descriptive message (never inventing fake predictions).

**Query Parameters:**
- `target_time` (`datetime` in ISO-8601, default: current time).

**Response Body (200 OK):**
```json
{
  "parkingId": "fixture-riverfront",
  "targetTime": "2026-10-25T14:30:00",
  "totalCapacity": 420,
  "predictedOccupiedSpaces": 286,
  "predictedFreeSpaces": 134,
  "occupancyPercentage": 68.1,
  "confidenceScore": 0.85,
  "modelSource": "simulated-baseline"
}
```

---

### 5. `POST /api/recommendations`
Consumes the Frontend search form criteria (`destination` and `arrivalTime`) and returns a ranked list of parking options directly compatible with `Frontend/src/services/parkingResultsProvider.js` and `ParkingCard.jsx`.

**Request Body:**
```json
{
  "destination": "Riverfront, Pune",
  "arrivalTime": "2026-10-25T14:30:00+05:30"
}
```

**Response Body (200 OK - Direct Array for Frontend Contract):**
```json
[
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
  },
  {
    "id": "fixture-market",
    "name": "Market Street Garage",
    "totalCapacity": 310,
    "predictedOccupiedSpaces": 198,
    "predictedFreeSpaces": 112,
    "distanceKm": 1.2,
    "coordinates": [18.5314, 73.8446],
    "coordinateSource": "simulated-development",
    "dataSource": "simulated-development",
    "recommendationStatus": "Alternative option",
    "recommendationExplanation": "Secondary alternative with 112 estimated available spaces"
  }
]
```

**Validation Error Response (422 Unprocessable Content):**
```json
{
  "error": {
    "type": "validation_error",
    "message": "Input validation failed. Please check the submitted fields.",
    "details": [
      {
        "location": "body -> arrivalTime",
        "message": "Invalid ISO-8601 timestamp format",
        "type": "value_error"
      }
    ],
    "status_code": 422
  }
}
```

---

## Setup & Running Locally

### 1. Setup Virtual Environment
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Run the installation command from the `backend/` directory. Its requirements
include the local editable `ml-model` package, so this also installs the ML
package and its declared runtime dependencies.

### 2. Configure Environment
```bash
cp .env.example .env
```

### 3. Run Database Index Migration
```bash
python -m scripts.init_indexes
```

### 4. (Optional) Seed Local Demonstration Data
```bash
python -m scripts.seed_db
```

### 5. Start the Server
```bash
uvicorn app.main:app --reload --port 8000
```
- Interactive OpenAPI / Swagger Documentation: `http://localhost:8000/docs`

### 6. Run Automated Tests
```bash
pytest -v
```
All 26 automated unit and integration tests run deterministically via dependency-injected test repositories without requiring a live MongoDB server.
