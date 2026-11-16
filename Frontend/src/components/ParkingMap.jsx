import { useMemo } from "react";

const NODES = {
  gate_north: { label: "North Gate", x: 70, y: 82, kind: "gate" },
  gate_south: { label: "South Gate", x: 845, y: 422, kind: "gate" },
  road_north: { label: "North junction", x: 230, y: 82, kind: "road" },
  road_central: { label: "Central junction", x: 440, y: 226, kind: "road" },
  road_south: { label: "South junction", x: 680, y: 390, kind: "road" },
  road_library: { label: "Library junction", x: 570, y: 100, kind: "road" },
  road_academic: { label: "Academic junction", x: 690, y: 128, kind: "road" },
  road_canteen: { label: "Canteen junction", x: 804, y: 214, kind: "road" },
  road_auditorium: { label: "Auditorium junction", x: 500, y: 326, kind: "road" },
  road_sports: { label: "Sports junction", x: 758, y: 344, kind: "road" },
  dest_library: { label: "Library", x: 570, y: 42, kind: "destination" },
  dest_academic_block: { label: "Academic Block", x: 710, y: 58, kind: "destination" },
  dest_canteen: { label: "Canteen", x: 850, y: 216, kind: "destination" },
  dest_auditorium: { label: "Auditorium", x: 498, y: 390, kind: "destination" },
  dest_sports_complex: { label: "Sports Complex", x: 760, y: 426, kind: "destination" },
  P1: { label: "North Parking", x: 205, y: 140, kind: "parking" },
  P2: { label: "Library Parking", x: 554, y: 160, kind: "parking" },
  P3: { label: "South Parking", x: 614, y: 438, kind: "parking" },
  P4: { label: "Sports Parking", x: 814, y: 322, kind: "parking" },
};

const EDGES = [
  ["gate_north", "road_north", 120], ["gate_south", "road_south", 100],
  ["road_north", "road_central", 180], ["road_central", "road_south", 220],
  ["road_central", "road_library", 100], ["road_library", "dest_library", 60],
  ["road_library", "P2", 45], ["road_library", "road_academic", 130],
  ["road_academic", "dest_academic_block", 55], ["road_academic", "road_canteen", 110],
  ["road_canteen", "dest_canteen", 40], ["road_central", "road_canteen", 150],
  ["road_central", "road_auditorium", 150], ["road_auditorium", "dest_auditorium", 50],
  ["road_auditorium", "road_sports", 180], ["road_sports", "dest_sports_complex", 75],
  ["road_sports", "P4", 65], ["road_south", "P3", 45], ["road_north", "P1", 50],
];

function occupancyColor(facility) {
  const capacity = facility?.totalCapacity;
  const occupied = facility?.currentOccupancy?.occupiedSpaces;
  if (!Number.isFinite(capacity) || capacity <= 0 || !Number.isFinite(occupied)) return "var(--text-muted)";
  const ratio = occupied / capacity;
  return ratio >= 0.9 ? "var(--danger)" : ratio >= 0.7 ? "var(--warning)" : "var(--accent)";
}

function ParkingMap({ facilities = [], routePath = [], selectedParkingId, onSelect }) {
  const facilitiesById = useMemo(
    () => new Map(facilities.map((facility) => [facility.id, facility])),
    [facilities],
  );
  const routeEdges = useMemo(() => {
    const active = new Set();
    for (let index = 1; index < routePath.length; index += 1) {
      active.add([routePath[index - 1], routePath[index]].sort().join("|"));
    }
    return active;
  }, [routePath]);

  return (
    <section className="panel map-panel" aria-labelledby="campus-map-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">CAMPUS OVERVIEW</p>
          <h2 id="campus-map-title">Campus map</h2>
        </div>
        <span className="map-key"><i className="map-key-route" /> Recommended route</span>
      </div>
      <div className="schematic-wrap" role="region" aria-label="Interactive schematic campus map">
        <svg viewBox="0 0 920 500" className="campus-schematic" role="img" aria-labelledby="map-title map-description">
          <title id="map-title">University campus schematic map</title>
          <desc id="map-description">Presentation-only campus layout with two gates, five destinations, four parking facilities and connected roads. Not geographically accurate.</desc>
          <path className="map-campus-boundary" d="M25 35H885V465H25z" />
          <text className="map-map-label" x="42" y="58">UNIVERSITY CAMPUS · SCHEMATIC</text>
          {EDGES.map(([from, to, distance]) => {
            const first = NODES[from];
            const second = NODES[to];
            const highlighted = routeEdges.has([from, to].sort().join("|"));
            const midpointX = (first.x + second.x) / 2;
            const midpointY = (first.y + second.y) / 2;
            return (
              <g key={`${from}-${to}`}>
                <line
                  className={`campus-road${highlighted ? " is-route" : ""}`}
                  x1={first.x} y1={first.y} x2={second.x} y2={second.y}
                />
                <text className="road-distance" x={midpointX + 4} y={midpointY - 5}>{distance} m</text>
              </g>
            );
          })}
          {Object.entries(NODES).map(([id, node]) => {
            if (node.kind === "road") {
              return <circle key={id} className="road-junction" cx={node.x} cy={node.y} r="4" />;
            }
            if (node.kind === "parking") {
              const facility = facilitiesById.get(id);
              const isSelected = selectedParkingId === id;
              const occupied = facility?.currentOccupancy?.occupiedSpaces;
              const available = facility?.availableSpaces;
              const capacity = facility?.totalCapacity;
              return (
                <g
                  key={id}
                  className={`map-node map-parking${isSelected ? " is-selected" : ""}`}
                  role="button"
                  tabIndex={0}
                  aria-label={`${node.label}: ${Number.isInteger(available) ? `${available} available` : "availability unavailable"}`}
                  onClick={() => onSelect?.(id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelect?.(id);
                    }
                  }}
                >
                  <circle cx={node.x} cy={node.y} r="15" className="parking-marker-ring" style={{ stroke: occupancyColor(facility) }} />
                  <text x={node.x} y={node.y + 4} textAnchor="middle" className="parking-marker-id">{id}</text>
                  <text x={node.x} y={node.y + 31} textAnchor="middle" className="map-node-label">{node.label}</text>
                  <text x={node.x} y={node.y + 44} textAnchor="middle" className="map-node-meta">
                    {Number.isInteger(available) && Number.isInteger(capacity) ? `${available}/${capacity} free` : Number.isInteger(occupied) ? `${occupied} occupied` : "—"}
                  </text>
                </g>
              );
            }
            const gate = node.kind === "gate";
            return (
              <g key={id} className={`map-node ${gate ? "map-gate" : "map-destination"}`}>
                <circle cx={node.x} cy={node.y} r={gate ? 10 : 8} />
                <text x={node.x} y={node.y + (gate ? 28 : -14)} textAnchor="middle" className="map-node-label">{node.label}</text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="map-caption">
        <span>Node positions are for presentation only; this schematic is not geographically accurate.</span>
        {routePath.length > 0 && <span className="route-active-label">Route highlighted</span>}
      </div>
    </section>
  );
}

export default ParkingMap;
