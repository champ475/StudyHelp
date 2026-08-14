import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
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

  it("advances to preferredStepType when it changes, even though the just-completed type is still nominally reachable — regression for a real UX bug", async () => {
    // Reproduces ProblemSolver's real shape: the backend's frontier
    // intentionally still includes an already-accepted step's type
    // (ARCHITECTURE.md D11 — no exclusion), so after finishing "borrow"
    // both "borrow" and "subtract_column" remain in availableStepTypes.
    // Without a preferredStepType hint, a student who just correctly
    // finished Borrow was left looking at the Borrow widget again.
    function Harness() {
      const [step, setStep] = useState<"initial" | "after_borrow">("initial");
      return (
        <>
          <button onClick={() => setStep("after_borrow")}>simulate accepting the borrow step</button>
          <StepWidgetSwitcher
            availableStepTypes={["borrow", "subtract_column"]}
            preferredStepType={step === "after_borrow" ? "subtract_column" : undefined}
            onSubmit={vi.fn()}
            disabled={false}
          />
        </>
      );
    }
    const user = userEvent.setup();
    render(<Harness />);
    expect(screen.getByText("Borrow a ten")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /simulate accepting/i }));
    expect(screen.getByText("Subtract a column")).toBeInTheDocument();
    expect(screen.queryByText("Borrow a ten")).not.toBeInTheDocument();
  });
});
