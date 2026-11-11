from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

DESTINATION_CLUES = {
    "riverfront": (18.5204, 73.8567),
    "market": (18.5314, 73.8446),
    "garden": (18.5074, 73.8077),
    "deccan": (18.5173, 73.8415),
    "shivajinagar": (18.5314, 73.8446),
    "kothrud": (18.5074, 73.8077),
    "pune": (18.5204, 73.8567),
}


def _normalize_coordinates(value: Any, fallback: Tuple[float, float]) -> Tuple[float, float]:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        lat, lon = value[0], value[1]
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            return float(lat), float(lon)
    return fallback


def _haversine_km(coord_a: Tuple[float, float], coord_b: Tuple[float, float]) -> float:
    lat1, lon1 = coord_a
    lat2, lon2 = coord_b
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    segment = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    return radius_km * (2.0 * math.atan2(math.sqrt(segment), math.sqrt(1.0 - segment)))


def _graph_from_destination(destination: str, candidates: Iterable[Mapping[str, Any]]) -> Dict[str, Dict[str, float]]:
    search_key = (destination or "").strip().lower()
    fallback_destination = (18.5204, 73.8567)
    for clue, coord in DESTINATION_CLUES.items():
        if clue in search_key:
            fallback_destination = coord
            break
    candidate_list = list(candidates)
    nodes = {"destination": fallback_destination}
    for candidate in candidate_list:
        candidate_id = str(candidate.get("id") or "unknown")
        coords = _normalize_coordinates(candidate.get("coordinates"), fallback_destination)
        nodes[candidate_id] = coords

    graph: Dict[str, Dict[str, float]] = {node: {} for node in nodes}
    node_ids = list(nodes)
    for index, source in enumerate(node_ids):
        for target in node_ids[index + 1:]:
            distance = _haversine_km(nodes[source], nodes[target])
            if distance <= 0:
                distance = 0.1
            graph[source][target] = distance
            graph[target][source] = distance
    return graph


def _dijkstra(graph: Mapping[str, Mapping[str, float]], start: str) -> Dict[str, float]:
    distances: Dict[str, float] = {node: math.inf for node in graph}
    distances[start] = 0.0
    visited: set[str] = set()
    frontier: List[Tuple[float, str]] = [(0.0, start)]

    while frontier:
        current_distance, current_node = min(frontier, key=lambda item: item[0])
        frontier.remove((current_distance, current_node))
        if current_node in visited:
            continue
        visited.add(current_node)

        for neighbor, weight in graph.get(current_node, {}).items():
            tentative = current_distance + weight
            if tentative < distances.get(neighbor, math.inf):
                distances[neighbor] = tentative
                frontier.append((tentative, neighbor))

    return distances


def _compute_free_spaces(candidate: Mapping[str, Any], fallback_capacity: Optional[int] = None) -> Optional[int]:
    total_capacity = candidate.get("totalCapacity")
    if total_capacity is None:
        total_capacity = candidate.get("total_capacity")
    if total_capacity is None:
        total_capacity = fallback_capacity
    if total_capacity is None:
        return None
    try:
        total_capacity = int(total_capacity)
    except (TypeError, ValueError):
        return None
    if total_capacity < 0:
        return None

    free = candidate.get("predictedFreeSpaces")
    if free is None:
        free = candidate.get("predicted_free_spaces")
    if free is not None:
        try:
            free = int(free)
        except (TypeError, ValueError):
            return None
        if free < 0 or free > total_capacity:
            return None
        return free

    occupied = candidate.get("predictedOccupiedSpaces")
    if occupied is None:
        occupied = candidate.get("predicted_occupied_spaces")
    if occupied is None:
        return None
    try:
        occupied = int(occupied)
    except (TypeError, ValueError):
        return None

    if occupied < 0 or occupied > total_capacity:
        return None
    return total_capacity - occupied


def _constraint_distance(constraints: Optional[Mapping[str, Any]]) -> Optional[float]:
    if not constraints:
        return None
    raw = constraints.get("maxWalkingDistanceKm")
    if raw is None:
        raw = constraints.get("max_walking_distance_km")
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return max(0.0, value)


