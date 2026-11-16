import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  fetchCurrentUser,
  getAuthToken,
  login as requestLogin,
  registerAccount,
  revokeSession,
  setAuthToken,
} from "../services/backendApiAdapter.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    if (!getAuthToken()) {
      setLoading(false);
      return () => { active = false; };
    }

    fetchCurrentUser()
      .then((currentUser) => {
        if (active) setUser(currentUser);
      })
      .catch(() => {
        setAuthToken(null);
        if (active) setUser(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, []);

  const login = useCallback(async (credentials) => {
    const response = await requestLogin(credentials);
    setAuthToken(response.accessToken);
    setUser(response.user);
    return response.user;
  }, []);

  const register = useCallback((credentials) => registerAccount(credentials), []);

  const logout = useCallback(async () => {
    let logoutError;
    try {
      await revokeSession();
    } catch (error) {
      logoutError = error;
    } finally {
      setAuthToken(null);
      setUser(null);
    }
    if (logoutError) throw logoutError;
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider.");
  return value;
}
