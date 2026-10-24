import React from "react";

export function MapContainer({
  children,
  center,
  zoom,
  minZoom,
  maxBounds,
  maxBoundsViscosity,
}) {
  return (
    <div
      data-testid="leaflet-map"
      data-map-center={JSON.stringify(center)}
      data-map-zoom={zoom}
      data-map-min-zoom={minZoom}
      data-map-bounds={JSON.stringify(maxBounds)}
      data-map-bounds-viscosity={maxBoundsViscosity}
    >
      {children}
    </div>
  );
}

export const Marker = React.forwardRef(function Marker(
  { alt, children, eventHandlers, icon, title },
  ref,
) {
  React.useImperativeHandle(ref, () => ({
    closePopup: () => {},
    openPopup: () => {},
  }));

  return (
    <div
      data-testid="parking-map-marker-wrapper"
      data-selected={icon.options.html.includes("is-selected")}
      data-title={title}
    >
      <button type="button" aria-label={alt} onClick={() => eventHandlers?.click?.()}>
        {title}
      </button>
      {children}
    </div>
  );
});

export function Popup({ children }) {
  return <div data-testid="parking-map-popup">{children}</div>;
}

export function TileLayer() {
  return null;
}

export function useMap() {
  return {
    getZoom: () => 14,
    setView: () => {},
  };
}