def rank_parking_candidates(request: Mapping[str, Any]) -> Dict[str, Any]:
    """Rank parking candidates using a documented availability-first, distance-second rule.

    The algorithm computes shortest paths with Dijkstra's algorithm on a weighted graph whose
    edges use route-distance approximations. The ranking score is formally:
        score = (predicted_free_spaces * 10) - distance_km
    Higher scores are preferred. This keeps availability as the primary decision factor and
    uses distance as a secondary tie-breaker, which matches the PRD 4 requirements.
    """
    destination = str(request.get("destination") or "Pune")
    candidates = list(request.get("candidates") or [])
    constraints = request.get("constraints")

    if not candidates:
        return {"rankedOptions": [], "algorithm": "dijkstra-multi-criteria", "engineSource": "graph-engine-v1"}

    graph = _graph_from_destination(destination, candidates)
    route_distances = _dijkstra(graph, "destination")
    max_walk_distance = _constraint_distance(constraints)

    ranked: List[Dict[str, Any]] = []
    for candidate in candidates:
        candidate_id = str(candidate.get("id") or "unknown")
        route_distance = route_distances.get(candidate_id, math.inf)
        if not math.isfinite(route_distance):
            route_distance = _haversine_km(
                _normalize_coordinates(candidate.get("coordinates"), (18.5204, 73.8567)),
                DESTINATION_CLUES.get((destination or "").strip().lower(), (18.5204, 73.8567)),
            )

        if max_walk_distance is not None and route_distance > max_walk_distance:
            continue

        free_spaces = _compute_free_spaces(candidate)
        if free_spaces is None or free_spaces <= 0:
            continue

        option = {
            "id": str(candidate.get("id")),
            "name": str(candidate.get("name") or f"Parking {candidate_id}"),
            "totalCapacity": int(candidate.get("totalCapacity") or candidate.get("total_capacity") or 0),
            "predictedOccupiedSpaces": int(candidate.get("predictedOccupiedSpaces") or candidate.get("predicted_occupied_spaces") or 0),
            "predictedFreeSpaces": free_spaces,
            "distanceKm": round(route_distance, 1),
            "coordinates": list(candidate.get("coordinates") or [18.5204, 73.8567]),
            "coordinateSource": candidate.get("coordinateSource") or candidate.get("coordinate_source") or "simulated-development",
            "dataSource": candidate.get("dataSource") or candidate.get("data_source") or "simulated-development",
        }
        score = (free_spaces * 10.0) - route_distance
        ranked.append({"candidate": option, "score": score})

    ranked.sort(key=lambda item: item["score"], reverse=True)

    ranked_options: List[Dict[str, Any]] = []
    for index, item in enumerate(ranked):
        candidate = item["candidate"]
        status = "Recommended" if index == 0 else "Alternative option"
        explanation = (
            f"Availability-first ranking: {candidate['predictedFreeSpaces']} spaces free and "
            f"{candidate['distanceKm']} km from destination."
        )
        ranked_options.append({
            "id": candidate["id"],
            "name": candidate["name"],
            "totalCapacity": candidate["totalCapacity"],
            "predictedOccupiedSpaces": candidate["predictedOccupiedSpaces"],
            "predictedFreeSpaces": candidate["predictedFreeSpaces"],
            "distanceKm": candidate["distanceKm"],
            "coordinates": candidate["coordinates"],
            "coordinateSource": candidate["coordinateSource"],
            "dataSource": candidate["dataSource"],
            "recommendationStatus": status,
            "recommendationExplanation": explanation,
        })

    return {
        "rankedOptions": ranked_options,
        "algorithm": "dijkstra-multi-criteria",
        "engineSource": "graph-engine-v1",
        "routingMetadata": {
            "graphNodeCount": len(graph),
            "distanceRule": "availability-first, distance-second",
            "scoreFormula": "(predicted_free_spaces * 10) - distance_km",
        },
    }
