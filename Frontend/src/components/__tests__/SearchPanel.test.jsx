import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import SearchPanel from "../SearchPanel.jsx";

function renderSearchPanel() {
  const onSearch = vi.fn();
  const user = userEvent.setup();

  const { container } = render(<SearchPanel onSearch={onSearch} />);

  return { container, onSearch, user };
}

describe("SearchPanel validation", () => {
  it("reports an empty destination and missing arrival time", async () => {
    const { container, onSearch, user } = renderSearchPanel();

    await user.click(screen.getByRole("button", { name: "Find parking" }));

    expect(screen.getByText("Enter a destination to continue.")).toBeInTheDocument();
    expect(screen.getByText("Choose a valid arrival date and time.")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /YOUR DESTINATION/ })).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(container.querySelector('input[name="arrival-time"]')).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(onSearch).toHaveBeenLastCalledWith(null);
  });

  it("rejects a whitespace-only destination", async () => {
    const { onSearch, user } = renderSearchPanel();

    await user.type(screen.getByLabelText("YOUR DESTINATION"), "   ");
    await user.type(screen.getByLabelText("ARRIVAL TIME"), "2026-10-25T10:30");
    await user.click(screen.getByRole("button", { name: "Find parking" }));

    expect(screen.getByText("Enter a destination to continue.")).toBeInTheDocument();
    expect(screen.queryByText("Choose a valid arrival date and time.")).not.toBeInTheDocument();
    expect(onSearch).toHaveBeenLastCalledWith(null);
  });

  it("reports a missing arrival time when the destination is valid", async () => {
    const { onSearch, user } = renderSearchPanel();

    await user.type(screen.getByLabelText("YOUR DESTINATION"), "Central Library");
    await user.click(screen.getByRole("button", { name: "Find parking" }));

    expect(screen.getByText("Choose a valid arrival date and time.")).toBeInTheDocument();
    expect(screen.queryByText("Enter a destination to continue.")).not.toBeInTheDocument();
    expect(onSearch).toHaveBeenLastCalledWith(null);
  });

  it("passes trimmed search criteria when both fields are valid", async () => {
    const { onSearch, user } = renderSearchPanel();

    await user.type(screen.getByLabelText("YOUR DESTINATION"), "  Central Library  ");
    await user.type(screen.getByLabelText("ARRIVAL TIME"), "2026-10-25T10:30");
    await user.click(screen.getByRole("button", { name: "Find parking" }));

    expect(onSearch).toHaveBeenLastCalledWith({
      destination: "Central Library",
      arrivalTime: "2026-10-25T10:30",
    });
    expect(screen.getByText(/parking recommendations have not been retrieved/i)).toBeInTheDocument();
  });
});
