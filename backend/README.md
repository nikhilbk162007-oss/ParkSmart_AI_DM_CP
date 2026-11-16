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
    api/
      dependencies/
        auth.py                   # Bearer-token and administrator authorization dependencies
    db/
      mongodb.py                  # PyMongo connection lifecycle, clean shutdown & ping verification
      indexes.py                  # Idempotent database index definitions
    models/
      parking.py                  # ParkingFacility domain model & measured occupancy invariants
    schemas/
      auth.py                     # Login, regular-user registration & public user schemas
      parking.py                  # Parking request/response schemas (ParkingCreate, ParkingBaseResponse)
      prediction.py               # Occupancy prediction response schema & invariants
      recommendation.py           # Multi-criteria recommendation schemas & ISO-8601 parsing
    repositories/
      auth_repository.py          # MongoDB and in-memory account storage
      parking_repository.py       # Abstract ParkingRepository, Mongo & In-Memory implementations
      dependencies.py             # Repository dependency provider
    services/
      auth_service.py             # Argon2 password verification and signed bearer tokens
      parking_service.py          # Business logic and entity lookup service
      dependencies.py             # Service dependency provider
    api/
      routes/
        auth.py                   # Register, login & authenticated-user endpoints
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
    create_admin.py               # Environment-driven initial administrator provisioning
    init_indexes.py               # Safe, repeatable database index migration script
    seed_db.py                    # Local synthetic demonstration data seeder
  requirements.txt                # Production and development dependencies
  pytest.ini                      # Pytest runner configuration
  .env.example                    # Sample environment variables
  README.md                       # Setup and operating documentation
```

---

## Authentication and Roles

The API uses Argon2id password hashes and expiring HS256 bearer tokens. Set
`AUTH_JWT_SECRET` to a unique random value of at least 32 bytes; the API refuses
to start if the secret is missing or too short. Generate one for a local
PowerShell session with:

```powershell
Set-Location backend
$env:AUTH_JWT_SECRET = python -c "import secrets; print(secrets.token_urlsafe(48))"
$env:INITIAL_ADMIN_USERNAME = Read-Host "Initial admin username"
$securePassword = Read-Host "Initial admin password" -AsSecureString
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
  $env:INITIAL_ADMIN_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
}
python -m scripts.seed_db
python -m scripts.create_admin
Remove-Item Env:\INITIAL_ADMIN_USERNAME, Env:\INITIAL_ADMIN_PASSWORD
python -m uvicorn app.main:app --reload --port 8000
```

The initial admin password must be at least 12 characters. Provisioning does
not reset an existing administrator password. Keep this PowerShell session
open so the API uses the same signing secret.

`POST /api/auth/register` accepts only a username and password and always
creates a regular `user`; a supplied role is rejected. `POST /api/auth/login`
returns a short-lived access token, and `GET /api/auth/me` validates it.
`POST /api/auth/logout` revokes the active token until expiry. The frontend
keeps that bearer token in tab-scoped `sessionStorage` and clears it on logout.

`GET /api/parking`, `GET /api/predictions/{parking_id}` and
`POST /api/recommendations` require any authenticated role. Parking
create/update/delete and vehicle entry/exit endpoints require the `admin`
role. Send tokens as `Authorization: Bearer <accessToken>`.

Run the frontend in a second PowerShell window:

```powershell
Set-Location frontend
npm install
npm run dev
```

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
    "id": "P1",
    "name": "North Parking",
    "totalCapacity": 50,
    "coordinates": null,
    "dataSource": "simulated-campus-v1",
    "isSimulated": true,
    "acceptedVehicleTypes": ["car", "two-wheeler"],
    "currentOccupancy": {
      "occupiedSpaces": 15,
      "freeSpaces": 35,
      "vehicleCounts": {"car": 15, "two-wheeler": 0},
      "occupancyPercentage": 30.0
    },
    "availableSpaces": 35,
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
Calls the legacy ML integration adapter to estimate occupancy at a target arrival time. This forecast is separate from simulated entry/exit occupancy and is not used by the campus vehicle-event endpoints.
- Guarantees invariant: `predictedOccupiedSpaces + predictedFreeSpaces == totalCapacity`.
- If `ML_ADAPTER_MODE=module` and the ML module is not configured or fails, returns `503 Service Unavailable` with a descriptive message (never inventing fake predictions).

**Query Parameters:**
- `target_time` (`datetime` in ISO-8601, default: current time).

---

### 5. `POST /api/recommendations`
Returns campus parking recommendations using current occupancy from the parking
repository and the predefined weighted campus road graph. The endpoint does not
call the ML predictor and does not use geographic coordinates.

**Request Body:**
```json
{
  "destination": "Library",
  "entryGate": "gate_north",
  "vehicleType": "car"
}
```

`destination` accepts Library, Academic Block, Canteen, Auditorium, Sports
Complex, or the matching stable `dest_*` node ID. `entryGate` accepts
`gate_north` or `gate_south` and defaults to `gate_north`. `vehicleType` accepts
`car` or `two-wheeler` and defaults to `car`. The optional legacy `arrivalTime`
field is ignored by static campus routing.

The response is a direct JSON array of ranked options. Each option includes
available and occupied spaces, capacity, accepted vehicle types, gate-to-lot
distance, parking-to-destination walking distance, route paths, score and
recommendation reason. Full or vehicle-incompatible facilities are omitted;
no eligible facility produces `[]`. Distances are fictional graph distances in
metres, and occupancy is simulated rather than live.

### 6. Simulated vehicle entry and exit

The backend includes four fixed, fictional campus facilities. Their capacities
and starting occupancy are simulation inputs, not real campus measurements:

| ID | Facility | Capacity | Initially occupied | Accepted vehicles |
|---|---|---:|---:|---|
| P1 | North Parking | 50 | 15 | `car`, `two-wheeler` |
| P2 | Library Parking | 30 | 18 | `car` |
| P3 | South Parking | 40 | 35 | `car`, `two-wheeler` |
| P4 | Sports Parking | 60 | 20 | `car`, `two-wheeler` |

The initial vehicle-type breakdown was not specified, so seed occupancy is
initialized as cars; the two-wheeler count starts at zero. The seed utility
resets these four facilities to their initial simulation state and removes the
previous known simulated Pune fixtures. Parking records have no geographic
coordinates until campus map data is defined.

Both event endpoints accept `car` or `two-wheeler` and return the updated
parking record, including `currentOccupancy.vehicleCounts`, `occupiedSpaces`,
`freeSpaces`, and top-level `availableSpaces`. Counts and capacity checks are
updated atomically in MongoDB and under a lock in the in-memory repository.
Unknown facilities return 404; unsupported vehicle types fail request
validation with 422; incompatible vehicle types, full entries, and exits
without a matching parked vehicle return 400.

Record one car entering North Parking:

```http
POST /api/parking/P1/entry
Content-Type: application/json

