import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CompareColumnWidget } from "./CompareColumnWidget";

describe("CompareColumnWidget", () => {
  it("disables submit until every field is set, then submits structured fields", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<CompareColumnWidget onSubmit={onSubmit} disabled={false} />);

    const submit = screen.getByRole("button", { name: "Submit" });
    expect(submit).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Units" }));
    expect(submit).toBeDisabled();

    const minuendGroup = screen.getByRole("group", { name: "Top digit (minuend)" });
    await user.click(within(minuendGroup).getByRole("button", { name: "2" }));

    const subtrahendGroup = screen.getByRole("group", { name: "Bottom digit (subtrahend)" });
    await user.click(within(subtrahendGroup).getByRole("button", { name: "5" }));
    expect(submit).toBeDisabled(); // borrow_needed still unset

    await user.click(screen.getByRole("button", { name: "Yes" }));
    expect(submit).toBeEnabled();

    await user.click(submit);
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({
      column: "units",
      minuend_digit: 2,
      subtrahend_digit: 5,
      borrow_needed: true,
    });
  });

  it("never emits a raw string for a digit field — always a number", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<CompareColumnWidget onSubmit={onSubmit} disabled={false} />);

    await user.click(screen.getByRole("button", { name: "Tens" }));
    const minuendGroup = screen.getByRole("group", { name: "Top digit (minuend)" });
    await user.click(within(minuendGroup).getByRole("button", { name: "7" }));
    const subtrahendGroup = screen.getByRole("group", { name: "Bottom digit (subtrahend)" });
    await user.click(within(subtrahendGroup).getByRole("button", { name: "3" }));
    await user.click(screen.getByRole("button", { name: "No" }));
    await user.click(screen.getByRole("button", { name: "Submit" }));

    const [[submitted]] = onSubmit.mock.calls as [[{ minuend_digit: unknown }]];
    expect(typeof submitted.minuend_digit).toBe("number");
  });

  it("stays disabled while the disabled prop is true even with all fields set", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<CompareColumnWidget onSubmit={onSubmit} disabled={true} />);

    await user.click(screen.getByRole("button", { name: "Units" }));
    const minuendGroup = screen.getByRole("group", { name: "Top digit (minuend)" });
    await user.click(within(minuendGroup).getByRole("button", { name: "2" }));
    const subtrahendGroup = screen.getByRole("group", { name: "Bottom digit (subtrahend)" });
    await user.click(within(subtrahendGroup).getByRole("button", { name: "5" }));
    await user.click(screen.getByRole("button", { name: "Yes" }));

    expect(screen.getByRole("button", { name: "Submit" })).toBeDisabled();
  });
});
