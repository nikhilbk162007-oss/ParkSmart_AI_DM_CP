# ParkSmart AI Frontend

Responsive React + Vite frontend for ParkSmart AI. It provides destination and arrival-time
selection, parking-result comparison, sorting and filters, and an India-constrained Leaflet map.
The recommendation provider uses an adapter boundary and sends API-mode searches
to the confirmed backend `POST /api/recommendations` contract.

## Prerequisites

- Node.js 20 or later
- npm

## Install and run

From this directory:

```bash
npm install
npm run dev
```

Vite prints the local development URL after startup. To create and preview a production build:

```bash
npm run build
npm run preview
```

Demo-mode results include an interactive Leaflet map using OpenStreetMap tiles. The map starts near
Pune and is constrained to India. Demo marker coordinates are simulated and are not verified
parking locations; map tiles may require an internet connection.

## Tests

Run the complete test suite once:

```bash
npm test
```

Run tests in watch mode during development:

```bash
npm run test:watch
```

Tests use Vitest, jsdom, and React Testing Library. They use simulated fixtures
and mocked API responses; no tests make real network requests.

## Environment variables

Copy `.env.example` to `.env.local` to choose the results provider:

```text
VITE_PARKING_DATA_MODE=demo
VITE_API_BASE_URL=
```

- `VITE_PARKING_DATA_MODE` accepts `demo` or `api` and defaults to `demo`.
- Demo mode reads only the simulated development fixtures.
- API mode posts to `${VITE_API_BASE_URL}/api/recommendations` with an ISO-8601 absolute arrival timestamp. Backend error messages and retry are supported.
- Vite environment variables are included in the browser bundle. Do not put private API keys or secrets in `.env` variables prefixed with `VITE_`.

The default API adapter implements the agreed backend contract. Tests and other
consumers can inject a custom adapter. Adapter results are checked for object
records with unique IDs; malformed records are surfaced as an error rather than
silently dropped or replaced with demo data.

## Remaining integration details

The backend base URL, search endpoint, HTTP method, destination and arrival-time
request fields, and direct-array response shape are implemented. The frontend
expects each result to have a stable unique `id`; optional display fields are
`name`, `totalCapacity`, `predictedOccupiedSpaces`, `predictedFreeSpaces`,
`distanceKm`, `coordinates` (`[latitude, longitude]`), `recommendationStatus`,
and `recommendationExplanation`.
- **Set C — predictions:** definitions and units for occupied/free counts; whether the figures are predictions or current observations; prediction horizon and timestamp; treatment of stale or unavailable predictions; and any confidence/limitation metadata that should be shown. The UI labels occupancy as predicted and explicitly distinguishes it from current occupancy; current occupancy is not displayed because no agreed field or definition exists.
- **Set D — recommendations and routes:** recommendation status, ranking, and explanations are implemented. Route duration and route geometry/details are not currently returned; no route is inferred by the frontend from `distanceKm`.

Sample, predicted, and live information must be distinguishable in the confirmed response contract, including provenance and relevant timestamps. The frontend does not claim live availability.

## Structure

- `src/App.jsx` — page shell, header, hero, and supporting illustration
- `src/components/SearchPanel.jsx` — destination and arrival-time controls with validation
- `src/components/ResultsSection.jsx` — results heading, filters, sorting, selection, and empty state
- `src/components/ParkingCard.jsx` — reusable parking result presentation
- `src/components/ParkingMap.jsx` — India-constrained Leaflet map, validated coordinates, and synchronized marker/card selection
- `src/components/__tests__/` — search, results, sorting/filtering, and card tests
- `src/__tests__/App.test.jsx` — app-level demo and API-mode flow tests
- `src/test/setup.js` — Testing Library matchers, cleanup, and jsdom map mocks
- `src/data/parkingFixtures.js` — explicitly simulated development-only parking examples
- `src/services/parkingResultsProvider.js` — provider that selects demo fixtures or the backend API adapter
- `src/services/backendApiAdapter.js` — `POST /api/recommendations` adapter
- `src/services/__tests__/parkingResultsProvider.test.js` — adapter validation, empty results, and failure behavior
- `src/index.css` — design tokens, layout, responsive rules, and focus styles
- `src/main.jsx` — React application entry point

## Implementation status

Implemented: responsive home/search shell, accessible destination and arrival-time inputs, inline validation, local search-criteria capture, sortable/filterable result presentation, defensive optional-field display, and synchronized map/card selection. A result is highlighted as recommended only when its data explicitly has the recognized recommendation status; remaining results are labelled alternatives only when such a recommendation exists. Supplied recommendation explanations are displayed without generating one.

After valid submission, demo mode displays simulated development fixtures on the results list and map. The Pune-area coordinates and all fixture values are simulated and do not identify verified facilities or represent live availability. The map starts near Pune and is constrained to India; coordinates outside those bounds are not shown as markers. Distance is labelled as reported data: its route basis is not established, and the frontend does not calculate or imply driving distance. Occupancy is labelled predicted, not current. Sorting and filtering operate on loaded results. Loading, error, retry, no-results, no-filter-match, and invalid-map-coordinate states are supported. Searches are cancellable and stale responses are ignored.

OpenStreetMap tiles are used as the map background and require an internet connection. If map tiles fail, a fallback message is shown while the parking result list remains usable.

Current-occupancy display and route geometry remain blocked pending those data
contracts. Naive browser arrival times are converted to absolute instants before
submission. ML prediction and recommendation algorithms are implemented by
Sets C and D, not this frontend.
