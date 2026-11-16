import { useEffect, useMemo, useState } from "react";
import { ArrowDownToLine, ArrowUpFromLine, CarFront, CircleHelp } from "lucide-react";

function SimulationControl({ facilities, busy, feedback, onVehicleEvent }) {
  const [parkingId, setParkingId] = useState(facilities[0]?.id || "");
  const [vehicleType, setVehicleType] = useState("car");
  const facility = facilities.find((item) => item.id === parkingId);
  const acceptedTypes = facility?.acceptedVehicleTypes || [];
  const vehicleCounts = facility?.currentOccupancy?.vehicleCounts || {};
  const canUseVehicle = acceptedTypes.includes(vehicleType);

  useEffect(() => {
    if (!facilities.some((item) => item.id === parkingId) && facilities.length) {
      setParkingId(facilities[0].id);
    }
  }, [facilities, parkingId]);

  useEffect(() => {
    if (acceptedTypes.length && !acceptedTypes.includes(vehicleType)) {
      setVehicleType(acceptedTypes[0]);
    }
  }, [parkingId, acceptedTypes, vehicleType]);

  const occupancyPercent = useMemo(() => {
    if (!facility?.totalCapacity) return 0;
    return Math.round((facility.currentOccupancy.occupiedSpaces / facility.totalCapacity) * 100);
  }, [facility]);

  return (
    <section className="view-section" aria-labelledby="simulation-title">
      <div className="page-heading">
        <div><p className="eyebrow">VEHICLE FLOW SIMULATOR</p><h1 id="simulation-title">Simulation control</h1><p className="page-subtitle">Record a vehicle movement and update facility occupancy.</p></div>
        <span className="simulated-pill"><span /> SIMULATED EVENTS ONLY</span>
      </div>
      <div className="simulation-layout">
        <section className="panel simulation-form-panel">
          <div className="panel-heading">
            <div><p className="eyebrow">CONTROL PANEL</p><h2>Vehicle event</h2></div>
            <span className="simulation-icon"><CarFront size={20} /></span>
          </div>
          <label className="form-field">
            <span>Parking facility</span>
            <select aria-label="Parking facility" value={parkingId} onChange={(event) => setParkingId(event.target.value)} disabled={busy || !facilities.length}>
              {facilities.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.id}</option>)}
            </select>
          </label>
          <label className="form-field">
            <span>Vehicle type</span>
            <select aria-label="Simulation vehicle type" value={vehicleType} onChange={(event) => setVehicleType(event.target.value)} disabled={busy || !facility}>
              <option value="car" disabled={!acceptedTypes.includes("car")}>Car{!acceptedTypes.includes("car") ? " · not accepted" : ""}</option>
              <option value="two-wheeler" disabled={!acceptedTypes.includes("two-wheeler")}>Two-wheeler{!acceptedTypes.includes("two-wheeler") ? " · not accepted" : ""}</option>
            </select>
          </label>
          <div className="event-actions">
            <button type="button" className="button button-primary" disabled={busy || !facility || !canUseVehicle} onClick={() => onVehicleEvent(parkingId, "entry", vehicleType)}>
              <ArrowDownToLine size={17} /> {busy === "entry" ? "Recording…" : "Simulate entry"}
            </button>
            <button type="button" className="button button-secondary" disabled={busy || !facility || !canUseVehicle} onClick={() => onVehicleEvent(parkingId, "exit", vehicleType)}>
              <ArrowUpFromLine size={17} /> {busy === "exit" ? "Recording…" : "Simulate exit"}
            </button>
          </div>
          {feedback && (
            <p className={`event-feedback ${feedback.type}`} role={feedback.type === "error" ? "alert" : "status"}>
              {feedback.message}
            </p>
          )}
          <div className="simulation-disclaimer"><CircleHelp size={15} /><span>Each action records exactly one vehicle using the backend entry/exit API.</span></div>
        </section>
        <section className="panel simulation-current">
          <p className="eyebrow">CURRENT FACILITY STATE</p>
          {facility ? (
            <>
              <h2>{facility.name}</h2>
              <span className="facility-id">{facility.id} · backend simulated record</span>
              <div className="simulation-occupancy">
                <strong>{facility.currentOccupancy.occupiedSpaces}<small> / {facility.totalCapacity}</small></strong>
                <span>spaces occupied</span>
                <div className="occupancy-progress"><span style={{ width: `${occupancyPercent}%` }} /></div>
                <div className="simulation-space-row"><span>Available</span><strong>{facility.availableSpaces}</strong></div>
              </div>
              <div className="vehicle-count-list">
                {facility.acceptedVehicleTypes.map((type) => (
                  <div key={type}><span>{type === "two-wheeler" ? "Two-wheelers" : "Cars"}</span><strong>{vehicleCounts[type] ?? 0}</strong></div>
                ))}
              </div>
            </>
          ) : <p className="subtle-copy">Facility state will appear when backend data is available.</p>}
        </section>
      </div>
    </section>
  );
}

export default SimulationControl;
