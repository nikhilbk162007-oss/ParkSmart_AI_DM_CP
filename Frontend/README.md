# ParkSmart AI — Campus Parking Dashboard

Responsive React + Vite dashboard for the fictional university-campus parking
simulation. The UI reads facility occupancy and recommendations from the
FastAPI backend and submits simulated vehicle entry/exit events. It does not
use frontend fixture data as a fallback.

## Features

- **Dashboard:** total capacity, occupied and available spaces, occupancy rate,
  facility comparison, and campus overview.
- **Find parking:** choose Library, Academic Block, Canteen, Auditorium, or
  Sports Complex; select North/South Gate and car/two-wheeler; review ranked
  recommendations and route segments.
- **Campus map:** interactive schematic of the graph’s gates, destinations,
  roads, and parking facilities. Node positions are for presentation only and
  are not geographic coordinates.
- **Simulation control:** post one vehicle entry or exit and refresh facility
  state and current recommendations.
- **Parking details:** capacity, availability, occupancy by vehicle type,
  compatibility, and available recommendation route details.

All facility occupancy is explicitly simulated. It is not live sensor data.

## Start the demonstration

Prerequisites: Python 3.10+, Node.js 20+, npm, and a running local MongoDB
service (default URI `mongodb://localhost:27017`).

In a PowerShell terminal from the project root, configure and seed the backend:

```powershell
Set-Location .\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m scripts.seed_db
uvicorn app.main:app --reload --port 8000
```

In a second terminal from the project root:

```powershell
Set-Location .\frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). The frontend API base
defaults to `http://localhost:8000`; override `VITE_API_BASE_URL` in
`.env.local` if the backend runs elsewhere. Backend CORS defaults include the
local Vite origins above.

The seed command initializes the four fictional campus parking records and
their initial occupancy. Reseeding resets those simulation values.

## API contract

- `GET /api/parking` — facility capacities, accepted vehicle types, current
  occupancy and available spaces.
- `POST /api/recommendations` — request body:
  `{"destination":"Library","entryGate":"gate_north","vehicleType":"car"}`.
  The backend returns a direct JSON array containing route distances, paths,
  scores, availability and recommendation explanations.
- `POST /api/parking/{parking_id}/entry` and
  `POST /api/parking/{parking_id}/exit` — request body:
  `{"vehicleType":"car"}`. Each successful request changes occupancy by one.

The dashboard reports backend errors and provides retry; it never replaces
failed or empty API responses with demo fixtures. Route paths use stable graph
node IDs. Campus map node positions are schematic and must not be interpreted
as GPS coordinates.

## Development

```powershell
npm test
npm run build
```

The frontend uses React, Vite, Lucide icons, Vitest, and React Testing Library.
No new runtime dependencies are required.
