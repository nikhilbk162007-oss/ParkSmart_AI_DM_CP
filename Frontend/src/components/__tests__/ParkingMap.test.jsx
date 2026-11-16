import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ParkingMap from "../ParkingMap.jsx";

const facilities = [{
  id: "P1",
  name: "North Parking",
  totalCapacity: 50,
  availableSpaces: 35,
  currentOccupancy: { occupiedSpaces: 15 },
}];

describe("ParkingMap schematic", () => {
  it("shows all campus landmarks and clearly labels its presentation-only layout", () => {
    render(<ParkingMap facilities={facilities} />);
    expect(screen.getByRole("region", { name: "Interactive schematic campus map" })).toBeInTheDocument();
    for (const label of [
      "North Gate", "South Gate", "Library", "Academic Block", "Canteen",
      "Auditorium", "Sports Complex", "North Parking", "Library Parking",
      "South Parking", "Sports Parking",
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(screen.getAllByText(/not geographically accurate/i).length).toBeGreaterThan(0);
    expect(screen.getByText("120 m")).toBeInTheDocument();
  });

  it("highlights route graph edges and allows selecting a facility", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const { container } = render(
      <ParkingMap
        facilities={facilities}
        routePath={["gate_north", "road_north", "P1"]}
        selectedParkingId="P1"
        onSelect={onSelect}
      />,
    );
    expect(container.querySelectorAll(".campus-road.is-route")).toHaveLength(2);
    await user.click(screen.getByRole("button", { name: /North Parking: 35 available/i }));
    expect(onSelect).toHaveBeenCalledWith("P1");
  });
});
