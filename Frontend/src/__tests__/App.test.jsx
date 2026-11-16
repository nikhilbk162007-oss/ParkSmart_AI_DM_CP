import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/backendApiAdapter.js", () => ({
  fetchCurrentUser: vi.fn(),
  fetchCampusRecommendations: vi.fn(),
  fetchParkingFacilities: vi.fn(),
  getAuthToken: vi.fn(),
  login: vi.fn(),
  registerAccount: vi.fn(),
  recordVehicleEvent: vi.fn(),
  revokeSession: vi.fn(),
  setAuthToken: vi.fn(),
}));

import {
  fetchCurrentUser,
  fetchCampusRecommendations,
  fetchParkingFacilities,
  getAuthToken,
  login,
  recordVehicleEvent,
  revokeSession,
  setAuthToken,
} from "../services/backendApiAdapter.js";
import App from "../App.jsx";

const initialFacility = {
  id: "P1",
  name: "North Parking",
  totalCapacity: 50,
  availableSpaces: 35,
  acceptedVehicleTypes: ["car", "two-wheeler"],
  currentOccupancy: {
    occupiedSpaces: 15,
    freeSpaces: 35,
    vehicleCounts: { car: 15, "two-wheeler": 0 },
  },
  isSimulated: true,
  dataSource: "simulated-campus-v1",
};

const updatedFacility = {
  ...initialFacility,
  availableSpaces: 34,
  currentOccupancy: {
    occupiedSpaces: 16,
    freeSpaces: 34,
    vehicleCounts: { car: 16, "two-wheeler": 0 },
  },
};

const recommendation = {
  id: "P1",
  name: "North Parking",
  totalCapacity: 50,
  availableSpaces: 35,
  occupiedSpaces: 15,
  acceptedVehicleTypes: ["car", "two-wheeler"],
  isSimulated: true,
  dataSource: "simulated-campus-v1",
  entryGate: "gate_north",
  destination: "dest_library",
  routeDistanceMeters: 170,
  walkingDistanceMeters: 390,
  totalDistanceMeters: 560,
  routePath: ["gate_north", "road_north", "P1", "road_library", "dest_library"],
  recommendationReason: "35 spaces available; balanced route.",
  recommendationStatus: "Recommended",
};

function goTo(user, section) {
  return user.click(within(screen.getByRole("navigation", { name: "Main navigation" })).getByRole("button", { name: new RegExp(section) }));
}

function startPortal(role = "user", path = role === "admin" ? "/admin" : "/user") {
  getAuthToken.mockReturnValue("test-access-token");
  fetchCurrentUser.mockResolvedValue({ username: "campus-test", role });
  window.history.replaceState({}, "", path);
}

