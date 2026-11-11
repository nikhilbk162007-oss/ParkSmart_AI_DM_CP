from __future__ import annotations

import heapq
import math
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

AVAILABILITY_WEIGHT = 0.6
PROXIMITY_WEIGHT = 0.4
ROAD_DETOUR_FACTOR = 1.3
GRAPH_NEIGHBORS = 3
DEFAULT_REFERENCE = (18.5204, 73.8567)

DESTINATION_WAYPOINTS: Dict[str, Tuple[float, float]] = {
    "riverfront": (18.5204, 73.8567),
    "market street": (18.5314, 73.8446),
    "garden district": (18.5074, 73.8077),
    "garden road": (18.5074, 73.8077),
    "deccan": (18.5173, 73.8415),
    "shivajinagar": (18.5314, 73.8446),
    "kothrud": (18.5074, 73.8077),
    "pune": DEFAULT_REFERENCE,
}


def _haversine_km(coord_a: Sequence[float], coord_b: Sequence[float]) -> float:
    lat1, lon1 = coord_a
    lat2, lon2 = coord_b
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    value = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    return 6371.0 * 2.0 * math.atan2(math.sqrt(value), math.sqrt(1.0 - value))


def _normalize_coordinates(value: Any, fallback: Sequence[float]) -> Tuple[float, float]:
    if (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and all(isinstance(part, (int, float)) and math.isfinite(part) for part in value)
    ):
        return float(value[0]), float(value[1])
    return float(fallback[0]), float(fallback[1])


def resolve_destination(text: str) -> Tuple[Tuple[float, float], bool]:
    """Resolve known Pune destination names using whole-phrase word boundaries."""
    normalized = (text or "").strip().lower()
    for phrase, coordinates in sorted(DESTINATION_WAYPOINTS.items(), key=lambda item: -len(item[0])):
        if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", normalized):
            return coordinates, True
    return DEFAULT_REFERENCE, False


def _dijkstra(graph: Mapping[str, Mapping[str, float]], start: str) -> Dict[str, float]:
    distances = {node: math.inf for node in graph}
    distances[start] = 0.0
    frontier: List[Tuple[float, str]] = [(0.0, start)]
    while frontier:
        distance, node = heapq.heappop(frontier)
        if distance != distances[node]:
            continue
        for neighbor, weight in graph[node].items():
            candidate = distance + weight
            if candidate < distances.get(neighbor, math.inf):
                distances[neighbor] = candidate
                heapq.heappush(frontier, (candidate, neighbor))
    return distances


def _candidate_center(candidates: Sequence[Mapping[str, Any]]) -> Tuple[float, float]:
    points = [
        _normalize_coordinates(candidate.get("coordinates"), DEFAULT_REFERENCE)
        for candidate in candidates
    ]
    if not points:
        return DEFAULT_REFERENCE
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def _build_sparse_graph(
    destination: Sequence[float],
    candidates: Sequence[Mapping[str, Any]],
    neighbor_count: int,
) -> Tuple[Dict[str, Dict[str, float]], List[str]]:
    candidate_nodes = [f"candidate:{index}" for index in range(len(candidates))]
    node_ids = ["destination", *candidate_nodes]
    points = [tuple(destination)] + [
        _normalize_coordinates(candidate.get("coordinates"), destination)
        for candidate in candidates
    ]
    graph: Dict[str, Dict[str, float]] = {node: {} for node in node_ids}
    if len(points) < 2:
        return graph, candidate_nodes

    # SciPy's spatial index is available with the project's scikit-learn dependency.
    # A linear fallback keeps the engine usable in minimal installations.
    try:
        from scipy.spatial import cKDTree

        tree_points = [
            (point[0], point[1] * math.cos(math.radians(point[0])))
            for point in points
        ]
        _, neighbors = cKDTree(tree_points).query(
            tree_points, k=min(len(points), max(2, neighbor_count + 1))
        )
        neighbor_rows = neighbors.tolist()
    except ImportError:
        neighbor_rows = []
        for index, point in enumerate(points):
            ordered = sorted(
                (other for other in range(len(points)) if other != index),
                key=lambda other: _haversine_km(point, points[other]),
            )
            neighbor_rows.append([index, *ordered[:neighbor_count]])

    def connect(first: int, second: int) -> None:
        if first == second:
            return
        weight = _haversine_km(points[first], points[second]) * ROAD_DETOUR_FACTOR
        graph[node_ids[first]][node_ids[second]] = weight
        graph[node_ids[second]][node_ids[first]] = weight

    for index, row in enumerate(neighbor_rows):
        selected = [int(item) for item in row if int(item) != index][:neighbor_count]
        for neighbor in selected:
            connect(index, neighbor)

    # A longitude-ordered spanning chain guarantees connectivity without a dense graph.
    ordered_nodes = sorted(range(1, len(points)), key=lambda index: (points[index][1], points[index][0], index))
    chain = [0, *ordered_nodes]
    for first, second in zip(chain, chain[1:]):
        connect(first, second)
    return graph, candidate_nodes


def calculate_route_distances(
    destination_text: str,
    candidates: Sequence[Mapping[str, Any]],
    neighbor_count: int = GRAPH_NEIGHBORS,
) -> Tuple[Tuple[float, float], bool, List[float]]:
    resolved_coordinates, resolved = resolve_destination(destination_text)
    reference = resolved_coordinates if resolved else _candidate_center(candidates)
    graph, candidate_nodes = _build_sparse_graph(reference, candidates, neighbor_count)
    distances = _dijkstra(graph, "destination")
    route_distances = []
    for index, candidate in enumerate(candidates):
        coordinate = _normalize_coordinates(candidate.get("coordinates"), reference)
        route_distance = distances.get(candidate_nodes[index], math.inf)
        if not math.isfinite(route_distance):
            route_distance = _haversine_km(reference, coordinate) * ROAD_DETOUR_FACTOR
        route_distances.append(route_distance)
    return reference, resolved, route_distances


