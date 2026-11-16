import { afterEach, describe, expect, it, vi } from "vitest";
import {
  backendApiAdapter,
  fetchParkingFacilities,
  recordVehicleEvent,
} from "../backendApiAdapter.js";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

const facility = {
  id: "P1",
  name: "North Parking",
  totalCapacity: 50,
  isSimulated: true,
  acceptedVehicleTypes: ["car", "two-wheeler"],
  currentOccupancy: {
    occupiedSpaces: 15,
    freeSpaces: 35,
    vehicleCounts: { car: 15, "two-wheeler": 0 },
  },
  availableSpaces: 35,
};

describe("backend API adapter", () => {
  it("requests campus recommendations using the backend field names and direct array contract", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);
    await expect(backendApiAdapter({
      destination: "Library",
      entryGate: "gate_south",
      vehicleType: "two-wheeler",
    }, { baseUrl: "http://localhost:8000/" })).resolves.toEqual([]);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/recommendations",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          destination: "Library",
          entryGate: "gate_south",
          vehicleType: "two-wheeler",
        }),
      }),
    );
  });

  it("loads real backend facility occupancy without fixture fallback", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [facility] });
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchParkingFacilities({ baseUrl: "http://localhost:8000" }))
      .resolves.toEqual([facility]);
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/parking", expect.any(Object));
  });

  it("posts entry and exit events with the exact vehicleEvent body", async () => {
    const updated = {
      ...facility,
      currentOccupancy: {
        ...facility.currentOccupancy,
        occupiedSpaces: 16,
        freeSpaces: 34,
        vehicleCounts: { car: 16, "two-wheeler": 0 },
      },
      availableSpaces: 34,
    };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => updated });
    vi.stubGlobal("fetch", fetchMock);
    await recordVehicleEvent("P1", "entry", "car", { baseUrl: "http://localhost:8000" });
    await recordVehicleEvent("P1", "exit", "car", { baseUrl: "http://localhost:8000" });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/parking/P1/entry",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ vehicleType: "car" }) }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/parking/P1/exit",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ vehicleType: "car" }) }),
    );
  });

  it("surfaces API errors and aborts", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ error: { message: "Parking facility is full." } }),
    }));
    await expect(recordVehicleEvent("P1", "entry", "car", { baseUrl: "http://localhost:8000" }))
      .rejects.toThrow("Parking facility is full.");

    const abortError = new DOMException("Aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abortError));
    await expect(fetchParkingFacilities({ baseUrl: "http://localhost:8000" })).rejects.toBe(abortError);
  });
});
