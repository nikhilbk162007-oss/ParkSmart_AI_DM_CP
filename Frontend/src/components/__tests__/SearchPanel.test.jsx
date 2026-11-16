import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import SearchPanel from "../SearchPanel.jsx";

describe("SearchPanel", () => {
  it("submits a supported campus destination, gate, and vehicle type", async () => {
    const user = userEvent.setup();
    const onSearch = vi.fn();
    render(<SearchPanel onSearch={onSearch} searchStatus="idle" />);

    await user.selectOptions(screen.getByLabelText("Destination"), "Sports Complex");
    await user.selectOptions(screen.getByLabelText("Entry gate"), "gate_south");
    await user.selectOptions(screen.getByLabelText("Vehicle type"), "two-wheeler");
    await user.click(screen.getByRole("button", { name: /find parking/i }));

    expect(onSearch).toHaveBeenCalledWith({
      destination: "Sports Complex",
      entryGate: "gate_south",
      vehicleType: "two-wheeler",
    });
    expect(screen.getAllByRole("option")).toHaveLength(9);
  });

  it("prevents duplicate searches while the request is loading", () => {
    render(<SearchPanel onSearch={() => {}} searchStatus="loading" />);
    expect(screen.getByRole("button", { name: /searching/i })).toBeDisabled();
  });
});
