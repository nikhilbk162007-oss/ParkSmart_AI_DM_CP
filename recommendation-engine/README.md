# ParkSmart AI Recommendation Engine

This module implements the PRD 4 recommendation engine for ParkSmart AI.

## What it does

- models parking locations and destination as weighted graph vertices
- computes shortest paths with Dijkstra's algorithm
- filters candidates using availability and distance constraints
- ranks options with a documented availability-first, distance-second score

## Ranking rule

The engine uses the following deterministic score:

score = (predicted_free_spaces * 10) - distance_km

This keeps available parking as the primary decision factor and uses route distance as a tie-breaker. Higher score wins. The rule is documented and not arbitrary.

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
