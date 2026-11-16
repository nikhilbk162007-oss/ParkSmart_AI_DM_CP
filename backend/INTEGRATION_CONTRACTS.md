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
  "parkingId": "P1",
  "totalCapacity": 50,
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
  "predictedOccupiedSpaces": 30,
  "predictedFreeSpaces": 20,
  "occupancyPercentage": 60.0,
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

Naive arrival times are interpreted in the backend `APP_TIMEZONE` (default
`Asia/Kolkata`) before invoking an ML adapter. An explicit offset continues to
identify the same absolute instant.

## 2. Fictional campus vehicle events

The backend's initial campus simulation uses these fixed records:

| ID | Name | Capacity | Initial occupancy | Accepted vehicle types |
|---|---|---:|---:|---|
| P1 | North Parking | 50 | 15 | `car`, `two-wheeler` |
| P2 | Library Parking | 30 | 18 | `car` |
| P3 | South Parking | 40 | 35 | `car`, `two-wheeler` |
| P4 | Sports Parking | 60 | 20 | `car`, `two-wheeler` |

These are simulated values, not campus measurements. Because the initial
vehicle-type split was not provided, every initially occupied space is seeded
as a car and the initial two-wheeler count is zero. Coordinates are omitted
rather than inventing campus geography.

### Entry

`POST /api/parking/{parking_id}/entry`

```json
{"vehicleType": "two-wheeler"}
```

Supported values are exactly `car` and `two-wheeler`. A successful request
increments the total occupancy and that vehicle type's count by one, and
decrements free spaces by one. The endpoint returns the updated parking record.
For example, after a two-wheeler enters P1, `currentOccupancy` contains:

```json
{
  "occupiedSpaces": 16,
  "freeSpaces": 34,
  "vehicleCounts": {"car": 15, "two-wheeler": 1},
  "occupancyPercentage": 32.0
}
```

### Exit

`POST /api/parking/{parking_id}/exit`

```json
{"vehicleType": "two-wheeler"}
```

A successful request decrements occupancy only when at least one parked
vehicle of that type exists. Entry is rejected when the facility is full. An
unsupported or facility-incompatible vehicle type, a full facility, or an exit
without a matching parked vehicle returns a structured 400/422 error; unknown
parking IDs return 404.

`availableSpaces` is returned at the top level and always equals
`totalCapacity - currentOccupancy.occupiedSpaces`. MongoDB uses one conditional
document update per event; the in-memory implementation protects the same
operation with a lock. Event updates change the simulated state and do not
claim live sensor or real-time availability.

---

## 3. Discrete Mathematics Recommendation Engine (PRD 4)

Campus recommendations use the predefined weighted, undirected road graph in
`recommendation_engine.campus_graph`. Edge weights are fictional road distances
in metres; no geographic coordinates or external map service are used. The
backend loads current simulated occupancy from its parking repository and does
not invoke the ML predictor for this endpoint.

### Invocation Modes
Configured via `REC_ADAPTER_MODE` in `.env`:
- `mock` and `module`: Both call the campus recommendation function in-process.
- `http`: Not supported for the campus contract; returns a structured 503 until
  the configured service implements the campus request/response contract.

### Request Contract
`POST /api/recommendations`

```json
{
  "destination": "Library",
  "entryGate": "gate_north",
  "vehicleType": "car",
  "arrivalTime": "2026-10-25T14:30:00+05:30"
}
```

`destination` must be one of Library, Academic Block, Canteen, Auditorium, or
Sports Complex (or its stable `dest_*` node ID). `entryGate` accepts
`gate_north` or `gate_south` and defaults to `gate_north`. `vehicleType` accepts
`car` or `two-wheeler` and defaults to `car`. `arrivalTime` is optional and
retained for compatibility; the fixed campus routes do not vary by time.

### Response Contract
The endpoint returns an ordered JSON array. Full and incompatible facilities
are omitted; an empty array means no eligible facility is available.

```json
[
  {
    "id": "P1",
    "name": "North Parking",
    "totalCapacity": 50,
    "availableSpaces": 35,
    "occupiedSpaces": 15,
    "acceptedVehicleTypes": ["car", "two-wheeler"],
    "isSimulated": true,
    "dataSource": "simulated-campus-v1",
    "entryGate": "gate_north",
    "destination": "dest_library",
    "routeDistanceMeters": 170,
    "walkingDistanceMeters": 390,
    "totalDistanceMeters": 560,
    "entryRoutePath": ["gate_north", "road_north", "P1"],
    "walkingRoutePath": ["P1", "road_north", "road_central", "road_library", "dest_library"],
    "routePath": ["gate_north", "road_north", "P1", "road_north", "road_central", "road_library", "dest_library"],
    "routeDetails": [
      {"segment": "entry-to-parking", "distanceMeters": 170, "path": ["gate_north", "road_north", "P1"]},
      {"segment": "parking-to-destination", "distanceMeters": 390, "path": ["P1", "road_north", "road_central", "road_library", "dest_library"]}
    ],
    "score": 0.67641,
    "recommendationReason": "35 spaces available (35/50); 170 m from North Gate and 390 m walk to Library (combined 560 m; score 0.676).",
    "recommendationStatus": "Recommended"
  }
]
```

The engine runs heap-based Dijkstra independently from the selected gate to
each eligible parking node and from each parking node to the destination.
`routeDistanceMeters` is the gate-to-parking distance; `walkingDistanceMeters`
is the parking-to-destination distance. Their sum is `totalDistanceMeters`.
Route paths contain stable graph node IDs.

The deterministic score is:
`0.6 * (availableSpaces / totalCapacity) + 0.4 * (1 / (1 + totalDistanceMeters / 1000))`.
Exact score ties are broken by stable facility ID. The first result is
`Recommended`; subsequent results are `Alternative option`. Invalid destinations,
gates, and vehicle types are rejected rather than being mapped to a geographic
fallback. Returned availability is simulated repository state and does not
represent live sensor data.
