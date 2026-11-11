# ParkSmart AI Recommendation Engine

This module implements the PRD 4 recommendation engine for ParkSmart AI.

## What it does

- models parking locations and destination as weighted graph vertices
- computes shortest paths with Dijkstra's algorithm
- filters candidates using availability and distance constraints
- ranks options with a documented availability-first, distance-second score

## Ranking rule

The engine uses the following deterministic normalized score:

score = 0.6 * (predicted_free_spaces / total_capacity) + 0.4 * (1 / (1 + route_distance_km))

Weights are configurable via the request constraints `availabilityWeight` and
`proximityWeight`; they are normalized to sum to one. The defaults prioritize
availability while still accounting for proximity. Exact score ties are broken
by the stable option ID.

Destination lookups use whole-phrase matches for known Pune places. Unrecognized
destinations use the candidate-set centre as a clearly disclosed reference;
they are never silently geocoded to central Pune. Sparse k-nearest-neighbour
graphs use Dijkstra shortest paths with haversine edge lengths multiplied by
`ROAD_DETOUR_FACTOR=1.3`.

Facilities with no predicted availability remain in the output, last, with the
status `Full at arrival`. All coordinates and predictions retain their data
provenance; the engine does not create live data.

## Example usage

```python
from recommendation_engine.dijkstra import rank_parking_candidates

request = {
    "destination": "Riverfront, Pune",
    "arrivalTime": "2026-10-25T14:30:00+05:30",
    "candidates": [
        {
            "id": "fixture-riverfront",
            "name": "Riverfront Parking House",
            "totalCapacity": 420,
            "coordinates": [18.5204, 73.8567],
            "predictedOccupiedSpaces": 286,
            "predictedFreeSpaces": 134,
        }
    ],
    "constraints": {"maxWalkingDistanceKm": 3.0},
}

result = rank_parking_candidates(request)
print(result["rankedOptions"])
```

## Install

From this directory:

```bash
python -m pip install -e .
```

## Test

```bash
python -m pytest -q
```
