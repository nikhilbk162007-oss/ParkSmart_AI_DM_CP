"""Campus parking filtering and deterministic shortest-route ranking."""

from fractions import Fraction
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .campus_graph import (
    CAMPUS_ROAD_GRAPH,
    NODE_LABELS,
    PARKING_NODES,
    resolve_destination,
    resolve_entry_gate,
)
from .dijkstra import shortest_path


AVAILABILITY_WEIGHT = 0.6
DISTANCE_WEIGHT = 0.4
DISTANCE_SCALE_METERS = 1000


def _candidate_state(
    candidate: Mapping[str, Any], vehicle_type: str
) -> Optional[Tuple[str, str, int, int]]:
    parking_id = candidate.get("id")
    if parking_id not in PARKING_NODES:
        return None

    accepted_types = candidate.get("acceptedVehicleTypes")
    if not isinstance(accepted_types, (list, tuple)) or vehicle_type not in accepted_types:
        return None

    capacity = candidate.get("totalCapacity")
    occupancy = candidate.get("currentOccupancy")
    if type(capacity) is not int or capacity <= 0 or not isinstance(occupancy, Mapping):
        return None
    occupied = occupancy.get("occupiedSpaces")
    if type(occupied) is not int or not 0 <= occupied <= capacity:
        return None
    if sum(
        count for count in (occupancy.get("vehicleCounts") or {}).values()
        if type(count) is int and count >= 0
    ) != occupied:
        return None

    available = capacity - occupied
    if available == 0:
        return None
    return (
        str(parking_id),
        str(candidate.get("name") or NODE_LABELS[parking_id]),
        capacity,
        available,
    )


def recommend_campus_parking(request: Mapping[str, Any]) -> Dict[str, Any]:
    """Rank available compatible campus facilities by capacity and route length."""
    destination_value = request.get("destination")
    gate_value = request.get("entryGate", "gate_north")
    vehicle_type = request.get("vehicleType", "car")
    destination_node = resolve_destination(destination_value)
    gate_node = resolve_entry_gate(gate_value)
    if vehicle_type not in ("car", "two-wheeler"):
        raise ValueError(f"Unsupported vehicle type: {vehicle_type!r}")

    ranked: List[Tuple[Fraction, str, Dict[str, Any]]] = []
    for candidate in request.get("candidates") or []:
        if not isinstance(candidate, Mapping):
            continue
        state = _candidate_state(candidate, vehicle_type)
        if state is None:
            continue
        parking_id, name, capacity, available = state
        route_distance, entry_path = shortest_path(
            CAMPUS_ROAD_GRAPH, gate_node, parking_id
        )
        walking_distance, walking_path = shortest_path(
            CAMPUS_ROAD_GRAPH, parking_id, destination_node
        )
        if route_distance is None or walking_distance is None:
            continue

        total_distance = route_distance + walking_distance
        availability_score = Fraction(available, capacity)
        distance_score = Fraction(
            DISTANCE_SCALE_METERS,
            DISTANCE_SCALE_METERS + int(total_distance),
        )
        score = (
            Fraction(3, 5) * availability_score
            + Fraction(2, 5) * distance_score
        )
        full_path = entry_path + walking_path[1:]
        reason = (
            f"{available} spaces available ({available}/{capacity}); "
            f"{int(route_distance)} m from {NODE_LABELS[gate_node]} and "
            f"{int(walking_distance)} m walk to {NODE_LABELS[destination_node]} "
            f"(combined {int(total_distance)} m; score {float(score):.3f})."
        )
        ranked.append(
            (
                score,
                parking_id,
                {
                    "id": parking_id,
                    "name": name,
                    "totalCapacity": capacity,
                    "availableSpaces": available,
                    "occupiedSpaces": capacity - available,
                    "acceptedVehicleTypes": list(candidate["acceptedVehicleTypes"]),
                    "isSimulated": candidate.get("isSimulated", True),
                    "dataSource": candidate.get("dataSource", "simulated-campus-v1"),
                    "entryGate": gate_node,
                    "destination": destination_node,
                    "routeDistanceMeters": int(route_distance),
                    "walkingDistanceMeters": int(walking_distance),
                    "totalDistanceMeters": int(total_distance),
                    "entryRoutePath": entry_path,
                    "walkingRoutePath": walking_path,
                    "routePath": full_path,
                    "routeDetails": [
                        {
                            "segment": "entry-to-parking",
                            "distanceMeters": int(route_distance),
                            "path": entry_path,
                        },
                        {
                            "segment": "parking-to-destination",
                            "distanceMeters": int(walking_distance),
                            "path": walking_path,
                        },
                    ],
                    "score": round(float(score), 6),
                    "recommendationReason": reason,
                },
            )
        )

    ranked.sort(key=lambda result: (-result[0], result[1]))
    recommendations = []
    for index, (_, _, option) in enumerate(ranked):
        status = "Recommended" if index == 0 else "Alternative option"
        recommendations.append({**option, "recommendationStatus": status})

    return {
        "rankedOptions": recommendations,
        "algorithm": "heap-dijkstra-campus-distance-availability",
        "engineSource": "campus-graph-v1",
        "routingMetadata": {
            "entryGate": gate_node,
            "destination": destination_node,
            "vehicleType": vehicle_type,
            "distanceUnit": "metres",
            "scoreFormula": (
                "0.6 * (availableSpaces / totalCapacity) + "
                "0.4 * (1 / (1 + totalDistanceMeters / 1000))"
            ),
            "availabilityWeight": AVAILABILITY_WEIGHT,
            "distanceWeight": DISTANCE_WEIGHT,
            "distanceScaleMeters": DISTANCE_SCALE_METERS,
            "eligibleFacilityCount": len(recommendations),
        },
    }
