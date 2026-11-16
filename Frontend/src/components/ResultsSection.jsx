import { AlertCircle, Route } from "lucide-react";
import ParkingCard from "./ParkingCard.jsx";
import ParkingMap from "./ParkingMap.jsx";

function ResultsSection({
  criteria,
  status,
  results = [],
  error,
  onRetry,
  facilities = [],
  selectedParkingId,
  onSelectParking,
}) {
  const topResult = results[0];
  return (
    <section className="view-section" aria-label="Recommendation results">
      {status === "loading" ? (
        <div className="panel state-panel" role="status">
          <span className="loading-indicator" />
          <div><strong>Finding your best route</strong><p>Checking current simulated availability at each compatible facility.</p></div>
        </div>
      ) : status === "error" ? (
        <div className="panel state-panel error-state" role="alert">
          <AlertCircle size={22} />
          <div><strong>Recommendations unavailable</strong><p>{error}</p></div>
          <button className="button button-secondary" type="button" onClick={onRetry}>Try again</button>
        </div>
      ) : status === "success" && results.length === 0 ? (
        <div className="panel empty-state" role="status">
          <Route size={26} />
          <h2>No compatible spaces available</h2>
          <p>All facilities are full or do not accept this vehicle type. Try another vehicle or check again after a simulated exit.</p>
        </div>
      ) : (
        <>
          {status === "success" && (
            <div className="results-summary panel">
              <div className="summary-icon"><Route size={19} /></div>
              <div>
                <strong>{results.length} recommendation{results.length === 1 ? "" : "s"} found</strong>
                <span>Ranked by availability and combined route distance</span>
              </div>
              <span className="summary-destination">{criteria?.destination}</span>
            </div>
          )}
          {topResult && (
            <ParkingMap
              facilities={facilities}
              routePath={topResult.routePath}
              selectedParkingId={selectedParkingId || topResult.id}
              onSelect={onSelectParking}
            />
          )}
          {status === "success" && (
            <div className="parking-card-list" aria-label="Ranked parking recommendations">
              {results.map((parking, index) => (
                <ParkingCard
                  key={parking.id}
                  parking={parking}
                  rank={index + 1}
                  isSelected={parking.id === selectedParkingId}
                  onSelect={onSelectParking}
                />
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}

export default ResultsSection;
