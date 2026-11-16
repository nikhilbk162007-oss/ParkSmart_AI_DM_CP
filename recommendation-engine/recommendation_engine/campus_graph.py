"""Fictional university campus road network; edge weights are metres."""

from typing import Dict, Mapping, Tuple


NODE_LABELS: Dict[str, str] = {
    "gate_north": "North Gate",
    "gate_south": "South Gate",
    "road_north": "North Road Junction",
    "road_central": "Central Road Junction",
    "road_south": "South Road Junction",
    "road_library": "Library Road Junction",
    "road_academic": "Academic Road Junction",
    "road_canteen": "Canteen Road Junction",
    "road_auditorium": "Auditorium Road Junction",
    "road_sports": "Sports Road Junction",
    "dest_library": "Library",
    "dest_academic_block": "Academic Block",
    "dest_canteen": "Canteen",
    "dest_auditorium": "Auditorium",
    "dest_sports_complex": "Sports Complex",
    "P1": "North Parking",
    "P2": "Library Parking",
    "P3": "South Parking",
    "P4": "Sports Parking",
}

ENTRY_GATES: Dict[str, str] = {
    "north gate": "gate_north",
    "gate_north": "gate_north",
    "south gate": "gate_south",
    "gate_south": "gate_south",
}

DESTINATIONS: Dict[str, str] = {
    "library": "dest_library",
    "dest_library": "dest_library",
    "academic block": "dest_academic_block",
    "dest_academic_block": "dest_academic_block",
    "canteen": "dest_canteen",
    "dest_canteen": "dest_canteen",
    "auditorium": "dest_auditorium",
    "dest_auditorium": "dest_auditorium",
    "sports complex": "dest_sports_complex",
    "dest_sports_complex": "dest_sports_complex",
}

PARKING_NODES: Tuple[str, ...] = ("P1", "P2", "P3", "P4")

# Each tuple is one undirected road segment: (node ID, node ID, distance in metres).
CAMPUS_ROAD_EDGES: Tuple[Tuple[str, str, int], ...] = (
    ("gate_north", "road_north", 120),
    ("gate_south", "road_south", 100),
    ("road_north", "road_central", 180),
    ("road_central", "road_south", 220),
    ("road_central", "road_library", 100),
    ("road_library", "dest_library", 60),
    ("road_library", "P2", 45),
    ("road_library", "road_academic", 130),
    ("road_academic", "dest_academic_block", 55),
    ("road_academic", "road_canteen", 110),
    ("road_canteen", "dest_canteen", 40),
    ("road_central", "road_canteen", 150),
    ("road_central", "road_auditorium", 150),
    ("road_auditorium", "dest_auditorium", 50),
    ("road_auditorium", "road_sports", 180),
    ("road_sports", "dest_sports_complex", 75),
    ("road_sports", "P4", 65),
    ("road_south", "P3", 45),
    ("road_north", "P1", 50),
)


def build_campus_graph() -> Dict[str, Dict[str, int]]:
    """Build the adjacency map for the predefined undirected campus roads."""
    graph: Dict[str, Dict[str, int]] = {node_id: {} for node_id in NODE_LABELS}
    for first, second, distance_m in CAMPUS_ROAD_EDGES:
        if first not in graph or second not in graph:
            raise ValueError(f"Campus edge references an unknown node: {first}, {second}")
        if type(distance_m) is not int or distance_m <= 0:
            raise ValueError("Campus road distances must be positive integer metres")
        graph[first][second] = distance_m
        graph[second][first] = distance_m
    return graph


CAMPUS_ROAD_GRAPH: Mapping[str, Mapping[str, int]] = build_campus_graph()


def resolve_entry_gate(value: str) -> str:
    try:
        return ENTRY_GATES[value.strip().casefold()]
    except (AttributeError, KeyError) as exc:
        raise ValueError(f"Unknown campus entry gate: {value!r}") from exc


def resolve_destination(value: str) -> str:
    try:
        return DESTINATIONS[value.strip().casefold()]
    except (AttributeError, KeyError) as exc:
        raise ValueError(f"Unknown campus destination: {value!r}") from exc
