import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ParkingCard from "../ParkingCard.jsx";

describe("ParkingCard", () => {
  it("shows a percentage and accessible progress for consistent predicted counts", () => {
    render(
      <ParkingCard
        parking={{
          id: "valid",
          name: "Civic Garage",
          totalCapacity: 200,
          predictedOccupiedSpaces: 80,
          predictedFreeSpaces: 120,
          distanceKm: 1.4,
        }}
        mode="api"
      />,
    );

    const progress = screen.getByRole("progressbar", { name: "Predicted occupancy" });
    expect(progress).toHaveAttribute("aria-valuenow", "40");
    expect(progress).toHaveAttribute(
      "aria-valuetext",
      "Predicted occupancy: 40%, 80 spaces out of 200 spaces",
    );
    expect(screen.getByText("Predicted occupancy: 40%, 80 spaces out of 200 spaces"))
      .toBeInTheDocument();
    expect(screen.getByText("120 spaces")).toBeInTheDocument();
    expect(screen.getByText("1.4 km")).toBeInTheDocument();
  });

  it("does not calculate a percentage when capacity is zero", () => {
    render(
      <ParkingCard
        parking={{
          id: "zero",
          totalCapacity: 0,
          predictedOccupiedSpaces: 0,
          predictedFreeSpaces: 0,
          distanceKm: 0,
        }}
        mode="api"
      />,
    );

    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
    expect(
      screen.getByText("Occupancy percentage unavailable because capacity is zero."),
    ).toBeInTheDocument();
    expect(screen.getAllByText("0 spaces")).toHaveLength(3);
  });

  it("renders graceful fallbacks when optional fields are missing", () => {
    render(<ParkingCard parking={{ id: "partial", name: "Example Garage" }} mode="api" />);

    expect(screen.getByRole("heading", { name: "Example Garage" })).toBeInTheDocument();
    expect(screen.getAllByText("Not provided")).toHaveLength(6);
    expect(screen.getByText(/occupancy percentage unavailable/i)).toBeInTheDocument();
    expect(screen.queryByText("Simulated")).not.toBeInTheDocument();
    expect(screen.queryByText(/sample location/i)).not.toBeInTheDocument();
  });

  it("labels occupancy as predicted and distinguishes it from current occupancy", () => {
    render(
      <ParkingCard
        parking={{
          id: "predicted",
          totalCapacity: 100,
          predictedOccupiedSpaces: 40,
          predictedFreeSpaces: 60,
        }}
        mode="api"
      />,
    );

    expect(screen.getByText("Predicted occupancy · not current occupancy")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Predicted occupancy" })).toBeInTheDocument();
    expect(screen.queryByText(/current occupancy:\s*\d/i)).not.toBeInTheDocument();
  });

  it("renders supplied recommendation information while safely ignoring malformed optional text", () => {
    render(
      <ParkingCard
        parking={{
          id: "malformed-optional",
          name: { unexpected: true },
          recommendationStatus: ["unexpected"],
          recommendationExplanation: { unexpected: true },
          distanceKm: "2",
          predictedFreeSpaces: "10",
        }}
        mode="api"
      />,
    );

    expect(screen.getByRole("heading", { name: "Parking location" })).toBeInTheDocument();
    expect(screen.getAllByText("Not provided")).toHaveLength(4);
    expect(screen.getAllByText("Invalid value")).toHaveLength(2);
    expect(screen.getByText("Reported distance")).toBeInTheDocument();
  });

  it.each([
    ["negative capacity", { totalCapacity: -1, predictedOccupiedSpaces: 0 }],
    ["non-finite capacity", { totalCapacity: Number.POSITIVE_INFINITY, predictedOccupiedSpaces: 1 }],
    ["negative occupancy", { totalCapacity: 10, predictedOccupiedSpaces: -1 }],
    ["non-finite occupancy", { totalCapacity: 10, predictedOccupiedSpaces: Number.NaN }],
    ["occupancy beyond capacity", { totalCapacity: 10, predictedOccupiedSpaces: 11 }],
    [
      "inconsistent occupied and free counts",
      { totalCapacity: 10, predictedOccupiedSpaces: 4, predictedFreeSpaces: 4 },
    ],
  ])("does not render a misleading progress value for %s", (_description, values) => {
    render(<ParkingCard parking={{ id: "invalid", ...values }} mode="api" />);

    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
    expect(screen.getByText(/occupancy percentage unavailable/i)).toBeInTheDocument();
  });

  it.each([
    ["negative distance", -0.5],
    ["non-finite distance", Number.NaN],
  ])("marks %s as invalid", (_description, distanceKm) => {
    render(<ParkingCard parking={{ id: "distance", distanceKm }} mode="api" />);

    expect(screen.getByText("Invalid value")).toBeInTheDocument();
  });

  it("keeps the simulated-data label and does not invent recommendation explanations", () => {
    render(
      <ParkingCard
        parking={{ id: "demo", dataSource: "simulated-development" }}
        mode="demo"
      />,
    );

    expect(screen.getByText("Simulated")).toBeInTheDocument();
    expect(screen.getAllByText("Not provided")).toHaveLength(6);
    expect(screen.queryByText(/illustrative fixture text/i)).not.toBeInTheDocument();
  });
});
