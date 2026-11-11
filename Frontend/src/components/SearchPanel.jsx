import { useState } from "react";
import { Clock3, MapPin, Search } from "lucide-react";

function SearchPanel({ onSearch, searchStatus }) {
  const [destination, setDestination] = useState("");
  const [arrivalTime, setArrivalTime] = useState("");
  const [errors, setErrors] = useState({});
  const [capturedCriteria, setCapturedCriteria] = useState(null);

  function handleSubmit(event) {
    event.preventDefault();

    const nextErrors = {};
    const trimmedDestination = destination.trim();

    if (!trimmedDestination) {
      nextErrors.destination = "Enter a destination to continue.";
    }

    if (!arrivalTime || Number.isNaN(new Date(arrivalTime).getTime())) {
      nextErrors.arrivalTime = "Choose a valid arrival date and time.";
    }

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length === 0) {
      const criteria = { destination: trimmedDestination, arrivalTime };
      setCapturedCriteria(criteria);
      onSearch(criteria);
      return;
    }

    setCapturedCriteria(null);
    onSearch(null);
  }

  function handleDestinationChange(event) {
    setDestination(event.target.value);
    setErrors((currentErrors) => ({ ...currentErrors, destination: undefined }));
    setCapturedCriteria(null);
    onSearch(null);
  }

  function handleArrivalTimeChange(event) {
    setArrivalTime(event.target.value);
    setErrors((currentErrors) => ({ ...currentErrors, arrivalTime: undefined }));
    setCapturedCriteria(null);
    onSearch(null);
  }

  return (
    <form
      className="search-panel"
      id="parking-search"
      aria-label="Parking search"
      onSubmit={handleSubmit}
      noValidate
    >
      <div className="search-fields">
        <label className="search-field destination-field">
          <MapPin className="field-icon" size={19} strokeWidth={1.8} aria-hidden="true" />
          <span className="field-content">
            <span className="field-label">YOUR DESTINATION</span>
            <input
              type="text"
              name="destination"
              placeholder="Enter a place or address"
              autoComplete="street-address"
              required
              value={destination}
              onChange={handleDestinationChange}
              aria-invalid={Boolean(errors.destination)}
              aria-describedby={errors.destination ? "destination-error" : undefined}
            />
            {errors.destination && (
              <span className="field-error" id="destination-error" role="alert">
                {errors.destination}
              </span>
            )}
          </span>
        </label>
        <span className="field-divider" aria-hidden="true" />
        <label className="search-field time-field">
          <Clock3 className="field-icon" size={19} strokeWidth={1.8} aria-hidden="true" />
          <span className="field-content">
            <span className="field-label">ARRIVAL TIME</span>
            <input
              type="datetime-local"
              name="arrival-time"
              required
              value={arrivalTime}
              onChange={handleArrivalTimeChange}
              aria-invalid={Boolean(errors.arrivalTime)}
              aria-describedby={errors.arrivalTime ? "arrival-time-error" : undefined}
            />
            {errors.arrivalTime && (
              <span className="field-error" id="arrival-time-error" role="alert">
                {errors.arrivalTime}
              </span>
            )}
          </span>
        </label>
      </div>
      <button className="search-button" type="submit">
        <Search size={17} strokeWidth={2} aria-hidden="true" />
        Find parking
      </button>
      {capturedCriteria ? (
        <p className="search-status search-success" role="status" aria-live="polite">
          {searchStatus === "loading"
            ? `Searching for ${capturedCriteria.destination}…`
            : searchStatus === "success"
              ? `Showing results for ${capturedCriteria.destination}.`
              : searchStatus === "error"
                ? `Could not load results for ${capturedCriteria.destination}.`
                : `Search ready for ${capturedCriteria.destination}.`}
        </p>
      ) : (
        <p className="search-status" aria-live="polite">
          Enter a destination and arrival time to search.
        </p>
      )}
    </form>
  );
}

export default SearchPanel;
