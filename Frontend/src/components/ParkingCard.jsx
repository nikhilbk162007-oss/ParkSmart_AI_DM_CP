import { MapPin, ParkingSquare } from "lucide-react";

function isNonNegativeFiniteNumber(value) {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

function formatSpaces(value, capacity) {
  if (value === null || value === undefined) {
    return "Not provided";
  }
  if (!Number.isInteger(value) || !isNonNegativeFiniteNumber(value)) {
    return "Invalid value";
  }
  if (isNonNegativeFiniteNumber(capacity) && value > capacity) {
    return "Inconsistent data";
  }
  return `${value} spaces`;
}

function getOccupancy(parking) {
  const { totalCapacity, predictedOccupiedSpaces, predictedFreeSpaces } = parking;
  const hasCapacity = isNonNegativeFiniteNumber(totalCapacity);
  const hasOccupied = predictedOccupiedSpaces !== null && predictedOccupiedSpaces !== undefined;
  const hasFree = predictedFreeSpaces !== null && predictedFreeSpaces !== undefined;
  const occupiedIsValid =
    Number.isInteger(predictedOccupiedSpaces) &&
    isNonNegativeFiniteNumber(predictedOccupiedSpaces) &&
    hasCapacity &&
    predictedOccupiedSpaces <= totalCapacity;
  const freeIsValid =
    Number.isInteger(predictedFreeSpaces) &&
    isNonNegativeFiniteNumber(predictedFreeSpaces) &&
    hasCapacity &&
    predictedFreeSpaces <= totalCapacity;

  if (
    hasOccupied &&
    hasFree &&
    occupiedIsValid &&
    freeIsValid &&
    predictedOccupiedSpaces + predictedFreeSpaces !== totalCapacity
  ) {
    return { status: "inconsistent" };
  }

  if (!hasCapacity || !hasOccupied || !occupiedIsValid) {
    return { status: "unavailable" };
  }

  if (totalCapacity === 0) {
    return { status: "zero-capacity" };
  }

  return {
    status: "valid",
    percentage: (predictedOccupiedSpaces / totalCapacity) * 100,
  };
}

function formatDistance(value) {
  if (value === null || value === undefined) {
    return "Not provided";
  }
  if (!isNonNegativeFiniteNumber(value)) {
    return "Invalid value";
  }
  return `${value} km`;
}

function textValue(value) {
  return typeof value === "string" && value.trim() ? value.trim() : "Not provided";
}

function isRecommendedStatus(value) {
  return typeof value === "string" && value.trim().toLowerCase() === "recommended";
}

function ParkingCard({ parking, mode, isSelected, onSelect, hasRecommendedOption = false }) {
  const option =
    parking && typeof parking === "object" && !Array.isArray(parking) ? parking : {};
  const name = textValue(option.name);
  const recommendationStatus = textValue(option.recommendationStatus);
  const recommendationExplanation = textValue(option.recommendationExplanation);
  const isRecommended = isRecommendedStatus(option.recommendationStatus);
  const isAlternative = hasRecommendedOption && !isRecommended;
  const hasPrediction =
    option.predictedFreeSpaces !== null && option.predictedFreeSpaces !== undefined;
  const occupancy = getOccupancy(option);
  const capacityText = formatSpaces(option.totalCapacity);
  const occupiedText = formatSpaces(option.predictedOccupiedSpaces, option.totalCapacity);
  const freeText = formatSpaces(option.predictedFreeSpaces, option.totalCapacity);
  const distanceText = formatDistance(option.distanceKm);
  const roundedOccupancy =
    occupancy.status === "valid" ? Math.round(occupancy.percentage * 10) / 10 : null;
  const occupancyText =
    occupancy.status === "valid"
      ? `Predicted occupancy: ${roundedOccupancy}%, ${occupiedText} out of ${capacityText}`
      : occupancy.status === "zero-capacity"
        ? "Occupancy percentage unavailable because capacity is zero."
        : occupancy.status === "inconsistent"
          ? "Occupancy percentage unavailable because capacity and predicted counts are inconsistent."
          : "Occupancy percentage unavailable because valid capacity and predicted occupied spaces were not provided.";

  return (
    <article
      className={`parking-card${isSelected ? " is-selected" : ""}${isRecommended ? " is-recommended" : ""}`}
    >
      <div className="parking-card-heading">
        <div className="parking-card-icon" aria-hidden="true">
          <ParkingSquare size={20} strokeWidth={1.8} />
        </div>
        <div className="parking-card-title">
          <h3>{name === "Not provided" ? "Parking location" : name}</h3>
          {mode === "demo" && <span className="simulated-tag">Simulated</span>}
          {isRecommended && <span className="recommendation-tag">Recommended</span>}
          {isAlternative && <span className="alternative-tag">Alternative option</span>}
        </div>
      </div>

      <dl className="parking-card-details">
        <div className="parking-detail parking-detail-capacity">
          <dt>Total capacity</dt>
          <dd>{capacityText}</dd>
        </div>
        <div className="parking-detail parking-detail-occupied">
          <dt>Predicted occupied spaces</dt>
          <dd>{occupiedText}</dd>
        </div>
        <div className="parking-detail parking-detail-free">
          <dt>Predicted free spaces</dt>
          <dd>
            {freeText}
            {hasPrediction && freeText.endsWith("spaces") && (
              <span className="prediction-tag">Predicted</span>
            )}
          </dd>
        </div>
        <div className="parking-detail parking-detail-distance">
          <dt>Reported distance</dt>
          <dd>{distanceText}</dd>
        </div>
      </dl>

      <div className="occupancy-summary">
        <div className="occupancy-summary-heading">
          <span>Predicted occupancy · not current occupancy</span>
          {roundedOccupancy !== null && <strong>{roundedOccupancy}%</strong>}
        </div>
        {occupancy.status === "valid" ? (
          <>
            <div
              className="occupancy-progress"
              role="progressbar"
              aria-label="Predicted occupancy"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={roundedOccupancy}
              aria-valuetext={occupancyText}
            >
              <span style={{ width: `${occupancy.percentage}%` }} />
            </div>
            <p className="occupancy-description">{occupancyText}</p>
          </>
        ) : (
          <p className="occupancy-unavailable">{occupancyText}</p>
        )}
      </div>

      <div className="parking-card-recommendation">
        <p>
          <span>Recommendation status</span>
          <strong>{recommendationStatus}</strong>
        </p>
        <p>
          <span>Recommendation explanation</span>
          <strong>{recommendationExplanation}</strong>
        </p>
      </div>
      {mode === "demo" && (
        <p className="parking-card-location">
          <MapPin size={14} aria-hidden="true" />
          Sample location · not geocoded
        </p>
      )}
      <button
        className="parking-card-select"
        type="button"
        aria-pressed={isSelected}
        disabled={
          !(
            (typeof option.id === "string" && option.id.trim()) ||
            (typeof option.id === "number" && Number.isFinite(option.id))
          )
        }
        onClick={() => onSelect?.(option.id)}
      >
        {isSelected ? "Selected on map" : "Show on map"}
      </button>
    </article>
  );
}

export default ParkingCard;
