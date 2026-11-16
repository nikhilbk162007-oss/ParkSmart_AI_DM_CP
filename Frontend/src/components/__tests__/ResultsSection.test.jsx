import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ResultsSection from "../ResultsSection.jsx";

const recommendation = {
  id: "P1",
  name: "North Parking",
  totalCapacity: 50,
  availableSpaces: 35,
  occupiedSpaces: 15,
  acceptedVehicleTypes: ["car", "two-wheeler"],
  isSimulated: true,
  dataSource: "simulated-campus-v1",
  entryGate: "gate_north",
  destination: "dest_library",
  routeDistanceMeters: 170,
  walkingDistanceMeters: 390,
  totalDistanceMeters: 560,
  routePath: ["gate_north", "road_north", "P1", "road_library", "dest_library"],
  recommendationReason: "35 spaces available; balanced route.",
  recommendationStatus: "Recommended",
};

describe("ResultsSection", () => {
  it("renders backend route and occupancy details and highlights the top result", () => {
    render(
      <ResultsSection
        criteria={{ destination: "Library", entryGate: "gate_north", vehicleType: "car" }}
        status="success"
        results={[recommendation]}
        facilities={[{ id: "P1", name: "North Parking", totalCapacity: 50, availableSpaces: 35, currentOccupancy: { occupiedSpaces: 15 } }]}
        selectedParkingId="P1"
      />,
    );

    expect(screen.getByText("1 recommendation found")).toBeInTheDocument();
    const card = screen.getByRole("article", { name: /North Parking, Recommended/i });
    expect(within(card).getByText("170 m")).toBeInTheDocument();
    expect(within(card).getByText("390 m")).toBeInTheDocument();
    expect(within(card).getByText("35 spaces available; balanced route.")).toBeInTheDocument();
    expect(card).toHaveClass("is-recommended");
    expect(screen.getAllByText(/not geographically accurate/i).length).toBeGreaterThan(0);
  });

  it("shows loading, empty and retryable error states", async () => {
    const onRetry = vi.fn();
    const { rerender } = render(<ResultsSection status="loading" results={[]} />);
    expect(screen.getByRole("status")).toHaveTextContent("Finding your best route");

    rerender(<ResultsSection status="success" results={[]} />);
    expect(screen.getByRole("heading", { name: "No compatible spaces available" })).toBeInTheDocument();

    rerender(<ResultsSection status="error" error="Backend offline" results={[]} onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Backend offline");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
