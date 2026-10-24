import { useMemo, useState } from "react";
import ParkingCard from "./ParkingCard.jsx";

function formatArrivalTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Invalid arrival time"
    : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function ResultsSection({ criteria, results }) {
  const [sortBy, setSortBy] = useState("distance");
  const [maxDistance, setMaxDistance] = useState("");
  const [minPredictedFreeSpaces, setMinPredictedFreeSpaces] = useState("");

  const filteredResults = useMemo(() => {
    const filtered = results.filter((parking) => {
      const withinDistance =
        maxDistance === "" ||
        (Number.isFinite(parking.distanceKm) && parking.distanceKm <= Number(maxDistance));
      const meetsAvailability =
        minPredictedFreeSpaces === "" ||
        (Number.isFinite(parking.predictedFreeSpaces) &&
          parking.predictedFreeSpaces >= Number(minPredictedFreeSpaces));

      return withinDistance && meetsAvailability;
    });

    return filtered.sort((first, second) => {
      if (sortBy === "predicted-free") {
        return (second.predictedFreeSpaces ?? -1) - (first.predictedFreeSpaces ?? -1);
      }
      return (first.distanceKm ?? Number.POSITIVE_INFINITY) -
        (second.distanceKm ?? Number.POSITIVE_INFINITY);
    });
  }, [maxDistance, minPredictedFreeSpaces, results, sortBy]);

  return (
    <section className="results-section" aria-labelledby="results-title">
      <div className="results-heading-row">
        <div>
          <p className="results-eyebrow">DEVELOPMENT PREVIEW</p>
          <h2 id="results-title">Parking options</h2>
          <p className="results-query">
            For <strong>{criteria.destination}</strong>
            <span aria-hidden="true"> · </span>
            Arriving {formatArrivalTime(criteria.arrivalTime)}
          </p>
        </div>
        <span className="results-count" aria-live="polite">
          {filteredResults.length} of {results.length} simulated options
        </span>
      </div>

      <div className="simulation-notice" role="note">
        <strong>Simulated development data</strong>
        <span>
          These sample locations and predicted figures are fictional interface fixtures. They are
          not based on your destination and do not represent live parking availability.
        </span>
      </div>

      <div className="results-toolbar">
        <label className="result-control">
          <span>Sort by</span>
          <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
            <option value="distance">Distance</option>
            <option value="predicted-free">Predicted free spaces</option>
          </select>
        </label>
        <label className="result-control">
          <span>Maximum distance (km)</span>
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
        <div className="parking-card-list" aria-label="Parking options">
          {filteredResults.map((parking) => (
            <ParkingCard key={parking.id} parking={parking} />
          ))}
        </div>
      ) : results.length === 0 ? (
        <div className="results-empty" role="status">
          <h3>No results data to display</h3>
          <p>No parking records were supplied for this view.</p>
        </div>
      ) : (
        <div className="results-empty" role="status">
          <h3>No options match these filters</h3>
          <p>Adjust the distance or predicted availability filters to see the simulated examples.</p>
        </div>
      )}
    </section>
  );
}

export default ResultsSection;
