import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

vi.mock("react-leaflet", async () => import("./mocks/reactLeaflet.jsx"));
vi.mock("leaflet", () => ({
  default: {
    divIcon: (options) => ({ options }),
  },
}));

afterEach(() => {
  cleanup();
});
