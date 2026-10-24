import { useMemo, useState } from "react";
import ParkingCard from "./ParkingCard.jsx";
import ParkingMap from "./ParkingMap.jsx";

function formatArrivalTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Invalid arrival time"
    : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function isNonNegativeFiniteNumber(value) {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

function isValidSpaceCount(value) {
  return Number.isInteger(value) && isNonNegativeFiniteNumber(value);
}

function ResultsSection({ criteria, mode, status, results, error, onRetry }) {
  const [sortBy, setSortBy] = useState("distance");
  const [maxDistance, setMaxDistance] = useState("");
  const [minPredictedFreeSpaces, setMinPredictedFreeSpaces] = useState("");
  const [selectedParkingId, setSelectedParkingId] = useState(null);

  const filteredResults = useMemo(() => {
    const filtered = results.filter((parking) => {
      const withinDistance =
        maxDistance === "" ||
        (isNonNegativeFiniteNumber(parking.distanceKm) &&
          parking.distanceKm <= Number(maxDistance));
      const meetsAvailability =
        minPredictedFreeSpaces === "" ||
        (isValidSpaceCount(parking.predictedFreeSpaces) &&
          parking.predictedFreeSpaces >= Number(minPredictedFreeSpaces));

      return withinDistance && meetsAvailability;
    });

    return filtered.sort((first, second) => {
      if (sortBy === "predicted-free") {
        const firstHasCount = isValidSpaceCount(first.predictedFreeSpaces);
        const secondHasCount = isValidSpaceCount(second.predictedFreeSpaces);
        if (firstHasCount !== secondHasCount) {
          return firstHasCount ? -1 : 1;
        }
        return firstHasCount ? second.predictedFreeSpaces - first.predictedFreeSpaces : 0;
      }
      const firstHasDistance = isNonNegativeFiniteNumber(first.distanceKm);
      const secondHasDistance = isNonNegativeFiniteNumber(second.distanceKm);
      if (firstHasDistance !== secondHasDistance) {
        return firstHasDistance ? -1 : 1;
      }
      return firstHasDistance ? first.distanceKm - second.distanceKm : 0;
    });
  }, [maxDistance, minPredictedFreeSpaces, results, sortBy]);

  const visibleSelectedParkingId = filteredResults.some(
    (parking) => parking.id === selectedParkingId,
  )
    ? selectedParkingId
    : null;
  const hasRecommendedOption = results.some(
    (parking) =>
      typeof parking.recommendationStatus === "string" &&
      parking.recommendationStatus.trim().toLowerCase() === "recommended",
  );

  return (
    <section className="results-section" aria-labelledby="results-title">
      <div className="results-heading-row">
        <div>
          <p className="results-eyebrow">
            {mode === "demo" ? "DEVELOPMENT PREVIEW" : "API MODE"}
          </p>
          <h2 id="results-title">Parking options</h2>
          <p className="results-query">
            For <strong>{criteria.destination}</strong>
            <span aria-hidden="true"> · </span>
            Arriving {formatArrivalTime(criteria.arrivalTime)}
          </p>
        </div>
        {status === "success" && (
          <span className="results-count" aria-live="polite">
            {mode === "demo"
              ? `${filteredResults.length} of ${results.length} simulated options`
              : `${filteredResults.length} ${filteredResults.length === 1 ? "option" : "options"}`}
          </span>
        )}
      </div>

      {mode === "demo" && (
        <div className="simulation-notice" role="note">
          <strong>Simulated development data</strong>
          <span>
            These sample locations and predicted figures are fictional interface fixtures. They are
            not based on your destination and do not represent live parking availability.
          </span>
        </div>
      )}

      {status === "loading" ? (
        <div className="results-message" role="status" aria-live="polite">
          <span className="loading-indicator" aria-hidden="true" />
          <span>Loading parking results…</span>
        </div>
      ) : status === "error" ? (
        <div className="results-error" role="alert">
          <div>
            <h3>Parking results could not be loaded</h3>
            <p>{error}</p>
          </div>
          <button className="retry-button" type="button" onClick={onRetry}>
            Try again
          </button>
        </div>
      ) : (
        <>
          <div className="results-toolbar">
            <label className="result-control">
              <span>Sort by</span>
              <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
                <option value="distance">Reported distance</option>
                <option value="predicted-free">Predicted free spaces</option>
              </select>
            </label>
            <label className="result-control">
              <span>Maximum reported distance (km)</span>
              <input
                type="number"
                min="0"
                step="0.1"
                inputMode="decimal"
                value={maxDistance}
                onChange={(event) => setMaxDistance(event.target.value)}
                placeholder="Any distance"
              />
            </label>
            <label className="result-control">
              <span>Minimum predicted free spaces</span>
              <input
                type="number"
                min="0"
                step="1"
                inputMode="numeric"
                value={minPredictedFreeSpaces}
                onChange={(event) => setMinPredictedFreeSpaces(event.target.value)}
                placeholder="Any availability"
              />
            </label>
          </div>

          {filteredResults.length > 0 ? (
            <>
              <ParkingMap
                results={filteredResults}
                mode={mode}
                selectedParkingId={visibleSelectedParkingId}
                onSelect={setSelectedParkingId}
              />
              <div className="parking-card-list" aria-label="Parking options">
                {filteredResults.map((parking) => (
                  <ParkingCard
                    key={parking.id}
                    parking={parking}
                    mode={mode}
                    hasRecommendedOption={hasRecommendedOption}
                    isSelected={parking.id === visibleSelectedParkingId}
                    onSelect={setSelectedParkingId}
                  />
                ))}
              </div>
            </>
          ) : results.length === 0 ? (
            <div className="results-empty" role="status">
              <h3>No parking options found</h3>
              <p>There are no results to display for this search.</p>
            </div>
          ) : (
            <div className="results-empty" role="status">
              <h3>No options match these filters</h3>
              <p>
                Adjust the distance or predicted availability filters to see the available
                options.
              </p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

export default ResultsSection;