{"vehicleType": "car"}
```

The response is the updated facility, with `occupiedSpaces: 16`,
`freeSpaces: 34`, `vehicleCounts: {"car": 16, "two-wheeler": 0}`, and
`availableSpaces: 34`.

Record one car exiting:

```http
POST /api/parking/P1/exit
Content-Type: application/json

{"vehicleType": "car"}
```

Occupancy values are simulated state changes. They are explicitly marked
`isSimulated: true` and `dataSource: "simulated-campus-v1"`; they do not
represent live sensors or real-time campus availability.

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
include the local editable `ml-model` and `recommendation-engine` packages, so
this also installs the ML model and the PRD 4 recommendation engine with their
runtime dependencies.

### 2. Configure Environment
```bash
cp .env.example .env
```

Important settings include `APP_TIMEZONE=Asia/Kolkata`,
`ML_ADAPTER_MODE`/`REC_ADAPTER_MODE` (`mock`, `module`, or `http`),
`ML_SERVICE_URL`, `ML_TIMEOUT_SECONDS`, `REC_SERVICE_URL`, and
`REC_TIMEOUT_SECONDS`. See `.env.example` for the full list and safe local
defaults.

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
The automated unit and integration tests run deterministically via
dependency-injected repositories and mocked Mongo lifecycle, without requiring
a live MongoDB server.

## Campus recommendation behaviour

The campus score is
`0.6 * (availableSpaces / totalCapacity) + 0.4 * (1 / (1 + totalDistanceMeters / 1000))`.
Exact ties are broken by facility ID. Both `REC_ADAPTER_MODE=mock` and
`REC_ADAPTER_MODE=module` execute the campus graph engine in-process.
`REC_ADAPTER_MODE=http` is not supported for the campus contract and returns a
structured 503 until the configured HTTP service implements that contract.
Arrival time does not affect the fixed graph or route distances.
