import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext.jsx";
import CampusPortal from "./CampusPortal.jsx";
import LoginPage from "./components/LoginPage.jsx";

function RequireAuthentication({ children, adminOnly = false }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <main className="auth-page"><p className="subtle-copy">Restoring session…</p></main>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (adminOnly && user.role !== "admin") return <Navigate to="/user" replace />;
  return children;
}

function PortalRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <main className="auth-page"><p className="subtle-copy">Restoring session…</p></main>;
  return <Navigate to={user ? (user.role === "admin" ? "/admin" : "/user") : "/login"} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<LoginPage registration />} />
          <Route path="/user/*" element={<RequireAuthentication><CampusPortal isAdmin={false} /></RequireAuthentication>} />
          <Route path="/admin/*" element={<RequireAuthentication adminOnly><CampusPortal isAdmin /></RequireAuthentication>} />
          <Route path="/" element={<PortalRedirect />} />
          <Route path="*" element={<PortalRedirect />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
