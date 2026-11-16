import { afterEach, describe, expect, it, vi } from "vitest";
import { getConfiguredParkingMode, getParkingResults } from "../parkingResultsProvider.js";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("parkingResultsProvider", () => {
  it("uses the backend API by default rather than fabricated fixtures", () => {
    expect(getConfiguredParkingMode()).toBe("api");
  });

  it("returns backend recommendations and passes cancellation through", async () => {
    const records = [{ id: "P1", name: "North Parking" }];
    const apiAdapter = vi.fn().mockResolvedValue(records);
    const signal = new AbortController().signal;
    await expect(getParkingResults({
      destination: "Library",
      entryGate: "gate_north",
      vehicleType: "car",
    }, { apiAdapter, signal })).resolves.toEqual({ mode: "api", results: records });
    expect(apiAdapter).toHaveBeenCalledWith(
      { destination: "Library", entryGate: "gate_north", vehicleType: "car" },
      { signal },
    );
  });

  it("does not substitute fixtures for empty, invalid, or failed backend responses", async () => {
    await expect(getParkingResults({}, { apiAdapter: vi.fn().mockResolvedValue([]) }))
      .resolves.toEqual({ mode: "api", results: [] });
    await expect(getParkingResults({}, { apiAdapter: vi.fn().mockResolvedValue({}) }))
      .rejects.toThrow("results array");
    await expect(getParkingResults({}, { apiAdapter: vi.fn().mockRejectedValue(new Error("offline")) }))
      .rejects.toThrow("offline");
  });
});
