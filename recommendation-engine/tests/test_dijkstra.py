from recommendation_engine.dijkstra import rank_parking_candidates


def test_rank_parking_candidates_returns_ranked_options():
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
            },
            {
                "id": "fixture-market",
                "name": "Market Street Garage",
                "totalCapacity": 310,
                "coordinates": [18.5314, 73.8446],
                "predictedOccupiedSpaces": 198,
                "predictedFreeSpaces": 112,
            },
            {
                "id": "fixture-zero",
                "name": "Low Availability Garage",
                "totalCapacity": 120,
                "coordinates": [18.5600, 73.8200],
                "predictedOccupiedSpaces": 119,
                "predictedFreeSpaces": 1,
            },
        ],
        "constraints": {"maxWalkingDistanceKm": 3.0},
    }

    response = rank_parking_candidates(request)

    assert response["algorithm"] == "dijkstra-multi-criteria"
    assert response["engineSource"] == "graph-engine-v1"
    assert len(response["rankedOptions"]) == 2
    assert response["rankedOptions"][0]["recommendationStatus"] == "Recommended"
    assert response["rankedOptions"][0]["id"] == "fixture-riverfront"
    assert response["rankedOptions"][0]["predictedFreeSpaces"] == 134


def test_rank_parking_candidates_filters_by_distance_constraint():
    request = {
        "destination": "Market Street, Pune",
        "arrivalTime": "2026-10-25T14:30:00+05:30",
        "candidates": [
            {
                "id": "nearby",
                "name": "Nearby Parking",
                "totalCapacity": 200,
                "coordinates": [18.5314, 73.8446],
                "predictedOccupiedSpaces": 100,
                "predictedFreeSpaces": 100,
            },
            {
                "id": "far-away",
                "name": "Far Parking",
                "totalCapacity": 200,
                "coordinates": [18.9000, 74.2000],
                "predictedOccupiedSpaces": 50,
                "predictedFreeSpaces": 150,
            },
        ],
        "constraints": {"maxWalkingDistanceKm": 1.0},
    }

    response = rank_parking_candidates(request)
    assert [item["id"] for item in response["rankedOptions"]] == ["nearby"]


def test_rank_parking_candidates_handles_zero_availability():
    request = {
        "destination": "Pune",
        "arrivalTime": "2026-10-25T14:30:00+05:30",
        "candidates": [
            {
                "id": "zero",
                "name": "Sold Out",
                "totalCapacity": 50,
                "coordinates": [18.5204, 73.8567],
                "predictedOccupiedSpaces": 50,
                "predictedFreeSpaces": 0,
            },
        ],
    }

    response = rank_parking_candidates(request)
    assert response["rankedOptions"] == []
