import { afterEach, describe, expect, it, vi } from "vitest";
import { backendApiAdapter } from "../backendApiAdapter.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("backendApiAdapter", () => {
  it("preserves abort errors from fetch", async () => {
    const abortError = new DOMException("Aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abortError));
    await expect(
      backendApiAdapter(
        { destination: "Pune", arrivalTime: "2026-10-25T14:30" },
        { baseUrl: "http://localhost:8000", signal: new AbortController().signal },
      ),
    ).rejects.toBe(abortError);
  });

  it("preserves abort errors while parsing a response", async () => {
    const abortError = new DOMException("Aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => { throw abortError; },
    }));
    await expect(
      backendApiAdapter(
        { destination: "Pune", arrivalTime: "2026-10-25T14:30" },
        { baseUrl: "http://localhost:8000", signal: new AbortController().signal },
      ),
    ).rejects.toBe(abortError);
  });

  it("maps network failures to ParkingResultsError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    await expect(
      backendApiAdapter(
        { destination: "Pune", arrivalTime: "2026-10-25T14:30" },
        { baseUrl: "http://localhost:8000", signal: undefined },
      ),
    ).rejects.toMatchObject({ name: "ParkingResultsError", message: /offline/ });
  });
});
