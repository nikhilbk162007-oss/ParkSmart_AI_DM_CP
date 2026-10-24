import { useEffect, useMemo, useRef, useState } from "react";
import {
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

export const INDIA_BOUNDS = [
  [6.5, 68.1],
  [35.7, 97.4],
];
export const PUNE_MAP_CENTER = [18.5204, 73.8567];

export function isValidCoordinatePair(coordinates) {
  return (
    Array.isArray(coordinates) &&
    coordinates.length === 2 &&
    Number.isFinite(coordinates[0]) &&
    Number.isFinite(coordinates[1]) &&
    coordinates[0] >= -90 &&
    coordinates[0] <= 90 &&
    coordinates[1] >= -180 &&
    coordinates[1] <= 180
  );
}

export function isIndiaCoordinatePair(coordinates) {
  return (
    isValidCoordinatePair(coordinates) &&
    coordinates[0] >= INDIA_BOUNDS[0][0] &&
    coordinates[0] <= INDIA_BOUNDS[1][0] &&
    coordinates[1] >= INDIA_BOUNDS[0][1] &&
    coordinates[1] <= INDIA_BOUNDS[1][1]
  );
}

function makeParkingIcon(markerNumber, isSelected) {
  return L.divIcon({
    className: "parksmart-marker-icon",
    html: `<span class="parking-map-marker${isSelected ? " is-selected" : ""}"><span>${markerNumber}</span></span>`,
    iconSize: [36, 42],
    iconAnchor: [18, 21],
    popupAnchor: [0, -19],
  });
}

function getParkingName(parking, markerNumber) {
  return typeof parking.name === "string" && parking.name.trim()
    ? parking.name.trim()
    : `Parking option ${markerNumber}`;
}

function MapViewController({ selectedParking }) {
  const map = useMap();

  useEffect(() => {
    if (selectedParking) {
      map.setView(selectedParking.coordinates, map.getZoom(), { animate: false });
    }
  }, [map, selectedParking]);

  return null;
}

function ParkingMarker({ parking, markerNumber, isSelected, onSelect, mode }) {
  const markerRef = useRef(null);
  const name = getParkingName(parking, markerNumber);
  const capacity =
    Number.isInteger(parking.totalCapacity) && parking.totalCapacity >= 0
      ? parking.totalCapacity
      : null;
  useEffect(() => {
    if (isSelected) {
      markerRef.current?.openPopup();
    } else {
      markerRef.current?.closePopup();
    }
  }, [isSelected]);

  const capacityText = capacity === null ? "Not provided" : `${capacity} spaces`;
  const distanceText =
    typeof parking.distanceKm === "number" && Number.isFinite(parking.distanceKm) && parking.distanceKm >= 0
      ? `${parking.distanceKm} km`
      : "Not provided";
  const predictedFreeText =
    Number.isInteger(parking.predictedFreeSpaces) &&
    parking.predictedFreeSpaces >= 0 &&
    (capacity === null || parking.predictedFreeSpaces <= capacity)
      ? `${parking.predictedFreeSpaces} spaces`
      : parking.predictedFreeSpaces === null || parking.predictedFreeSpaces === undefined
        ? "Not provided"
        : "Invalid value";

  return (
    <Marker
      ref={markerRef}
      position={parking.coordinates}
      icon={makeParkingIcon(markerNumber, isSelected)}
      title={name}
      alt={`${name}${mode === "demo" ? ", simulated demo marker" : ""}`}
      keyboard
      eventHandlers={{ click: () => onSelect(parking.id) }}
    >
      <Popup>
        <div className="parking-map-popup">
          {mode === "demo" && <strong className="popup-simulated">Simulated demo option</strong>}
          <strong>{name}</strong>
          <span>Total capacity: {capacityText}</span>
          <span>Predicted free spaces: {predictedFreeText}</span>
          <span>Reported distance: {distanceText}</span>
          {mode === "demo" && <span>Demonstration coordinate only</span>}
        </div>
      </Popup>
    </Marker>
  );
}

function ParkingMap({ results, mode, selectedParkingId, onSelect }) {
  const [tileError, setTileError] = useState(false);
  const mappedParking = useMemo(
    () => results.filter((parking) => isIndiaCoordinatePair(parking.coordinates)),
    [results],
  );
  const selectedParking = mappedParking.find((parking) => parking.id === selectedParkingId);

  useEffect(() => {
    setTileError(false);
  }, [mappedParking]);

  return (
    <section className="parking-map-section" aria-labelledby="parking-map-title">
      <div className="parking-map-heading">
        <div>
          <p className="results-eyebrow">LOCATION OVERVIEW</p>
          <h3 id="parking-map-title">Parking map</h3>
        </div>
        <span>{mappedParking.length} map {mappedParking.length === 1 ? "marker" : "markers"}</span>
      </div>

      {mode === "demo" && (
        <p className="map-simulation-notice" role="note">
          Demonstration map only. Parking options and their coordinates are simulated and do not
          identify verified parking facilities or live availability.
        </p>
      )}

      {mappedParking.length === 0 ? (
        <div className="parking-map-fallback" role="status">
          <strong>Map markers are unavailable</strong>
          <span>
            {mode === "demo"
              ? "No valid simulated coordinates were provided for these demonstration options."
              : "No valid coordinates were provided with these parking results."}
          </span>
        </div>
      ) : tileError ? (
        <div className="parking-map-fallback" role="alert">
          <strong>Map tiles could not be displayed</strong>
          <span>
            The map background is unavailable. Parking options remain available in the results
            list.
          </span>
        </div>
      ) : (
        <div className="parking-map-frame" role="region" aria-label="Interactive parking map">
          <MapContainer
            center={PUNE_MAP_CENTER}
            zoom={14}
            minZoom={5}
            maxBounds={INDIA_BOUNDS}
            maxBoundsViscosity={1}
            scrollWheelZoom={false}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              eventHandlers={{ tileerror: () => setTileError(true) }}
            />
            <MapViewController selectedParking={selectedParking} />
            {mappedParking.map((parking, index) => (
              <ParkingMarker
                key={parking.id}
                parking={parking}
                markerNumber={index + 1}
                isSelected={parking.id === selectedParkingId}
                onSelect={onSelect}
                mode={mode}
              />
            ))}
          </MapContainer>
        </div>
      )}
    </section>
  );
}

export default ParkingMap;
