import time

from recommendation_engine.dijkstra import (
    _build_sparse_graph,
    _dijkstra,
    rank_parking_candidates,
    resolve_destination,
    shortest_path,
)
from recommendation_engine.campus_graph import (
    CAMPUS_ROAD_EDGES,
    CAMPUS_ROAD_GRAPH,
    DESTINATIONS,
    ENTRY_GATES,
    NODE_LABELS,
    PARKING_NODES,
)
from recommendation_engine.campus_recommendation import recommend_campus_parking


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


def test_rank_parking_candidates_keeps_full_lots_last():
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
            _candidate("available", [18.521, 73.857], 10),
        ],
    }

    response = rank_parking_candidates(request)
    assert [option["id"] for option in response["rankedOptions"]] == ["available", "zero"]
    assert response["rankedOptions"][0]["recommendationStatus"] == "Recommended"
    assert response["rankedOptions"][1]["recommendationStatus"] == "Full at arrival"


def _candidate(identifier, coordinates, free, capacity=100):
    return {
        "id": identifier,
        "name": identifier,
        "totalCapacity": capacity,
        "coordinates": coordinates,
        "predictedOccupiedSpaces": capacity - free,
        "predictedFreeSpaces": free,
    }


def test_weighted_score_prefers_nearer_lot_with_slightly_less_availability():
    response = rank_parking_candidates({
        "destination": "Deccan",
        "candidates": [
            _candidate("near", [18.5173, 73.8415], 70),
            _candidate("far", [18.5500, 73.9000], 75),
        ],
    })
    assert response["rankedOptions"][0]["id"] == "near"
    assert "0.6 *" in response["routingMetadata"]["scoreFormula"]


def test_weighted_score_breaks_exact_ties_by_id():
    response = rank_parking_candidates({
        "destination": "Deccan",
        "candidates": [
            _candidate("z-lot", [18.5173, 73.8415], 50),
            _candidate("a-lot", [18.5173, 73.8415], 50),
        ],
    })
    assert [option["id"] for option in response["rankedOptions"]] == ["a-lot", "z-lot"]


def test_destination_resolver_uses_word_boundaries_and_reports_unresolved():
    assert resolve_destination("Deccan, Pune")[1] is True
    assert resolve_destination("Nanded railway station")[1] is False
    assert resolve_destination("Garden City, Bengaluru")[1] is False
    result = rank_parking_candidates({
        "destination": "Nanded railway station",
        "candidates": [_candidate("lot", [18.52, 73.85], 10)],
    })
    assert result["routingMetadata"]["destinationResolved"] is False
    assert "Destination not recognised" in result["rankedOptions"][0]["recommendationExplanation"]


def test_graph_is_connected_and_dijkstra_prefers_intended_shorter_path():
    candidates = [
        _candidate("one", [18.0, 73.0], 10),
        _candidate("two", [18.1, 73.1], 10),
        _candidate("three", [18.2, 73.2], 10),
    ]
    graph, _ = _build_sparse_graph((18.0, 73.0), candidates, 2)
    distances = _dijkstra(graph, "destination")
    assert all(value < float("inf") for value in distances.values())
    custom = {
        "start": {"end": 10.0, "middle": 2.0},
        "middle": {"start": 2.0, "end": 2.0},
        "end": {"start": 10.0, "middle": 2.0},
    }
    assert _dijkstra(custom, "start")["end"] == 4.0


