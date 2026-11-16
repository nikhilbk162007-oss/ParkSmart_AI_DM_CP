# ParkSmart AI Recommendation Engine

The package retains the original recommendation function and adds the
university-campus route and recommendation flow used by the backend.

## Campus recommendations

`campus_graph.py` is the authoritative fictional campus map. It defines
stable node IDs and undirected road edges weighted in integer metres. There
are two gates, five destinations, four parking facilities, and the junctions
needed to connect them. The graph uses no geographic coordinates or external
map service.

`shortest_path(graph, start, end)` in `dijkstra.py` uses heap-based Dijkstra
and returns `(distance, ordered_node_ids)`. Unreachable nodes return `(None, [])`;
unknown nodes raise `ValueError`.

`recommend_campus_parking(request)` expects a destination, optional entry gate
and vehicle type, and candidates containing facility IDs, capacity, accepted
vehicle types, simulated occupancy and vehicle counts. It excludes full,
incompatible, invalid, or unreachable candidates. The backend supplies these
candidate occupancy values from the parking repository; the module neither
hardcodes occupancy nor calls the ML predictor.

The deterministic score is:

```text
0.6 * (availableSpaces / totalCapacity)
+ 0.4 * (1 / (1 + totalDistanceMeters / 1000))
```

`totalDistanceMeters` is the sum of the gate-to-parking driving route and the
parking-to-destination walking route. Scores are sorted descending, with exact
ties broken by stable facility ID. Results include both segment paths, total
route nodes, available spaces, provenance, score and a recommendation reason.
Occupancy values are simulated state, not live sensor data.

Example:

```python
from recommendation_engine.campus_recommendation import recommend_campus_parking

result = recommend_campus_parking({
    "destination": "Library",
    "entryGate": "gate_north",
    "vehicleType": "car",
    "candidates": [{
        "id": "P1",
        "name": "North Parking",
        "totalCapacity": 50,
        "acceptedVehicleTypes": ["car", "two-wheeler"],
        "isSimulated": True,
        "dataSource": "simulated-campus-v1",
        "currentOccupancy": {
            "occupiedSpaces": 15,
            "freeSpaces": 35,
            "vehicleCounts": {"car": 15, "two-wheeler": 0},
        },
    }],
})
print(result["rankedOptions"])
```

## Retained legacy recommendation

`rank_parking_candidates` remains available for existing clients and tests. It
uses the original coordinate-based sparse graph and legacy destination
resolution. That flow is not used by the campus endpoint; its geographic
distances and fixtures should not be interpreted as campus routes.

## Install

From this directory:

```bash
python -m pip install -e .
```

## Test

```bash
python -m pytest -q
```
