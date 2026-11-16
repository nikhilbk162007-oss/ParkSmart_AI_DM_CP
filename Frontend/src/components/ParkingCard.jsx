import { ArrowUpRight, CarFront, Footprints, ParkingSquare } from "lucide-react";

function ParkingCard({ parking, rank, isSelected, onSelect }) {
  const isRecommended = parking.recommendationStatus === "Recommended";
  const occupiedPercent = parking.totalCapacity
    ? (parking.occupiedSpaces / parking.totalCapacity) * 100
    : 0;
  const supportedVehicles = parking.acceptedVehicleTypes || [];

  return (
    <article
      className={`parking-card${isRecommended ? " is-recommended" : ""}${isSelected ? " is-selected" : ""}`}
      aria-label={`${parking.name}, ${parking.recommendationStatus}`}
    >
      <div className="card-topline">
        <span className={`rank-badge${isRecommended ? " rank-badge-primary" : ""}`}>
          {String(rank).padStart(2, "0")}
        </span>
        <span className={`recommendation-tag${isRecommended ? " tag-primary" : ""}`}>
          {parking.recommendationStatus}
        </span>
        {parking.isSimulated && <span className="simulated-tag">SIMULATED</span>}
      </div>
      <div className="parking-card-title">
        <div className="facility-symbol"><ParkingSquare size={19} /></div>
        <div>
          <h3>{parking.name}</h3>
          <span className="facility-id">{parking.id} · {parking.dataSource || "campus simulation"}</span>
        </div>
        <button
          type="button"
          className="icon-button card-map-button"
          onClick={() => onSelect?.(parking.id)}
          aria-label={`Show ${parking.name} on campus map`}
          aria-pressed={Boolean(isSelected)}
        >
          <ArrowUpRight size={17} />
        </button>
      </div>
      <div className="availability-row">
        <div>
          <strong className="availability-number">{parking.availableSpaces}</strong>
          <span className="availability-label">spaces available</span>
        </div>
        <div className="capacity-count">{parking.occupiedSpaces} occupied <span>/</span> {parking.totalCapacity} total</div>
      </div>
      <div
        className="occupancy-progress"
        role="progressbar"
        aria-label={`${parking.name} occupancy`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(occupiedPercent)}
      >
        <span style={{ width: `${occupiedPercent}%` }} />
      </div>
      <div className="route-stats">
        <div className="route-stat">
          <span className="route-stat-icon"><CarFront size={16} /></span>
          <span><small>Gate to parking</small><strong>{parking.routeDistanceMeters} m</strong></span>
        </div>
        <div className="route-stat">
          <span className="route-stat-icon"><Footprints size={16} /></span>
          <span><small>Walk to destination</small><strong>{parking.walkingDistanceMeters} m</strong></span>
        </div>
      </div>
      <div className="compatibility">
        <span className="detail-label">ACCEPTS</span>
        <div className="vehicle-tags">
          {supportedVehicles.map((vehicle) => (
            <span className="vehicle-tag" key={vehicle}>
              <CarFront size={13} /> {vehicle === "two-wheeler" ? "Two-wheeler" : "Car"}
            </span>
          ))}
        </div>
      </div>
      <p className="recommendation-reason">{parking.recommendationReason}</p>
    </article>
  );
}

export default ParkingCard;
