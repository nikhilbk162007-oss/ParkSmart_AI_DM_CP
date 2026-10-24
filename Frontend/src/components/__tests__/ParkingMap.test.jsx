import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { parkingFixtures } from "../../data/parkingFixtures.js";
import ParkingMap, {
  INDIA_BOUNDS,
  isIndiaCoordinatePair,
  isValidCoordinatePair,
  PUNE_MAP_CENTER,
} from "../ParkingMap.jsx";

describe("ParkingMap", () => {
  it("renders one labeled marker for each simulated fixture coordinate", () => {
    render(
      <ParkingMap
        results={parkingFixtures}
        mode="demo"
        selectedParkingId={null}
        onSelect={() => {}}
      />,
    );

    expect(screen.getByRole("region", { name: "Interactive parking map" })).toBeInTheDocument();
    expect(screen.getByText(/demonstration map only/i)).toBeInTheDocument();
    expect(screen.getAllByTestId("parking-map-marker-wrapper")).toHaveLength(
      parkingFixtures.length,
    );
    expect(
      screen.getByRole("button", { name: /Riverfront Parking House, simulated demo marker/i }),
    ).toBeInTheDocument();
    const map = screen.getByTestId("leaflet-map");
    expect(map).toHaveAttribute("data-map-center", JSON.stringify(PUNE_MAP_CENTER));
    expect(map).toHaveAttribute("data-map-zoom", "14");
    expect(map).toHaveAttribute("data-map-bounds", JSON.stringify(INDIA_BOUNDS));
    expect(map).toHaveAttribute("data-map-bounds-viscosity", "1");
  });

  it("keeps every simulated fixture coordinate within India's bounds", () => {
    expect(parkingFixtures.every((parking) => isIndiaCoordinatePair(parking.coordinates))).toBe(
      true,
    );
  });

  it("selects a corresponding parking option when a marker is selected", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();

    render(
      <ParkingMap
        results={parkingFixtures}
        mode="demo"
        selectedParkingId={null}
        onSelect={onSelect}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: /Garden District Parking, simulated demo marker/i }),
    );

    expect(onSelect).toHaveBeenCalledWith("fixture-garden");
  });

  it("shows a fallback rather than crashing when coordinates are missing or invalid", () => {
    render(
      <ParkingMap
        results={[
          { id: "missing-coordinate" },
          { id: "invalid-coordinate", coordinates: [Number.NaN, 500] },
        ]}
        mode="demo"
        selectedParkingId={null}
        onSelect={() => {}}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("Map markers are unavailable");
    expect(screen.getByText(/no valid simulated coordinates/i)).toBeInTheDocument();
    expect(screen.queryByTestId("leaflet-map")).not.toBeInTheDocument();
  });

  it("excludes coordinates outside India from the map", () => {
    render(
      <ParkingMap
        results={[{ id: "outside-india", name: "Outside", coordinates: [51.505, -0.09] }]}
        mode="api"
        selectedParkingId={null}
        onSelect={() => {}}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("Map markers are unavailable");
    expect(screen.queryByTestId("leaflet-map")).not.toBeInTheDocument();
  });

  it.each([
    [[51.5, -0.1], true],
    [[-90, 180], true],
    [[91, 0], false],
    [[0, -181], false],
    [[Number.POSITIVE_INFINITY, 0], false],
    [["51.5", "-0.1"], false],
    [[51.5], false],
    [null, false],
  ])("validates coordinate pair %j", (coordinates, expected) => {
    expect(isValidCoordinatePair(coordinates)).toBe(expected);
  });

  it.each([
    [[18.5204, 73.8567], true],
    [[6.5, 68.1], true],
    [[35.7, 97.4], true],
    [[51.505, -0.09], false],
    [[18.5, 97.5], false],
    [[5.9, 73.8], false],
  ])("checks India coordinate bounds for %j", (coordinates, expected) => {
    expect(isIndiaCoordinatePair(coordinates)).toBe(expected);
  });
});
