import { backendApiAdapter } from "./backendApiAdapter.js";
import { ParkingResultsError } from "./parkingResultsError.js";
export { ParkingResultsError } from "./parkingResultsError.js";

export function getConfiguredParkingMode() {
  return "api";
}

export async function getParkingResults(criteria, { signal, apiAdapter } = {}) {
  if (signal?.aborted) {
    throw new DOMException("The search was cancelled.", "AbortError");
  }
  const results = await (apiAdapter || backendApiAdapter)(criteria, { signal });
  if (signal?.aborted) {
    throw new DOMException("The search was cancelled.", "AbortError");
  }
  if (!Array.isArray(results)) {
    throw new ParkingResultsError("The recommendation backend did not return a results array.");
  }
  return { mode: "api", results };
}
