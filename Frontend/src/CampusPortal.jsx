import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  ChevronDown,
  CircleParking,
  LayoutDashboard,
  Map,
  Menu,
  Search,
  Settings2,
  X,
} from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "./auth/AuthContext.jsx";
import DashboardOverview from "./components/DashboardOverview.jsx";
import ParkingDetails from "./components/ParkingDetails.jsx";
import ResultsSection from "./components/ResultsSection.jsx";
import SearchPanel from "./components/SearchPanel.jsx";
import SimulationControl from "./components/SimulationControl.jsx";
import {
  fetchCampusRecommendations,
  fetchParkingFacilities,
  recordVehicleEvent,
} from "./services/backendApiAdapter.js";

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "find", label: "Find parking", icon: Search },
  { id: "map", label: "Campus map", icon: Map },
];

const OPERATIONS_ITEMS = [
  { id: "simulation", label: "Simulation control", icon: Activity },
  { id: "details", label: "Parking details", icon: Settings2 },
];
const ADMIN_PORTAL_VIEWS = new Set(["dashboard", "find", "map", "simulation", "details"]);
const USER_PORTAL_VIEWS = new Set(["dashboard", "find", "map", "details"]);

function CampusPortal({ isAdmin }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const routerNavigate = useNavigate();
  const basePath = isAdmin ? "/admin" : "/user";
  const section = location.pathname.slice(basePath.length).split("/").filter(Boolean)[0] || "dashboard";
  const portalViews = isAdmin ? ADMIN_PORTAL_VIEWS : USER_PORTAL_VIEWS;
  const activeView = portalViews.has(section) ? section : "dashboard";
  const navigationItems = isAdmin
    ? [...NAV_ITEMS, ...OPERATIONS_ITEMS]
    : [...NAV_ITEMS, OPERATIONS_ITEMS[1]];
  const [facilities, setFacilities] = useState([]);
  const [facilityStatus, setFacilityStatus] = useState("loading");
  const [facilityError, setFacilityError] = useState("");
  const [selectedParkingId, setSelectedParkingId] = useState(null);
  const [recommendation, setRecommendation] = useState({
    criteria: null,
    status: "idle",
    results: [],
    error: "",
  });
  const [eventBusy, setEventBusy] = useState("");
  const [eventFeedback, setEventFeedback] = useState(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const recommendationRequestId = useRef(0);
  const recommendationController = useRef(null);
  const eventLock = useRef(false);

  useEffect(() => {
    if (!portalViews.has(section)) routerNavigate(basePath, { replace: true });
  }, [basePath, portalViews, routerNavigate, section]);

  const loadFacilities = useCallback(async ({ quiet = false } = {}) => {
    if (!quiet) setFacilityStatus("loading");
    try {
      const currentFacilities = await fetchParkingFacilities();
      setFacilities(currentFacilities);
      setFacilityError("");
      setFacilityStatus("success");
      setSelectedParkingId((current) =>
        current && currentFacilities.some((facility) => facility.id === current)
          ? current
          : currentFacilities[0]?.id || null,
      );
      return currentFacilities;
    } catch (error) {
      if (error?.name === "AbortError") return null;
      setFacilityStatus("error");
      setFacilityError(error instanceof Error ? error.message : "Unable to load campus facilities.");
      throw error;
    }
  }, []);

  useEffect(() => {
    loadFacilities().catch(() => {});
    return () => recommendationController.current?.abort();
  }, [loadFacilities]);

  const runSearch = useCallback(async (criteria) => {
    recommendationRequestId.current += 1;
    const requestId = recommendationRequestId.current;
    recommendationController.current?.abort();
    const controller = new AbortController();
    recommendationController.current = controller;
    setRecommendation({ criteria, status: "loading", results: [], error: "" });

    try {
      const results = await fetchCampusRecommendations(criteria, { signal: controller.signal });
      if (requestId !== recommendationRequestId.current || controller.signal.aborted) return false;
      setRecommendation({ criteria, status: "success", results, error: "" });
      if (results[0]) setSelectedParkingId(results[0].id);
      return true;
    } catch (error) {
      if (requestId !== recommendationRequestId.current || controller.signal.aborted) return false;
      setRecommendation({
        criteria,
        status: "error",
        results: [],
        error: error instanceof Error ? error.message : "Unable to load recommendations.",
      });
      return false;
    }
  }, []);

  async function handleVehicleEvent(parkingId, eventType, vehicleType) {
    if (eventLock.current) return;
    eventLock.current = true;
    setEventBusy(eventType);
    setEventFeedback(null);
    try {
      const updatedFacility = await recordVehicleEvent(parkingId, eventType, vehicleType);
      setFacilities((current) =>
        current.map((facility) => facility.id === updatedFacility.id ? updatedFacility : facility),
      );
      try {
        const latestFacilities = await fetchParkingFacilities();
        setFacilities(latestFacilities);
        setFacilityError("");
        setFacilityStatus("success");
      } catch (refreshError) {
        setEventFeedback({
          type: "success",
          message: `Vehicle ${eventType} recorded. Updated facility data is shown, but the full facility list could not refresh: ${refreshError.message}`,
        });
      }

      const recommendationsUpdated = recommendation.criteria
        ? await runSearch(recommendation.criteria)
        : true;
      setEventFeedback((current) => current || {
        type: "success",
        message: recommendationsUpdated
          ? `Vehicle ${eventType} recorded at ${updatedFacility.name}. Occupancy and recommendations are updated.`
          : `Vehicle ${eventType} recorded at ${updatedFacility.name}. Occupancy is updated, but recommendations could not refresh.`,
      });
    } catch (error) {
      setEventFeedback({
        type: "error",
        message: error instanceof Error ? error.message : "Unable to record the vehicle event.",
      });
    } finally {
      eventLock.current = false;
      setEventBusy("");
    }
  }

  function navigate(view) {
    routerNavigate(view === "dashboard" ? basePath : `${basePath}/${view}`);
    setMobileNavOpen(false);
  }

  async function signOut() {
    try {
      await logout();
      routerNavigate("/login", { replace: true, state: { message: "You have signed out." } });
    } catch (error) {
      routerNavigate("/login", {
        replace: true,
        state: { message: `Signed out on this device, but server revocation failed: ${error.message}` },
      });
    }
  }

  const selectedRecommendation = recommendation.results.find(
    (item) => item.id === selectedParkingId,
  );
  const pageTitle = navigationItems.find((item) => item.id === activeView)?.label || "Dashboard";
  const connected = facilityStatus === "success";

  return (
    <div className="app-shell">
      <aside className={`sidebar${mobileNavOpen ? " is-open" : ""}`}>
        <div className="sidebar-brand">
          <span className="brand-mark"><CircleParking size={22} strokeWidth={2} /></span>
          <span className="brand-name">ParkSmart<span>AI</span></span>
          <button className="icon-button mobile-nav-close" type="button" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)}><X size={19} /></button>
        </div>
        <div className="campus-switcher">
          <span className="campus-avatar">UC</span>
          <span><strong>University Campus</strong><small>Parking operations</small></span>
          <ChevronDown size={15} />
        </div>
        <nav className="main-navigation" aria-label="Main navigation">
          <p className="nav-section-label">WORKSPACE</p>
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
            <button key={id} type="button" className={`nav-item${activeView === id ? " is-active" : ""}`} aria-current={activeView === id ? "page" : undefined} onClick={() => navigate(id)}>
              <Icon size={18} strokeWidth={1.8} /><span>{label}</span>
            </button>
          ))}
          <p className="nav-section-label nav-section-spaced">{isAdmin ? "OPERATIONS" : "FACILITIES"}</p>
          {(isAdmin ? OPERATIONS_ITEMS : [OPERATIONS_ITEMS[1]]).map(({ id, label, icon: Icon }) => (
            <button key={id} type="button" className={`nav-item${activeView === id ? " is-active" : ""}`} aria-current={activeView === id ? "page" : undefined} onClick={() => navigate(id)}>
              <Icon size={18} strokeWidth={1.8} /><span>{label}</span>
              {isAdmin && id === "simulation" && <span className="nav-live-dot" aria-label="Simulation available" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-status"><span className={`connection-dot${connected ? " is-connected" : ""}`} /><span><strong>{connected ? "Backend connected" : facilityStatus === "loading" ? "Connecting…" : "Backend unavailable"}</strong><small>Campus API · localhost</small></span></div>
          <div className="sidebar-user"><span className="user-avatar">{user?.username?.slice(0, 2).toUpperCase()}</span><span><strong>{user?.username}</strong><small>{isAdmin ? "Administrator" : "User"} portal</small></span></div>
        </div>
      </aside>

      {mobileNavOpen && <button className="mobile-backdrop" type="button" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} />}
      <main className="main-area">
        <header className="topbar">
          <button className="icon-button mobile-menu-button" type="button" aria-label="Open navigation" onClick={() => setMobileNavOpen(true)}><Menu size={20} /></button>
          <div className="breadcrumbs"><span>ParkSmart AI</span><i>/</i><strong>{pageTitle}</strong></div>
          <div className="topbar-right">
            <span className="simulated-pill top-simulated"><span /> SIMULATED ENVIRONMENT</span>
            <button className="sign-out-button" type="button" onClick={signOut}>Sign out</button>
          </div>
        </header>
        <div className="content-area">
          {activeView === "dashboard" && (
            <DashboardOverview
              facilities={facilities}
              loading={facilityStatus === "loading"}
              error={facilityError}
              onRetry={() => loadFacilities().catch(() => {})}
              onNavigate={navigate}
              selectedParkingId={selectedParkingId}
              onSelectParking={setSelectedParkingId}
              showSimulationControl={isAdmin}
            />
          )}
          {activeView === "find" && (
            <section className="view-section" aria-label="Find parking workspace">
              <div className="page-heading">
                <div><p className="eyebrow">PERSONALIZED ROUTE PLAN</p><h1>Find parking</h1><p className="page-subtitle">Choose your destination and arrival gate to compare available facilities.</p></div>
                <span className="simulated-pill"><span /> CURRENT SIMULATION STATE</span>
              </div>
              <SearchPanel onSearch={runSearch} searchStatus={recommendation.status} />
              <ResultsSection
                criteria={recommendation.criteria}
                status={recommendation.status}
                results={recommendation.results}
                error={recommendation.error}
                onRetry={() => recommendation.criteria && runSearch(recommendation.criteria)}
                facilities={facilities}
                selectedParkingId={selectedParkingId}
                onSelectParking={setSelectedParkingId}
              />
            </section>
          )}
          {activeView === "map" && (
            <section className="view-section" aria-labelledby="map-page-title">
              <div className="page-heading"><div><p className="eyebrow">PREDEFINED ROAD NETWORK</p><h1 id="map-page-title">Campus map</h1><p className="page-subtitle">Explore all gates, destinations, facilities and the current recommended route.</p></div><span className="simulated-pill"><span /> PRESENTATION-ONLY LAYOUT</span></div>
              <ParkingMap facilities={facilities} routePath={selectedRecommendation?.routePath || []} selectedParkingId={selectedParkingId} onSelect={setSelectedParkingId} />
            </section>
          )}
          {isAdmin && activeView === "simulation" && (
            <SimulationControl facilities={facilities} busy={eventBusy} feedback={eventFeedback} onVehicleEvent={handleVehicleEvent} />
          )}
          {activeView === "details" && (
            <ParkingDetails facilities={facilities} parkingId={selectedParkingId} recommendations={recommendation.results} onSelectParking={setSelectedParkingId} />
          )}
          <footer className="page-footer"><span>ParkSmart AI</span><span>Campus parking management · Simulated data only</span></footer>
        </div>
      </main>
    </div>
  );
}

export default CampusPortal;
