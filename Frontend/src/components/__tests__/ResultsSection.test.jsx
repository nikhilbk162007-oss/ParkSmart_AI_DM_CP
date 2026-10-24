import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { parkingFixtures } from "../../data/parkingFixtures.js";
import ResultsSection from "../ResultsSection.jsx";

const criteria = {
  destination: "Central Library",
  arrivalTime: "2026-10-25T10:30",
};

function renderResults(results = parkingFixtures) {
  const user = userEvent.setup();
  render(
    <ResultsSection
      criteria={criteria}
      mode="demo"
      status="success"
      results={results}
      onRetry={() => {}}
    />,
  );
  return user;
}

function getParkingNames() {
  return Array.from(document.querySelectorAll(".parking-card-title h3")).map(
    (heading) => heading.textContent,
  );
}

describe("ResultsSection", () => {
  it("renders the simulated-data disclosure and fixture cards", () => {
    renderResults();

    expect(screen.getByText("Simulated development data")).toBeInTheDocument();
    expect(screen.getByText(/do not represent live parking availability/i)).toBeInTheDocument();
    expect(screen.getAllByText("Simulated")).toHaveLength(parkingFixtures.length);
    expect(getParkingNames()).toHaveLength(parkingFixtures.length);
  });

  it("sorts by predicted free spaces", async () => {
    const user = renderResults();

    await user.selectOptions(screen.getByLabelText("Sort by"), "predicted-free");

    expect(getParkingNames()).toEqual([
      "Garden District Parking",
      "Riverfront Parking House",
      "Market Street Garage",
    ]);
  });

  it("sorts valid numeric values before malformed optional values", async () => {
    const user = renderResults([
      { id: "bad-distance", name: "Invalid distance", distanceKm: -2, predictedFreeSpaces: "8" },
      { id: "valid-near", name: "Valid nearby", distanceKm: 0.5, predictedFreeSpaces: 8 },
      { id: "bad-count", name: "Invalid count", distanceKm: 1, predictedFreeSpaces: -1 },
    ]);

    expect(getParkingNames()).toEqual(["Valid nearby", "Invalid count", "Invalid distance"]);
    await user.selectOptions(screen.getByLabelText("Sort by"), "predicted-free");
    expect(getParkingNames()).toEqual(["Valid nearby", "Invalid distance", "Invalid count"]);

    await user.type(screen.getByLabelText("Minimum predicted free spaces"), "0");
    expect(getParkingNames()).toEqual(["Valid nearby"]);
  });

  it("filters by maximum distance and minimum predicted availability", async () => {
    const user = renderResults();

    await user.type(screen.getByLabelText("Maximum reported distance (km)"), "1");
    expect(
      screen.getAllByRole("article").map((card) => within(card).getByRole("heading").textContent),
    ).toEqual(["Riverfront Parking House"]);

    await user.clear(screen.getByLabelText("Maximum reported distance (km)"));
    await user.type(screen.getByLabelText("Minimum predicted free spaces"), "130");
    expect(
      screen.getAllByRole("article").map((card) => within(card).getByRole("heading").textContent),
    ).toEqual(["Riverfront Parking House", "Garden District Parking"]);
  });

  it("shows an empty filtered-results state when no fixtures match", async () => {
    const user = renderResults();

    await user.type(screen.getByLabelText("Minimum predicted free spaces"), "9999");

    expect(screen.getByRole("status")).toHaveTextContent("No options match these filters");
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
  });

  it("shows an empty-results state when no records are provided", () => {
    renderResults([]);

    expect(screen.getByRole("status")).toHaveTextContent("No parking options found");
    expect(screen.getByText("0 of 0 simulated options")).toBeInTheDocument();
  });

  it("shows API failures and invokes the provided retry action", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(
      <ResultsSection
        criteria={criteria}
        mode="api"
        status="error"
        results={[]}
        error="Backend request failed."
        onRetry={onRetry}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Backend request failed.");
    expect(screen.queryByText("Simulated development data")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("highlights only an explicitly recommended option and labels other results as alternatives", () => {
    const results = parkingFixtures.map((parking, index) =>
      index === 1
        ? {
            ...parking,
            recommendationStatus: "Recommended",
            recommendationExplanation: "Explicitly identified by the result data.",
          }
        : parking,
    );
    renderResults(results);

    const recommendedCard = screen
      .getByRole("heading", { level: 3, name: "Market Street Garage" })
      .closest(".parking-card");
    expect(within(recommendedCard).getByText("Recommended", { selector: "strong" }))
      .toBeInTheDocument();
    expect(
      within(recommendedCard).getByText("Explicitly identified by the result data."),
    ).toBeInTheDocument();
    expect(recommendedCard).toHaveClass("is-recommended");

    const alternativeCard = screen
      .getByRole("heading", { level: 3, name: "Garden District Parking" })
      .closest(".parking-card");
    expect(within(alternativeCard).getByText("Alternative option")).toBeInTheDocument();
    expect(alternativeCard).not.toHaveClass("is-recommended");
  });

  it("does not designate a recommendation when the result data has no recommendation status", () => {
    renderResults(parkingFixtures);

    expect(screen.queryByText("Recommended")).not.toBeInTheDocument();
    expect(screen.queryByText("Alternative option")).not.toBeInTheDocument();
    expect(document.querySelector(".parking-card.is-recommended")).not.toBeInTheDocument();
  });

  it("selects a card and its corresponding map marker in both directions", async () => {
    const user = renderResults();
    const markerButtons = screen.getAllByRole("button", { name: /simulated demo marker/i });
    const markerWrappers = screen.getAllByTestId("parking-map-marker-wrapper");

    await user.click(markerButtons[2]);

    expect(screen.getByRole("button", { name: "Selected on map" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(markerWrappers[2]).toHaveAttribute("data-selected", "true");

    const marketCard = screen
      .getByRole("heading", { level: 3, name: "Market Street Garage" })
      .closest(".parking-card");
    await user.click(within(marketCard).getByRole("button", { name: "Show on map" }));
    expect(markerWrappers[1]).toHaveAttribute("data-selected", "true");
    expect(screen.getAllByRole("button", { name: "Selected on map" })).toHaveLength(1);
  });
});
