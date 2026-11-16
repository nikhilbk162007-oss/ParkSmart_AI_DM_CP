import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  fetchCurrentUser,
  fetchParkingFacilities,
  login,
  revokeSession,
  setAuthToken,
} from "./backendApiAdapter.js";

describe("backend authentication adapter", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses the current bearer token for protected API requests", async () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => [],
    });
    setAuthToken("session-token");

    await fetchParkingFacilities();

    const [, options] = fetch.mock.calls[0];
    expect(options.headers.get("Authorization")).toBe("Bearer session-token");
  });

  it("keeps login public and clears stored tokens on logout", async () => {
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ accessToken: "new-token", user: { username: "reader", role: "user" } }),
    });
    await login({ username: "reader", password: "example-password" });
    expect(fetch.mock.calls[0][1].headers.has("Authorization")).toBe(false);

    setAuthToken("session-token");
    fetch.mockResolvedValue({
      ok: true,
      status: 204,
    });
    await revokeSession();
    expect(fetch.mock.calls[1][1].headers.get("Authorization")).toBe("Bearer session-token");
    setAuthToken(null);
    expect(window.sessionStorage.getItem("parksmart.accessToken")).toBeNull();
    fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ username: "reader", role: "user" }),
    });
    await fetchCurrentUser();
    expect(fetch.mock.calls[2][1].headers.has("Authorization")).toBe(false);
  });
});
