from .dijkstra import rank_parking_candidates

if __name__ == "__main__":
    sample_request = {
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
            },
            {
                "id": "fixture-market",
                "name": "Market Street Garage",
                "totalCapacity": 310,
                "coordinates": [18.5314, 73.8446],
                "predictedOccupiedSpaces": 198,
                "predictedFreeSpaces": 112,
            },
        ],
        "constraints": {"maxWalkingDistanceKm": 3.0},
    }
    print(rank_parking_candidates(sample_request))
