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

  it("reports the missing API contract without making network requests", async () => {
    vi.stubEnv("VITE_PARKING_DATA_MODE", "api");
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await submitValidSearch(user);

    expect(
      await screen.findByText(/backend contract is not configured/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => {
      expect(screen.getByText(/backend contract is not configured/i)).toBeInTheDocument();
    });
    expect(fetchMock).not.toHaveBeenCalled();
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
});
