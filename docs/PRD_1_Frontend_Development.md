# PRD 1: Frontend Development

## Project
**ParkSmart AI — AI-Based Smart Parking Recommendation System**

## Objective
Build a responsive interface that lets users search for parking, compare recommendations, and view predicted availability and route information returned by the backend.

## Responsibilities
- Build the UI with React and Vite.
- Create destination search and target-time selection.
- Display parking locations on a Leaflet/OpenStreetMap map.
- Show parking cards with capacity, predicted availability, distance, and recommendation reasons where provided by the API.
- Add relevant filters and sorting.
- Handle loading, empty, and error states.
- Make the interface responsive.
- Render API data rather than hardcoding results.

## Proposed Technology
- React + Vite
- JavaScript or TypeScript (agree with the team)
- Leaflet + OpenStreetMap

## User Flow
1. User enters a destination and target time.
2. Frontend requests recommendations from the backend.
3. Results are displayed as cards and map markers.
4. User compares availability, distance, and route details.
5. User selects a parking option for more information.

## Integration
Coordinate with the backend member before implementing requests. Proposed endpoints, to be confirmed by the team:
- `GET /api/parking`
- `GET /api/parking/{parking_id}`
- `GET /api/predictions/{parking_id}`
- `POST /api/recommendations`
- `GET /api/health`

## Deliverables
- Working React/Vite frontend.
- Search and results UI.
- Map with parking markers.
- Responsive design and loading/error/empty states.
- API integration.
- Setup instructions in `frontend/README.md`.

## Acceptance Criteria
- App starts using documented commands.
- Search results come from the API.
- Map markers use coordinates returned by the API.
- Empty responses and errors are handled.
- Sample, predicted, and live data are clearly distinguished.
- No live-availability claims are made unless live data is actually integrated.

## Dependencies
- Backend: API contract and sample responses.
- ML: prediction field definitions and limitations.
- Recommendation engine: ranking fields and recommendation reasons.

## Out of Scope
Building the ML model, database logic, or recommendation algorithm.
