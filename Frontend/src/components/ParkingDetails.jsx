import { useMemo } from "react";
import { CarFront, Footprints, ParkingSquare, Route } from "lucide-react";
import ParkingMap from "./ParkingMap.jsx";

function ParkingDetails({ facilities, parkingId, recommendations, onSelectParking }) {
  const facility = facilities.find((item) => item.id === parkingId) || facilities[0];
  const route = useMemo(
    () => recommendations.find((item) => item.id === facility?.id),
    [facility, recommendations],
  );
  const occupancy = facility?.currentOccupancy;
  const occupancyPercent = facility?.totalCapacity
    ? Math.round((occupancy.occupiedSpaces / facility.totalCapacity) * 100)
    : 0;

  return (
    <section className="view-section" aria-labelledby="details-title">
      <div className="page-heading">
        <div><p className="eyebrow">FACILITY PROFILE</p><h1 id="details-title">Parking details</h1><p className="page-subtitle">Occupancy and compatibility from the backend facility record.</p></div>
        <span className="simulated-pill"><span /> SIMULATED FACILITY DATA</span>
      </div>
      {!facility ? (
        <div className="panel empty-state"><ParkingSquare size={25} /><h2>No facility data</h2><p>Connect to the backend to view parking details.</p></div>
      ) : (
        <>
          <div className="detail-selector-row">
            <label className="form-field"><span>Select facility</span><select aria-label="Facility details" value={facility.id} onChange={(event) => onSelectParking(event.target.value)}>{facilities.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.id}</option>)}</select></label>
            <span className="simulated-tag">SIMULATED</span>
          </div>
          <div className="details-layout">
            <section className="panel facility-profile">
              <div className="profile-header"><span className="profile-icon"><ParkingSquare size={22} /></span><div><h2>{facility.name}</h2><span className="facility-id">{facility.id} · {facility.dataSource}</span></div></div>
              <div className="profile-capacity">
                <div><span className="detail-label">AVAILABLE SPACES</span><strong>{facility.availableSpaces}</strong></div>
                <div><span className="detail-label">TOTAL CAPACITY</span><strong>{facility.totalCapacity}</strong></div>
                <div><span className="detail-label">OCCUPANCY</span><strong>{occupancyPercent}%</strong></div>
              </div>
              <div className="occupancy-progress" role="progressbar" aria-label="Facility occupancy" aria-valuemin={0} aria-valuemax={100} aria-valuenow={occupancyPercent}><span style={{ width: `${occupancyPercent}%` }} /></div>
              <div className="detail-section">
                <h3>Occupancy by vehicle</h3>
                {(facility.acceptedVehicleTypes || []).map((type) => (
                  <div className="vehicle-count-row" key={type}>
                    <span><CarFront size={15} />{type === "two-wheeler" ? "Two-wheeler" : "Car"}</span>
                    <strong>{occupancy?.vehicleCounts?.[type] ?? 0}</strong>
                  </div>
                ))}
              </div>
              <div className="detail-section">
                <h3>Accepted vehicles</h3>
                <div className="vehicle-tags">{facility.acceptedVehicleTypes.map((type) => <span className="vehicle-tag" key={type}>{type === "two-wheeler" ? "Two-wheeler" : "Car"}</span>)}</div>
              </div>
              <p className="detail-data-note">Simulated values · not live sensor measurements</p>
            </section>
            <section className="panel route-profile">
              <p className="eyebrow">ROUTE DETAILS</p>
              <h2>{route ? `Route from ${route.entryGate === "gate_south" ? "South Gate" : "North Gate"}` : "No route selected"}</h2>
              {route ? (
                <>
                  <div className="route-info-row"><span><CarFront size={16} /> Gate to parking</span><strong>{route.routeDistanceMeters} m</strong></div>
                  <div className="route-info-row"><span><Footprints size={16} /> Parking to destination</span><strong>{route.walkingDistanceMeters} m</strong></div>
                  <div className="route-info-row route-total"><span><Route size={16} /> Combined distance</span><strong>{route.totalDistanceMeters} m</strong></div>
                  <p className="route-destination">Destination: {route.destination.replace("dest_", "").replaceAll("_", " ")}</p>
                  <div className="route-node-list">{route.routePath.map((node, index) => <span key={`${node}-${index}`}>{index > 0 && <i aria-hidden="true" />}<b>{node}</b></span>)}</div>
                </>
              ) : <p className="subtle-copy">Run a parking search to see route distances and node sequence for this facility.</p>}
            </section>
          </div>
          <ParkingMap facilities={facilities} routePath={route?.routePath || []} selectedParkingId={facility.id} onSelect={onSelectParking} />
        </>
      )}
    </section>
  );
}

export default ParkingDetails;
