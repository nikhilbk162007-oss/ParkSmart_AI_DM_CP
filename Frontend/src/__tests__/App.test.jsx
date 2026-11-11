import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getParkingResults } from "../services/parkingResultsProvider.js";
import App from "../App.jsx";

vi.mock("../services/parkingResultsProvider.js", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    getParkingResults: vi.fn(actual.getParkingResults),
  };
});

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function submitValidSearch(user) {
  await user.type(screen.getByLabelText("YOUR DESTINATION"), "Central Library");
  await user.type(screen.getByLabelText("ARRIVAL TIME"), "2026-10-25T10:30");
  await user.click(screen.getByRole("button", { name: "Find parking" }));
}

function deferred() {
  let resolve;
  const promise = new Promise((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

describe("App search results", () => {
  it("shows demo results only after a valid search submission", async () => {
    vi.stubEnv("VITE_PARKING_DATA_MODE", "demo");
    const user = userEvent.setup();
    render(<App />);

    expect(screen.queryByRole("heading", { name: "Parking options" })).not.toBeInTheDocument();
    expect(screen.queryByText("Riverfront Parking House")).not.toBeInTheDocument();

    await submitValidSearch(user);

    expect(await screen.findByRole("heading", { name: "Parking options" })).toBeInTheDocument();
    expect(screen.getByText("Simulated development data")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 3, name: "Riverfront Parking House" }),
    ).toBeInTheDocument();
  });

  it("does not show results after invalid search submission", async () => {
    vi.stubEnv("VITE_PARKING_DATA_MODE", "demo");
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "Find parking" }));

    expect(screen.getByText("Enter a destination to continue.")).toBeInTheDocument();
    expect(screen.getByText("Choose a valid arrival date and time.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Parking options" })).not.toBeInTheDocument();
  });

  it("submits API searches to the backend and renders returned options", async () => {
    vi.stubEnv("VITE_PARKING_DATA_MODE", "api");
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test///");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{
        id: "api-garage",
        name: "API Garage",
        totalCapacity: 100,
        predictedOccupiedSpaces: 30,
        predictedFreeSpaces: 70,
        distanceKm: 0.5,
        coordinates: [18.52, 73.85],
        recommendationStatus: "Recommended",
        recommendationExplanation: "Closest available option.",
      }],
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await submitValidSearch(user);

    expect(await screen.findByRole("heading", { name: "API Garage" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/api/recommendations",
      expect.objectContaining({ method: "POST" }),
    );
    const requestBody = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(requestBody.destination).toBe("Central Library");
    expect(requestBody.arrivalTime).toMatch(/Z$/);
  });

  it("shows a backend 503 message and retries API searches", async () => {
    vi.stubEnv("VITE_PARKING_DATA_MODE", "api");
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test");
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: async () => ({ error: { message: "Database unavailable." } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [{ id: "retry", name: "Retry Garage" }],
      });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await submitValidSearch(user);
    expect(await screen.findByRole("alert")).toHaveTextContent("Database unavailable.");
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: "Retry Garage" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("does not let an older search overwrite a newer result", async () => {
    vi.stubEnv("VITE_PARKING_DATA_MODE", "demo");
    const firstSearch = deferred();
    const secondSearch = deferred();
    vi.mocked(getParkingResults)
      .mockImplementationOnce(() => firstSearch.promise)
      .mockImplementationOnce(() => secondSearch.promise);

    const user = userEvent.setup();
    render(<App />);
    await submitValidSearch(user);
    await user.click(screen.getByRole("button", { name: "Find parking" }));

    secondSearch.resolve({
      mode: "api",
      results: [{ id: "latest-result", name: "Latest search result" }],
    });
    expect(
      await screen.findByRole("heading", { level: 3, name: "Latest search result" }),
    ).toBeInTheDocument();

    firstSearch.resolve({
      mode: "api",
      results: [{ id: "stale-result", name: "Stale search result" }],
    });
    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 3, name: "Latest search result" }))
        .toBeInTheDocument();
      expect(
        screen.queryByRole("heading", { level: 3, name: "Stale search result" }),
      ).not.toBeInTheDocument();
    });
  });

  it("resets filters when a new search is submitted", async () => {
    vi.stubEnv("VITE_PARKING_DATA_MODE", "demo");
    const user = userEvent.setup();
    render(<App />);
    await submitValidSearch(user);
    expect(await screen.findByRole("heading", { name: "Parking options" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("Minimum predicted free spaces"), "9999");
    expect(screen.getByText("3 hidden by filters")).toBeInTheDocument();
    await user.clear(screen.getByLabelText("YOUR DESTINATION"));
    await user.type(screen.getByLabelText("YOUR DESTINATION"), "New Destination");
    await user.clear(screen.getByLabelText("ARRIVAL TIME"));
    await user.type(screen.getByLabelText("ARRIVAL TIME"), "2026-10-25T12:30");
    await user.click(screen.getByRole("button", { name: "Find parking" }));
    expect(await screen.findByRole("heading", { level: 3, name: "Riverfront Parking House" })).toBeInTheDocument();
    expect(screen.getByLabelText("Minimum predicted free spaces")).toHaveValue(null);
  });
});
