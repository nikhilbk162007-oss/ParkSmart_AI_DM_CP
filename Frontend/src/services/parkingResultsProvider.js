import { parkingFixtures } from "../data/parkingFixtures.js";
import { backendApiAdapter } from "./backendApiAdapter.js";
import { ParkingResultsError } from "./parkingResultsError.js";
export { ParkingResultsError } from "./parkingResultsError.js";

function validateApiResults(results) {
  if (!Array.isArray(results)) {
    throw new ParkingResultsError(
      "The configured API adapter did not return a results array in the frontend format.",
    );
  }

  const seenIds = new Set();
  results.forEach((parking, index) => {
    if (!parking || typeof parking !== "object" || Array.isArray(parking)) {
      throw new ParkingResultsError(
        `API result ${index + 1} is malformed. The adapter must return parking option objects.`,
      );
    }

    const hasStringId = typeof parking.id === "string" && parking.id.trim().length > 0;
    const hasNumberId = typeof parking.id === "number" && Number.isFinite(parking.id);
    if (!hasStringId && !hasNumberId) {
      throw new ParkingResultsError(
        `API result ${index + 1} is missing a usable unique id required for card and map selection.`,
      );
    }

    const normalizedId = String(parking.id);
    if (seenIds.has(normalizedId)) {
      throw new ParkingResultsError(
        `API results contain duplicate id "${normalizedId}". The adapter must provide unique ids.`,
      );
    }
    seenIds.add(normalizedId);
  });

  return results;
}

export function getConfiguredParkingMode() {
  const mode = import.meta.env.VITE_PARKING_DATA_MODE?.trim().toLowerCase();
  return mode || "demo";
}

export async function getParkingResults(criteria, { signal, apiAdapter } = {}) {
  if (signal?.aborted) {
    throw new DOMException("The search was cancelled.", "AbortError");
  }

  const mode = getConfiguredParkingMode();

  if (mode === "demo") {
    return { mode, results: parkingFixtures };
  }

  if (mode !== "api") {
    throw new ParkingResultsError(
      `Unsupported VITE_PARKING_DATA_MODE "${mode}". Choose "demo" or "api".`,
    );
  }

  const baseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
  if (!baseUrl) {
    throw new ParkingResultsError(
      "API mode is selected, but VITE_API_BASE_URL is not set. Configure the backend base URL after it is confirmed.",
    );
  }

  const adapter = apiAdapter || backendApiAdapter;
  const results = validateApiResults(await adapter(criteria, { baseUrl, signal }));

  if (signal?.aborted) {
    throw new DOMException("The search was cancelled.", "AbortError");
  }

  return { mode, results };
}
