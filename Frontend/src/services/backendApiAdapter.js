import { ParkingResultsError } from "./parkingResultsError.js";

export async function backendApiAdapter(criteria, { baseUrl, signal }) {
  const url = `${baseUrl.replace(/\/+$/, "")}/api/recommendations`;
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        destination: criteria.destination,
        arrivalTime: new Date(criteria.arrivalTime).toISOString(),
      }),
      signal,
    });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw error;
    }
    throw new ParkingResultsError(
      error instanceof Error ? `Unable to reach the parking backend: ${error.message}` : "Unable to reach the parking backend.",
    );
  }

  if (!response.ok) {
    let message = `Parking backend returned HTTP ${response.status}.`;
    try {
      const body = await response.json();
      if (typeof body?.error?.message === "string" && body.error.message.trim()) {
        message = body.error.message;
      }
    } catch (error) {
      if (error?.name === "AbortError") {
        throw error;
      }
      // The response body may not be JSON; retain the explicit HTTP status error.
    }
    throw new ParkingResultsError(message);
  }

  try {
    return await response.json();
  } catch (error) {
    if (error?.name === "AbortError") {
      throw error;
    }
    throw new ParkingResultsError("The parking backend returned an invalid JSON response.");
  }
}