def test_two_thousand_candidates_rank_in_under_one_second():
    candidates = [
        _candidate(
            f"lot-{index:04d}",
            [18.0 + (index % 100) * 0.001, 73.0 + (index // 100) * 0.01],
            20 + index % 70,
        )
        for index in range(2000)
    ]
    started = time.perf_counter()
    result = rank_parking_candidates({"destination": "Unknown", "candidates": candidates})
    elapsed = time.perf_counter() - started
    assert len(result["rankedOptions"]) == 2000
    assert elapsed < 1.0


def test_destination_named_destination_and_duplicate_ids_keep_separate_nodes():
    response = rank_parking_candidates({
        "destination": "Deccan",
        "candidates": [
            _candidate("destination", [18.55, 73.9], 10),
            _candidate("same", [18.51, 73.84], 10),
            _candidate("same", [18.52, 73.85], 10),
        ],
    })
    assert len(response["rankedOptions"]) == 3
    assert response["rankedOptions"][0]["distanceKm"] > 0


def _campus_candidate(identifier, capacity, occupied, accepted):
    return {
        "id": identifier,
        "name": NODE_LABELS[identifier],
        "totalCapacity": capacity,
        "acceptedVehicleTypes": accepted,
        "isSimulated": True,
        "dataSource": "simulated-campus-v1",
        "currentOccupancy": {
            "occupiedSpaces": occupied,
            "freeSpaces": capacity - occupied,
            "vehicleCounts": {"car": occupied, "two-wheeler": 0}
            if "two-wheeler" in accepted
            else {"car": occupied},
        },
    }


def test_campus_graph_edges_are_positive_and_undirected():
    assert set(CAMPUS_ROAD_GRAPH) == set(NODE_LABELS)
    for first, second, distance in CAMPUS_ROAD_EDGES:
        assert distance > 0
        assert CAMPUS_ROAD_GRAPH[first][second] == distance
        assert CAMPUS_ROAD_GRAPH[second][first] == distance


def test_dijkstra_reconstructs_known_campus_routes():
    assert shortest_path(CAMPUS_ROAD_GRAPH, "gate_north", "P1") == (
        170,
        ["gate_north", "road_north", "P1"],
    )
    assert shortest_path(CAMPUS_ROAD_GRAPH, "P1", "dest_library") == (
        390,
        ["P1", "road_north", "road_central", "road_library", "dest_library"],
    )
    assert shortest_path(CAMPUS_ROAD_GRAPH, "gate_south", "P3") == (
        145,
        ["gate_south", "road_south", "P3"],
    )


def test_all_gates_can_reach_all_destinations_and_parking_nodes():
    for gate in ENTRY_GATES.values():
        for destination in DESTINATIONS.values():
            distance, path = shortest_path(CAMPUS_ROAD_GRAPH, gate, destination)
            assert distance is not None
            assert path[0] == gate
            assert path[-1] == destination
        for parking in PARKING_NODES:
            assert shortest_path(CAMPUS_ROAD_GRAPH, gate, parking)[0] is not None


def test_shortest_path_reports_unreachable_and_rejects_invalid_nodes():
    disconnected_graph = {"start": {}, "end": {}}
    assert shortest_path(disconnected_graph, "start", "end") == (None, [])
    for start, end in [("missing", "end"), ("start", "missing")]:
        try:
            shortest_path(disconnected_graph, start, end)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid graph node must be rejected")


def test_campus_recommendations_filter_and_return_route_segments():
    candidates = [
        _campus_candidate("P1", 50, 15, ["car", "two-wheeler"]),
        _campus_candidate("P2", 30, 18, ["car"]),
        _campus_candidate("P3", 40, 35, ["car", "two-wheeler"]),
        _campus_candidate("P4", 60, 60, ["car", "two-wheeler"]),
    ]
    response = recommend_campus_parking({
        "destination": "Library",
        "entryGate": "gate_north",
        "vehicleType": "two-wheeler",
        "candidates": candidates,
    })
    options = response["rankedOptions"]
    assert {option["id"] for option in options} == {"P1", "P3"}
    assert options[0]["id"] == "P1"
    assert options[0]["routeDistanceMeters"] == 170
    assert options[0]["walkingDistanceMeters"] == 390
    assert options[0]["routePath"] == [
        "gate_north",
        "road_north",
        "P1",
        "road_north",
        "road_central",
        "road_library",
        "dest_library",
    ]
    assert options[0]["recommendationStatus"] == "Recommended"
    assert options[0]["recommendationReason"]


def test_campus_recommendation_uses_live_simulated_occupancy_and_gate():
    candidates = [
        _campus_candidate("P1", 50, 15, ["car", "two-wheeler"]),
        _campus_candidate("P3", 40, 35, ["car", "two-wheeler"]),
    ]
    first = recommend_campus_parking({
        "destination": "Sports Complex",
        "entryGate": "gate_south",
        "vehicleType": "car",
        "candidates": candidates,
    })["rankedOptions"]
    assert first[0]["entryGate"] == "gate_south"

    candidates[0]["currentOccupancy"]["occupiedSpaces"] = 49
    candidates[0]["currentOccupancy"]["freeSpaces"] = 1
    candidates[0]["currentOccupancy"]["vehicleCounts"] = {"car": 49, "two-wheeler": 0}
    changed = recommend_campus_parking({
        "destination": "Sports Complex",
        "entryGate": "gate_south",
        "vehicleType": "car",
        "candidates": candidates,
    })["rankedOptions"]
    assert changed[0]["id"] == "P3"


def test_campus_recommendation_returns_empty_when_no_eligible_facilities():
    candidates = [
        _campus_candidate("P1", 50, 50, ["car", "two-wheeler"]),
        _campus_candidate("P2", 30, 18, ["car"]),
    ]
    assert recommend_campus_parking({
        "destination": "Canteen",
        "entryGate": "gate_north",
        "vehicleType": "two-wheeler",
        "candidates": candidates,
    })["rankedOptions"] == []


def test_campus_recommendation_invalid_gate_or_destination_is_rejected():
    base = {
        "destination": "Library",
        "entryGate": "gate_north",
        "vehicleType": "car",
        "candidates": [_campus_candidate("P1", 50, 15, ["car"])],
    }
    for key, value in [("entryGate", "gate_unknown"), ("destination", "Pune")]:
        request = {**base, key: value}
        try:
            recommend_campus_parking(request)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid {key} must be rejected")


def test_campus_recommendation_breaks_exact_score_ties_by_stable_id():
    candidates = [
        _campus_candidate("P1", 3627, 2617, ["car"]),
        _campus_candidate("P2", 3627, 2627, ["car"]),
    ]
    response = recommend_campus_parking({
        "destination": "Library",
        "entryGate": "gate_north",
        "vehicleType": "car",
        "candidates": candidates,
    })
    options = response["rankedOptions"]
    assert options[0]["score"] == options[1]["score"]
    assert [option["id"] for option in options] == ["P1", "P2"]
