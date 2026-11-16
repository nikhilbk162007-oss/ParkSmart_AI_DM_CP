import { useState } from "react";
import { ArrowRight, CarFront, MapPin, Signpost } from "lucide-react";

const DESTINATIONS = [
  ["Library", "Library"],
  ["Academic Block", "Academic Block"],
  ["Canteen", "Canteen"],
  ["Auditorium", "Auditorium"],
  ["Sports Complex", "Sports Complex"],
];

function SearchPanel({ onSearch, searchStatus }) {
  const [destination, setDestination] = useState("Library");
  const [entryGate, setEntryGate] = useState("gate_north");
  const [vehicleType, setVehicleType] = useState("car");

  function handleSubmit(event) {
    event.preventDefault();
    onSearch({ destination, entryGate, vehicleType });
  }

  return (
    <form className="search-panel" aria-label="Find campus parking" onSubmit={handleSubmit}>
      <label className="search-field">
        <span className="search-field-icon"><MapPin size={17} /></span>
        <span className="search-field-copy">
          <span className="field-label">DESTINATION</span>
          <select aria-label="Destination" value={destination} onChange={(event) => setDestination(event.target.value)}>
            {DESTINATIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </span>
      </label>
      <label className="search-field">
        <span className="search-field-icon"><Signpost size={17} /></span>
        <span className="search-field-copy">
          <span className="field-label">ENTRY GATE</span>
          <select aria-label="Entry gate" value={entryGate} onChange={(event) => setEntryGate(event.target.value)}>
            <option value="gate_north">North Gate</option>
            <option value="gate_south">South Gate</option>
          </select>
        </span>
      </label>
      <label className="search-field">
        <span className="search-field-icon"><CarFront size={17} /></span>
        <span className="search-field-copy">
          <span className="field-label">VEHICLE TYPE</span>
          <select aria-label="Vehicle type" value={vehicleType} onChange={(event) => setVehicleType(event.target.value)}>
            <option value="car">Car</option>
            <option value="two-wheeler">Two-wheeler</option>
          </select>
        </span>
      </label>
      <button className="button button-primary search-submit" type="submit" disabled={searchStatus === "loading"}>
        {searchStatus === "loading" ? "Searching…" : "Find parking"}
        <ArrowRight size={16} aria-hidden="true" />
      </button>
      <p className="search-status" aria-live="polite">
        {searchStatus === "loading"
          ? "Finding the best available route…"
          : searchStatus === "success"
            ? "Recommendations updated from current simulated occupancy."
            : searchStatus === "error"
              ? "Could not load recommendations. Check the backend connection."
              : "Routes use the fixed campus road network."}
      </p>
    </form>
  );
}

export default SearchPanel;
