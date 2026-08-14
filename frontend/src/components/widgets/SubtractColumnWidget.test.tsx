import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SubtractColumnWidget } from "./SubtractColumnWidget";

describe("SubtractColumnWidget", () => {
  it("lets the minuend digit go above 9 (a borrowed column, e.g. 12) — regression for a real bug", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<SubtractColumnWidget onSubmit={onSubmit} disabled={false} />);

    // Must NOT be a DigitPad (which only offers 0-9) for this field —
    // caught by actually driving the UI: after any borrow, minuend_digit
    // is legitimately 10-19 and was previously impossible to enter.
    expect(screen.queryByRole("button", { name: "12" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Units" }));

    const increase = screen.getByRole("button", {
      name: "Increase Top digit (after any borrowing)",
    });
    for (let i = 0; i < 12; i++) {
      await user.click(increase);
    }
    expect(screen.getByText("12")).toBeInTheDocument();

    const subtrahendGroup = screen.getByRole("group", { name: "Bottom digit" });
    await user.click(within(subtrahendGroup).getByRole("button", { name: "5" }));
    const resultGroup = screen.getByRole("group", { name: "Your answer for this column" });
    await user.click(within(resultGroup).getByRole("button", { name: "7" }));

    await user.click(screen.getByRole("button", { name: "Submit" }));
    expect(onSubmit).toHaveBeenCalledWith({
      column: "units",
      minuend_digit: 12,
      subtrahend_digit: 5,
      result_digit: 7,
    });
  });
});
