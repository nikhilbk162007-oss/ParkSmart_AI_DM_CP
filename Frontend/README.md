# ParkSmart AI Frontend

The initial React interface for ParkSmart AI, a smart parking recommendation system. This first stage establishes the responsive visual identity and application shell.

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

## Environment variables

Copy `.env.example` to `.env.local` when preparing local configuration:

```text
VITE_API_BASE_URL=http://localhost:8000
```

This value is an example for future integration. The frontend does not currently read it or make API requests.

## Structure

- `src/App.jsx` — page shell, header, hero, and supporting illustration
- `src/components/SearchPanel.jsx` — destination and arrival-time controls with validation
- `src/components/ResultsSection.jsx` — results heading, filters, sorting, and empty state
- `src/components/ParkingCard.jsx` — reusable parking result presentation
- `src/data/parkingFixtures.js` — explicitly simulated development-only parking examples
- `src/services/parkingResultsProvider.js` — isolated provider for development results
- `src/index.css` — design tokens, layout, responsive rules, and focus styles
- `src/main.jsx` — React application entry point

## Implementation status

Implemented: initial responsive shell, brand styling, accessible destination and arrival-time inputs, inline validation, local search-criteria capture, sortable/filterable result presentation, reusable parking cards, and a non-data parking-garage illustration.

After valid submission, the results section displays simulated development fixtures. Every example is marked as simulated; names, capacity, distances, and predicted figures are fictional, are not based on the entered destination, and do not represent live availability. Sorting and filtering operate only on these fixtures. The interface also supports a no-matching-results state.

No API is called, and no real recommendations are retrieved. Map integration, backend integration, ML prediction, and recommendation algorithms remain unimplemented.
