import { ParkingResultsError } from "./parkingResultsError.js";

const AUTH_TOKEN_STORAGE_KEY = "parksmart.accessToken";

export function getApiBaseUrl() {
  return import.meta.env.VITE_API_BASE_URL?.trim().replace(/\/+$/, "") || "http://localhost:8000";
}

function normalizeBaseUrl(baseUrl) {
  return baseUrl.replace(/\/+$/, "");
}

export function setAuthToken(token) {
  if (typeof window === "undefined") return;
  if (token) {
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
  } else {
    window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  }
}

export function getAuthToken() {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
}

async function requestJson(url, options = {}) {
  let response;
  try {
    const headers = new Headers(options.headers || {});
    const token = getAuthToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    response = await fetch(url, { ...options, headers });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw error;
    }
    throw new ParkingResultsError(
      error instanceof Error
        ? `Unable to reach the parking backend: ${error.message}`
        : "Unable to reach the parking backend.",
    );
  }

  if (!response.ok) {
    let message = `Parking backend returned HTTP ${response.status}.`;
    try {
      const body = await response.json();
      const detail = Array.isArray(body?.detail)
        ? body.detail.map((item) => item?.msg).filter(Boolean).join("; ")
        : body?.detail;
      if (typeof body?.error?.message === "string" && body.error.message.trim()) {
        message = body.error.message;
      } else if (typeof detail === "string" && detail.trim()) {
        message = detail;
      }
    } catch (error) {
      if (error?.name === "AbortError") {
        throw error;
      }
    }
    throw new ParkingResultsError(message);
  }

  if (response.status === 204) return null;

  try {
    return await response.json();
  } catch (error) {
    if (error?.name === "AbortError") {
      throw error;
    }
    throw new ParkingResultsError("The parking backend returned invalid JSON.");
  }
}

export async function login(credentials, { baseUrl = getApiBaseUrl() } = {}) {
  return requestJson(`${normalizeBaseUrl(baseUrl)}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });
}

export async function registerAccount(credentials, { baseUrl = getApiBaseUrl() } = {}) {
  return requestJson(`${normalizeBaseUrl(baseUrl)}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });
}

export async function fetchCurrentUser({ baseUrl = getApiBaseUrl() } = {}) {
  return requestJson(`${normalizeBaseUrl(baseUrl)}/api/auth/me`);
}

export async function revokeSession({ baseUrl = getApiBaseUrl() } = {}) {
  return requestJson(`${normalizeBaseUrl(baseUrl)}/api/auth/logout`, { method: "POST" });
}

function assertFacilityArray(facilities) {
  if (!Array.isArray(facilities)) {
    throw new ParkingResultsError("The parking backend did not return a facility array.");
  }
  const seenIds = new Set();
  facilities.forEach((facility, index) => {
    const occupancy = facility?.currentOccupancy;
    const counts = occupancy?.vehicleCounts;
    if (
      !facility ||
      typeof facility !== "object" ||
      typeof facility.id !== "string" ||
      !facility.id.trim() ||
      typeof facility.name !== "string" ||
      !Number.isInteger(facility.totalCapacity) ||
      facility.totalCapacity < 0 ||
      !Number.isInteger(facility.availableSpaces) ||
      !Number.isInteger(occupancy?.occupiedSpaces) ||
      !Number.isInteger(occupancy?.freeSpaces) ||
      !counts ||
      typeof counts !== "object" ||
      !Array.isArray(facility.acceptedVehicleTypes) ||
      typeof facility.isSimulated !== "boolean" ||
      facility.availableSpaces !== occupancy.freeSpaces ||
      facility.availableSpaces + occupancy.occupiedSpaces !== facility.totalCapacity ||
      Object.values(counts).some((count) => !Number.isInteger(count) || count < 0) ||
      Object.values(counts).reduce((sum, count) => sum + count, 0) !== occupancy.occupiedSpaces
    ) {
      throw new ParkingResultsError(`Parking facility ${index + 1} has an invalid response shape.`);
    }
    if (seenIds.has(facility.id)) {
      throw new ParkingResultsError(`Parking facilities contain duplicate ID "${facility.id}".`);
    }
    seenIds.add(facility.id);
  });
  return facilities;
}

function assertRecommendationArray(results) {
  if (!Array.isArray(results)) {
    throw new ParkingResultsError("The recommendation backend did not return a results array.");
  }
  const seenIds = new Set();
  results.forEach((item, index) => {
    if (
      !item ||
      typeof item !== "object" ||
      typeof item.id !== "string" ||
      !item.id.trim() ||
      typeof item.name !== "string" ||
      !Number.isInteger(item.totalCapacity) ||
      item.totalCapacity <= 0 ||
      !Number.isInteger(item.availableSpaces) ||
      item.availableSpaces <= 0 ||
      !Number.isInteger(item.occupiedSpaces) ||
      item.occupiedSpaces < 0 ||
      !Number.isInteger(item.routeDistanceMeters) ||
      item.routeDistanceMeters < 0 ||
      !Number.isInteger(item.walkingDistanceMeters) ||
      item.walkingDistanceMeters < 0 ||
      !Number.isInteger(item.totalDistanceMeters) ||
      item.totalDistanceMeters !== item.routeDistanceMeters + item.walkingDistanceMeters ||
      item.availableSpaces + item.occupiedSpaces !== item.totalCapacity ||
      !Array.isArray(item.acceptedVehicleTypes) ||
      !Array.isArray(item.routePath) ||
      typeof item.isSimulated !== "boolean" ||
      !["Recommended", "Alternative option"].includes(item.recommendationStatus) ||
      typeof item.recommendationReason !== "string"
    ) {
      throw new ParkingResultsError(`Recommendation ${index + 1} has an invalid response shape.`);
    }
    if (seenIds.has(item.id)) {
      throw new ParkingResultsError(`Recommendations contain duplicate ID "${item.id}".`);
    }
    seenIds.add(item.id);
  });
  return results;
}

export async function fetchParkingFacilities({ baseUrl = getApiBaseUrl(), signal } = {}) {
  const facilities = await requestJson(`${normalizeBaseUrl(baseUrl)}/api/parking`, { signal });
  return assertFacilityArray(facilities);
}

export async function fetchCampusRecommendations(criteria, { baseUrl = getApiBaseUrl(), signal } = {}) {
  const results = await requestJson(`${normalizeBaseUrl(baseUrl)}/api/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      destination: criteria.destination,
      entryGate: criteria.entryGate,
      vehicleType: criteria.vehicleType,
    }),
    signal,
  });
  return assertRecommendationArray(results);
}

export async function recordVehicleEvent(
  parkingId,
  eventType,
  vehicleType,
  { baseUrl = getApiBaseUrl(), signal } = {},
) {
  if (eventType !== "entry" && eventType !== "exit") {
    throw new ParkingResultsError("Vehicle event must be an entry or exit.");
  }
  const facility = await requestJson(
    `${normalizeBaseUrl(baseUrl)}/api/parking/${encodeURIComponent(parkingId)}/${eventType}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ vehicleType }),
      signal,
    },
  );
  return assertFacilityArray([facility])[0];
}

export async function backendApiAdapter(criteria, { baseUrl = getApiBaseUrl(), signal } = {}) {
  return fetchCampusRecommendations(criteria, { baseUrl, signal });
}
