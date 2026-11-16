import { useState } from "react";
import { CircleParking, LockKeyhole } from "lucide-react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

function LoginPage({ registration = false }) {
  const { user, loading, login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [success, setSuccess] = useState(location.state?.message || "");

  if (!loading && user) {
    return <Navigate to={user.role === "admin" ? "/admin" : "/user"} replace />;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setBusy(true);
    try {
      if (registration) {
        await register({ username, password });
        setSuccess("Account created. Sign in to open the User Portal.");
        navigate("/login", { replace: true, state: { message: "Account created. Sign in to open the User Portal." } });
      } else {
        const signedInUser = await login({ username, password });
        navigate(signedInUser.role === "admin" ? "/admin" : "/user", { replace: true });
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to complete the request.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel" aria-labelledby="auth-title">
        <div className="auth-brand">
          <span className="brand-mark"><CircleParking size={22} strokeWidth={2} /></span>
          <span className="brand-name">ParkSmart<span>AI</span></span>
        </div>
        <p className="eyebrow">UNIVERSITY CAMPUS PARKING</p>
        <h1 id="auth-title">{registration ? "Create your account" : "Welcome back"}</h1>
        <p className="auth-copy">
          {registration
            ? "Register for a regular user account. Administrator access is provisioned separately."
            : "Sign in to view campus parking availability and recommendations."}
        </p>
        {success && <p className="auth-feedback success" role="status">{success}</p>}
        {error && <p className="auth-feedback error" role="alert">{error}</p>}
        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="form-field">
            <span>Username</span>
            <input
              autoComplete="username"
              maxLength={64}
              minLength={3}
              onChange={(event) => setUsername(event.target.value)}
              required
              value={username}
            />
          </label>
          <label className="form-field">
            <span>Password</span>
            <input
              autoComplete={registration ? "new-password" : "current-password"}
              maxLength={128}
              minLength={registration ? 12 : 1}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
            {registration && <small>Use at least 12 characters.</small>}
          </label>
          <button className="button button-primary auth-submit" disabled={busy || loading} type="submit">
            <LockKeyhole size={16} />
            {busy ? "Please wait…" : registration ? "Create user account" : "Sign in"}
          </button>
        </form>
        <p className="auth-switch">
          {registration ? "Already registered? " : "New to ParkSmart AI? "}
          <Link to={registration ? "/login" : "/register"}>
            {registration ? "Sign in" : "Create a user account"}
          </Link>
        </p>
        <p className="auth-note">Campus occupancy is simulated; no live sensor data is connected.</p>
      </section>
    </main>
  );
}

export default LoginPage;