describe("ParkSmart campus dashboard", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    startPortal();
    fetchParkingFacilities.mockResolvedValue([initialFacility]);
    fetchCampusRecommendations.mockResolvedValue([recommendation]);
    recordVehicleEvent.mockResolvedValue(updatedFacility);
    revokeSession.mockResolvedValue(null);
  });

  it("loads dashboard metrics from backend facility records", async () => {
    render(<App />);
    expect(await screen.findByText("Backend connected")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Campus dashboard" })).toBeInTheDocument();
    expect(screen.getByText("50", { selector: ".metric-card strong" })).toBeInTheDocument();
    expect(screen.getByText("15", { selector: ".metric-card strong" })).toBeInTheDocument();
    expect(screen.getByText("35", { selector: ".metric-card strong" })).toBeInTheDocument();
    expect(screen.getAllByText(/simulated campus data/i).length).toBeGreaterThan(0);
  });

  it("submits selected destination, gate and vehicle type and renders backend recommendations", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Backend connected");
    await goTo(user, "Find parking");
    await user.selectOptions(screen.getByLabelText("Destination"), "Auditorium");
    await user.selectOptions(screen.getByLabelText("Entry gate"), "gate_south");
    await user.selectOptions(screen.getByLabelText("Vehicle type"), "two-wheeler");
    await user.click(within(screen.getByRole("form", { name: "Find campus parking" })).getByRole("button", { name: "Find parking" }));

    expect(await screen.findByRole("article", { name: "North Parking, Recommended" })).toBeInTheDocument();
    expect(fetchCampusRecommendations).toHaveBeenCalledWith(
      { destination: "Auditorium", entryGate: "gate_south", vehicleType: "two-wheeler" },
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(screen.getByText("170 m")).toBeInTheDocument();
    expect(screen.getByText("390 m")).toBeInTheDocument();
  });

  it("posts entry, refreshes facilities and reruns the current recommendation", async () => {
    const user = userEvent.setup();
    startPortal("admin");
    fetchParkingFacilities
      .mockResolvedValueOnce([initialFacility])
      .mockResolvedValueOnce([updatedFacility]);
    fetchCampusRecommendations
      .mockResolvedValueOnce([recommendation])
      .mockResolvedValueOnce([{ ...recommendation, availableSpaces: 34, occupiedSpaces: 16 }]);
    render(<App />);
    await screen.findByText("Backend connected");
    await goTo(user, "Find parking");
    await user.click(within(screen.getByRole("form", { name: "Find campus parking" })).getByRole("button", { name: "Find parking" }));
    await screen.findByRole("article", { name: "North Parking, Recommended" });

    await goTo(user, "Simulation control");
    await user.click(screen.getByRole("button", { name: "Simulate entry" }));
    expect(recordVehicleEvent).toHaveBeenCalledWith("P1", "entry", "car");
    expect(await screen.findByText(/Vehicle entry recorded at North Parking/i)).toBeInTheDocument();
    expect(fetchParkingFacilities).toHaveBeenCalledTimes(2);
    expect(fetchCampusRecommendations).toHaveBeenCalledTimes(2);
    expect(screen.getByText("16", { selector: ".simulation-occupancy > strong" })).toBeInTheDocument();
  });

  it("posts a vehicle exit and displays backend rejection feedback", async () => {
    const user = userEvent.setup();
    startPortal("admin");
    recordVehicleEvent.mockRejectedValueOnce(new Error("No parked 'car' vehicle is available to exit."));
    render(<App />);
    await screen.findByText("Backend connected");
    await goTo(user, "Simulation control");
    await user.click(screen.getByRole("button", { name: "Simulate exit" }));

    expect(recordVehicleEvent).toHaveBeenCalledWith("P1", "exit", "car");
    expect(await screen.findByRole("alert")).toHaveTextContent("No parked 'car' vehicle");
    expect(fetchParkingFacilities).toHaveBeenCalledTimes(1);
  });

  it("shows a clear backend connection error instead of demo data", async () => {
    fetchParkingFacilities.mockRejectedValue(new Error("Connection refused"));
    render(<App />);
    expect(await screen.findByText("Facility data unavailable.")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Connection refused");
    expect(screen.getByText("Backend unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Garden District Parking")).not.toBeInTheDocument();
  });

  it("keeps simulation controls out of the regular user portal", async () => {
    render(<App />);
    await screen.findByText("Backend connected");
    expect(screen.queryByRole("button", { name: "Simulation control" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open simulation controls" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Parking details" })).toBeInTheDocument();
  });

  it("redirects regular users away from admin routes", async () => {
    startPortal("user", "/admin/simulation");
    render(<App />);
    await screen.findByText("Backend connected");
    expect(window.location.pathname).toBe("/user");
    expect(screen.queryByRole("heading", { name: "Simulation control" })).not.toBeInTheDocument();
  });

  it("redirects unauthenticated visitors to login and admins to the admin portal", async () => {
    getAuthToken.mockReturnValue(null);
    window.history.replaceState({}, "", "/admin");
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
    expect(screen.getByLabelText("Username")).toBeInTheDocument();

    login.mockResolvedValue({
      accessToken: "admin-access-token",
      user: { username: "campus-admin", role: "admin" },
    });
    await user.type(screen.getByLabelText("Username"), "campus-admin");
    await user.type(screen.getByLabelText("Password"), "password-for-test");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Backend connected")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/admin");
    expect(screen.getByRole("button", { name: /Simulation control/ })).toBeInTheDocument();
    expect(setAuthToken).toHaveBeenCalledWith("admin-access-token");
  });

  it("clears the session and returns to login on logout", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Backend connected");
    await user.click(screen.getByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
    expect(setAuthToken).toHaveBeenCalledWith(null);
    expect(revokeSession).toHaveBeenCalledOnce();
  });
});
