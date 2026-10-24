import { MapPin, ParkingSquare } from "lucide-react";

function formatValue(value, formatter) {
  return value === null || value === undefined ? "Not provided" : formatter(value);
}

function ParkingCard({ parking }) {
  const hasPrediction =
    parking.predictedFreeSpaces !== null && parking.predictedFreeSpaces !== undefined;

  return (
    <article className="parking-card">
      <div className="parking-card-heading">
        <div className="parking-card-icon" aria-hidden="true">
          <ParkingSquare size={20} strokeWidth={1.8} />
        </div>
        <div className="parking-card-title">
          <h3>{parking.name || "Parking location"}</h3>
          <span className="simulated-tag">Simulated</span>
        </div>
      </div>

      <dl className="parking-card-details">
        <div className="parking-detail">
          <dt>Total capacity</dt>
          <dd>{formatValue(parking.totalCapacity, (value) => `${value} spaces`)}</dd>
        </div>
        <div className="parking-detail">
          <dt>Predicted free spaces</dt>
          <dd>
            {formatValue(parking.predictedFreeSpaces, (value) => `${value} spaces`)}
            {hasPrediction && <span className="prediction-tag">Predicted</span>}
          </dd>
        </div>
        <div className="parking-detail">
          <dt>Predicted occupied</dt>
          <dd>{formatValue(parking.predictedOccupiedSpaces, (value) => `${value} spaces`)}</dd>
        </div>
        <div className="parking-detail">
          <dt>Distance</dt>
          <dd>{formatValue(parking.distanceKm, (value) => `${value} km`)}</dd>
        </div>
      </dl>

      <div className="parking-card-recommendation">
        <p>
          <span>Recommendation status</span>
          <strong>{parking.recommendationStatus || "Not provided"}</strong>
        </p>
        <p>
          <span>Why this option</span>
          <strong>{parking.recommendationExplanation || "No explanation provided."}</strong>
        </p>
      </div>
      <p className="parking-card-location">
        <MapPin size={14} aria-hidden="true" />
        Sample location · not geocoded
      </p>
    </article>
  );
}

export default ParkingCard;
