import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ParkingCard from "../ParkingCard.jsx";

const parking = {
  id: "P1",
  name: "North Parking",
  totalCapacity: 50,
  availableSpaces: 35,
  occupiedSpaces: 15,
  acceptedVehicleTypes: ["car", "two-wheeler"],
  isSimulated: true,
  dataSource: "simulated-campus-v1",
  routeDistanceMeters: 170,
  walkingDistanceMeters: 390,
  recommendationReason: "35 spaces available; balanced route.",
  recommendationStatus: "Recommended",
};

describe("ParkingCard", () => {
  it("shows occupancy, distances, compatibility and the backend explanation", () => {
    render(<ParkingCard parking={parking} rank={1} />);
    const card = screen.getByRole("article", { name: "North Parking, Recommended" });
    expect(within(card).getByText("35", { selector: ".availability-number" })).toBeInTheDocument();
    expect(within(card).getByText("170 m")).toBeInTheDocument();
    expect(within(card).getByText("390 m")).toBeInTheDocument();
    expect(within(card).getByText("Car")).toBeInTheDocument();
    expect(within(card).getByText("Two-wheeler")).toBeInTheDocument();
    expect(within(card).getByText(parking.recommendationReason)).toBeInTheDocument();
    expect(within(card).getByText("SIMULATED")).toBeInTheDocument();
  });

  it("selects the facility for the map", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<ParkingCard parking={parking} rank={1} onSelect={onSelect} />);
    await user.click(screen.getByRole("button", { name: "Show North Parking on campus map" }));
    expect(onSelect).toHaveBeenCalledWith("P1");
  });
});
