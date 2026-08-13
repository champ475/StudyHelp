import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StepWidgetSwitcher } from "./StepWidgetSwitcher";

describe("StepWidgetSwitcher", () => {
  it("shows a message when no known step types are available", () => {
    render(<StepWidgetSwitcher availableStepTypes={[]} onSubmit={vi.fn()} disabled={false} />);
    expect(screen.getByText(/no more steps available/i)).toBeInTheDocument();
  });

  it("filters out unknown step types rather than rendering nothing useful", () => {
    render(
      <StepWidgetSwitcher
        availableStepTypes={["not_a_real_type", "compare_column"]}
        onSubmit={vi.fn()}
        disabled={false}
      />,
    );
    expect(screen.getByText("Compare a column")).toBeInTheDocument();
  });

  it("renders tabs and switches widgets when multiple step types are reachable", async () => {
    const user = userEvent.setup();
    render(
      <StepWidgetSwitcher
        availableStepTypes={["compare_column", "borrow"]}
        onSubmit={vi.fn()}
        disabled={false}
      />,
    );
    expect(screen.getByText("Compare a column")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Borrow" }));
    expect(screen.getByText("Borrow a ten")).toBeInTheDocument();
  });

  it("renders no tabs when only one step type is reachable", () => {
    render(
      <StepWidgetSwitcher availableStepTypes={["subtract_column"]} onSubmit={vi.fn()} disabled={false} />,
    );
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
  });
});