def _candidate_free_spaces(candidate: Mapping[str, Any]) -> Optional[int]:
    capacity = candidate.get("totalCapacity", candidate.get("total_capacity"))
    occupied = candidate.get("predictedOccupiedSpaces", candidate.get("predicted_occupied_spaces"))
    free = candidate.get("predictedFreeSpaces", candidate.get("predicted_free_spaces"))
    if type(capacity) is not int or capacity < 0:
        return None
    if free is not None:
        if type(free) is not int or free < 0 or free > capacity:
            return None
        if occupied is not None and (type(occupied) is not int or occupied + free != capacity):
            return None
        return free
    if type(occupied) is not int or occupied < 0 or occupied > capacity:
        return None
    return capacity - occupied


def _weight(constraints: Optional[Mapping[str, Any]], key: str, default: float) -> float:
    try:
        value = float((constraints or {}).get(key, default))
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) and 0 <= value <= 1 else default


def rank_parking_candidates(request: Mapping[str, Any]) -> Dict[str, Any]:
    """Rank by a weighted 0-1 availability/proximity score after Dijkstra routing."""
    destination_text = str(request.get("destination") or "")
    candidates = list(request.get("candidates") or [])
    constraints = request.get("constraints")
    if not candidates:
        _, resolved = resolve_destination(destination_text)
        return {
            "rankedOptions": [],
            "algorithm": "dijkstra-multi-criteria",
            "engineSource": "graph-engine-v1",
            "routingMetadata": {"destinationResolved": resolved},
        }

    availability_weight = _weight(constraints, "availabilityWeight", AVAILABILITY_WEIGHT)
    proximity_weight = _weight(constraints, "proximityWeight", PROXIMITY_WEIGHT)
    weight_total = availability_weight + proximity_weight
    if weight_total == 0:
        availability_weight, proximity_weight = AVAILABILITY_WEIGHT, PROXIMITY_WEIGHT
        weight_total = availability_weight + proximity_weight
    availability_weight /= weight_total
    proximity_weight /= weight_total
    try:
        neighbors = int((constraints or {}).get("graphNeighbors", GRAPH_NEIGHBORS))
    except (TypeError, ValueError):
        neighbors = GRAPH_NEIGHBORS
    neighbors = max(1, min(neighbors, 12))

    reference, resolved, route_distances = calculate_route_distances(
        destination_text, candidates, neighbors
    )
    ranked = []
    max_distance = (constraints or {}).get("maxWalkingDistanceKm")
    try:
        max_distance = float(max_distance) if max_distance is not None else None
    except (TypeError, ValueError):
        max_distance = None
    for index, candidate in enumerate(candidates):
        capacity = candidate.get("totalCapacity", candidate.get("total_capacity"))
        free = _candidate_free_spaces(candidate)
        if free is None or type(capacity) is not int:
            continue
        coordinate = _normalize_coordinates(candidate.get("coordinates"), reference)
        route_distance = route_distances[index]
        if max_distance is not None and route_distance > max_distance:
            continue
        availability = free / capacity if capacity else 0.0
        proximity = 1.0 / (1.0 + route_distance)
        score = availability_weight * availability + proximity_weight * proximity
        output = {
            "id": str(candidate.get("id", "")),
            "name": str(candidate.get("name") or f"Parking {candidate.get('id', '')}"),
            "totalCapacity": capacity,
            "predictedOccupiedSpaces": capacity - free,
            "predictedFreeSpaces": free,
            "distanceKm": round(route_distance, 1),
            "coordinates": list(coordinate),
            "coordinateSource": candidate.get("coordinateSource", candidate.get("coordinate_source", "simulated-development")),
            "dataSource": candidate.get("dataSource", candidate.get("data_source", "simulated-development")),
        }
        ranked.append((score, output))

    ranked.sort(key=lambda item: (item[1]["predictedFreeSpaces"] == 0, -item[0], item[1]["id"]))
    ranked_options = []
    for _, option in ranked:
        if option["predictedFreeSpaces"] == 0:
            status = "Full at arrival"
        elif not any(item["predictedFreeSpaces"] > 0 for item in ranked_options):
            status = "Recommended"
        else:
            status = "Alternative option"
        explanation = (
            f"Weighted score: {availability_weight:.1f} availability and "
            f"{proximity_weight:.1f} proximity; {option['predictedFreeSpaces']} spaces free "
            f"and {option['distanceKm']} km from destination."
        )
        if not resolved:
            explanation += f" Destination not recognised; distances are measured from candidate-set centre ({reference[0]:.4f}, {reference[1]:.4f})."
        ranked_options.append({
            **option,
            "recommendationStatus": status,
            "recommendationExplanation": explanation,
        })

    return {
        "rankedOptions": ranked_options,
        "algorithm": "dijkstra-multi-criteria",
        "engineSource": "graph-engine-v1",
        "routingMetadata": {
            "graphNodeCount": len(candidates) + 1,
            "destinationResolved": resolved,
            "distanceRule": "Dijkstra shortest path on a sparse k-nearest-neighbour graph; haversine edge weights multiplied by ROAD_DETOUR_FACTOR",
            "scoreFormula": f"{availability_weight:.1f} * (predicted_free_spaces / total_capacity) + {proximity_weight:.1f} * (1 / (1 + route_distance_km))",
        },
    }
