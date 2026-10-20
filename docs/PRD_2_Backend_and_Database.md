# PRD 2: Backend and Database

## Project
**ParkSmart AI — AI-Based Smart Parking Recommendation System**

## Objective
Build the API and data layer connecting the frontend, ML prediction module, and recommendation engine.

## Responsibilities
- Build the API using Python and FastAPI.
- Define a shared parking data schema.
- Integrate MongoDB.
- Validate requests and stored data.
- Connect the ML and recommendation modules using agreed interfaces.
- Return consistent JSON responses and clear errors.
- Use environment variables for configuration.
- Add API tests and setup documentation.

## Proposed Technology
- Python, FastAPI, MongoDB, Pydantic, Pytest.

## Proposed API Endpoints
Confirm exact request and response fields with the team before implementation.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/parking` | List parking locations |
| GET | `/api/parking/{parking_id}` | Get one parking location |
| GET | `/api/predictions/{parking_id}` | Get occupancy prediction |
| POST | `/api/recommendations` | Request ranked recommendations |
| GET | `/api/health` | Health check |

## Shared Data Contract
Agree on:
- Stable `parking_id`.
- Parking capacity and occupancy definitions.
- Coordinate format, such as `latitude` and `longitude`.
- Target-time format and timezone.
- Distance units.
- Whether predictions are counts or percentages.
- Recommendation score and explanation fields.

Do not mix occupied spaces, free spaces, and occupancy percentages without explicitly documenting conversions.

## Validation and Security
- Validate capacity and occupancy bounds.
- Handle missing or invalid coordinates.
- Return a clear response for unknown parking IDs.
- Distinguish simulated/sample records from real data.
- Never commit database credentials or secrets.

## Deliverables
- FastAPI application and route modules.
- MongoDB data-access layer.
- Shared request/response schemas.
- ML and recommendation integration interfaces.
- Tests for API behavior and validation.
- `.env.example` with placeholder names only.
- Setup instructions in `backend/README.md`.

## Acceptance Criteria
- API starts using documented commands.
- Endpoints follow documented response schemas.
- Invalid input produces understandable errors.
- Frontend can use the agreed API contract.
- ML and recommendation modules can integrate without duplicate schema definitions.
- Secrets are not stored in source control.

## Dependencies
Frontend needs API contracts; ML needs stable inputs/outputs; the recommendation engine needs parking records, predictions, and route-related fields.
