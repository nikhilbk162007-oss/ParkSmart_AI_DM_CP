import { afterEach, describe, expect, it, vi } from "vitest";
import { getParkingResults } from "../parkingResultsProvider.js";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("getParkingResults", () => {
  it("accepts API adapter records with unique IDs and missing optional fields", async () => {
    vi.stubEnv("VITE_PARKING_DATA_MODE", "api");
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test");
    const apiAdapter = vi.fn().mockResolvedValue([{ id: "option-1" }]);

    await expect(
      getParkingResults(
        { destination: "Pune", arrivalTime: "2026-10-25T10:30" },
        { apiAdapter },
      ),
    ).resolves.toEqual({ mode: "api", results: [{ id: "option-1" }] });
    expect(apiAdapter).toHaveBeenCalledOnce();
    expect(apiAdapter).toHaveBeenCalledWith(
      { destination: "Pune", arrivalTime: "2026-10-25T10:30" },
      expect.objectContaining({ baseUrl: "https://api.example.test" }),
    );
  });

  it("preserves an empty API response without substituting demo fixtures", async () => {
    vi.stubEnv("VITE_PARKING_DATA_MODE", "api");
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test");
    const apiAdapter = vi.fn().mockResolvedValue([]);

    await expect(getParkingResults({}, { apiAdapter })).resolves.toEqual({
      mode: "api",
      results: [],
    });
    expect(apiAdapter).toHaveBeenCalledOnce();
  });

  it("surfaces adapter failures without falling back to demo fixtures", async () => {
    vi.stubEnv("VITE_PARKING_DATA_MODE", "api");
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test");
    const apiAdapter = vi.fn().mockRejectedValue(new Error("Request failed."));

    await expect(getParkingResults({}, { apiAdapter })).rejects.toThrow("Request failed.");
    expect(apiAdapter).toHaveBeenCalledOnce();
  });

  it.each([
    ["non-array response", { results: [] }, /results array/i],
    ["null record", [null], /result 1 is malformed/i],
    ["array record", [[{ id: "option-1" }]], /result 1 is malformed/i],
    ["missing ID", [{ name: "Option" }], /missing a usable unique id/i],
    ["duplicate IDs", [{ id: "option-1" }, { id: "option-1" }], /duplicate id/i],
    ["colliding numeric and string IDs", [{ id: 1 }, { id: "1" }], /duplicate id/i],
  ])("rejects malformed API adapter data: %s", async (_case, response, errorMessage) => {
    vi.stubEnv("VITE_PARKING_DATA_MODE", "api");
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test");

    await expect(
      getParkingResults({}, { apiAdapter: vi.fn().mockResolvedValue(response) }),
    ).rejects.toMatchObject({
      name: "ParkingResultsError",
      message: expect.stringMatching(errorMessage),
    });
  });
});
