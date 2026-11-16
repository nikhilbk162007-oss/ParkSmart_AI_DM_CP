import { Activity, ArrowRight, CarFront, CircleParking, ParkingSquare } from "lucide-react";
import ParkingMap from "./ParkingMap.jsx";

function sumFacilityValue(facilities, value) {
  return facilities.reduce((sum, facility) => sum + (Number.isFinite(value(facility)) ? value(facility) : 0), 0);
}

function DashboardOverview({ facilities, loading, error, onRetry, onNavigate, selectedParkingId, onSelectParking, showSimulationControl }) {
  const capacity = sumFacilityValue(facilities, (facility) => facility.totalCapacity);
  const occupied = sumFacilityValue(facilities, (facility) => facility.currentOccupancy?.occupiedSpaces);
  const available = sumFacilityValue(facilities, (facility) => facility.availableSpaces);
  const occupancyRate = capacity ? Math.round((occupied / capacity) * 100) : 0;
  const hasData = facilities.length > 0;

  return (
    <section className="view-section" aria-labelledby="dashboard-title">
      <div className="page-heading dashboard-heading">
        <div>
          <p className="eyebrow">UNIVERSITY CAMPUS · PARKING OPERATIONS</p>
          <h1 id="dashboard-title">Campus dashboard</h1>
          <p className="page-subtitle">Campus capacity and vehicle counts from backend facility records.</p>
        </div>
        <span className="simulated-pill"><span /> SIMULATION ACTIVE</span>
      </div>

      <div className="welcome-strip">
        <div className="welcome-mark"><CircleParking size={22} /></div>
        <div><strong>Good planning starts here.</strong><span>Review campus capacity or find the best route to your destination.</span></div>
        <button className="button button-primary" type="button" onClick={() => onNavigate("find")}>
          Find parking <ArrowRight size={16} />
        </button>
      </div>

      {error && (
        <div className="inline-error" role="alert">
          <strong>Facility data unavailable.</strong> {error}
          <button type="button" className="text-button" onClick={onRetry}>Retry</button>
        </div>
      )}

      <div className="metrics-grid" aria-label="Campus parking metrics">
        <article className="metric-card">
          <div className="metric-label"><span>Total capacity</span><ParkingSquare size={17} /></div>
          <strong>{hasData ? capacity.toLocaleString() : "—"}</strong>
          <span className="metric-footnote">{hasData ? `${facilities.length} facilities` : "Waiting for backend"}</span>
        </article>
        <article className="metric-card">
          <div className="metric-label"><span>Currently occupied</span><CarFront size={17} /></div>
          <strong>{hasData ? occupied.toLocaleString() : "—"}</strong>
          <span className="metric-footnote">From simulated vehicle counts</span>
        </article>
        <article className="metric-card metric-card-accent">
          <div className="metric-label"><span>Available spaces</span><Activity size={17} /></div>
          <strong>{hasData ? available.toLocaleString() : "—"}</strong>
          <span className="metric-footnote">Updated from backend records</span>
        </article>
        <article className="metric-card">
          <div className="metric-label"><span>Occupancy rate</span><Activity size={17} /></div>
          <strong>{hasData ? `${occupancyRate}%` : "—"}</strong>
          <div className="mini-progress"><span style={{ width: `${occupancyRate}%` }} /></div>
        </article>
      </div>

      <div className="dashboard-grid">
        <section className="panel facility-comparison" aria-labelledby="facility-comparison-title">
          <div className="panel-heading">
            <div><p className="eyebrow">FACILITY STATUS</p><h2 id="facility-comparison-title">Parking capacity</h2></div>
            <button type="button" className="text-button" onClick={() => onNavigate("details")}>View details <ArrowRight size={14} /></button>
          </div>
          {loading && !hasData ? (
            <p className="subtle-copy">Loading facility records…</p>
          ) : hasData ? (
            <div className="facility-bars">
              {facilities.map((facility) => {
                const facilityOccupied = facility.currentOccupancy?.occupiedSpaces;
                const percent = facility.totalCapacity ? Math.round((facilityOccupied / facility.totalCapacity) * 100) : 0;
                return (
                  <button
                    className="facility-bar-row"
                    type="button"
                    key={facility.id}
                    onClick={() => { onSelectParking(facility.id); onNavigate("details"); }}
                  >
                    <span className="facility-bar-name">{facility.name}<small>{facility.id}</small></span>
                    <span className="facility-bar-track" aria-label={`${percent}% occupied`}><i style={{ width: `${percent}%` }} /></span>
                    <span className="facility-bar-value">{facility.availableSpaces}<small>free</small></span>
                  </button>
                );
              })}
            </div>
          ) : (
            <p className="subtle-copy">Facility comparison will appear when the backend responds.</p>
          )}
        </section>
        <section className="panel overview-note">
          <p className="eyebrow">DATA STATUS</p>
          <div className="data-status-line"><span className="status-dot" /> Simulated campus data</div>
          <p>Occupancy changes when you record a simulated vehicle entry or exit. No sensor feed or real-world campus measurements are connected.</p>
          {showSimulationControl && <button className="button button-secondary" type="button" onClick={() => onNavigate("simulation")}>Open simulation controls</button>}
        </section>
      </div>

      <ParkingMap facilities={facilities} selectedParkingId={selectedParkingId} onSelect={onSelectParking} />
    </section>
  );
}

export default DashboardOverview;
