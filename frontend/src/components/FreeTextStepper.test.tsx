import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FreeTextStepper } from "./FreeTextStepper";

describe("FreeTextStepper", () => {
  it("shows the per-topic hint as both a helper line and the input placeholder", () => {
    render(
      <FreeTextStepper
        lockedTexts={[]}
        activeText=""
        onActiveTextChange={vi.fn()}
        onCommit={vi.fn()}
        disabled={false}
        solved={false}
        hint="Rewrite both fractions with a common denominator."
      />,
    );
    expect(
      screen.getByText("Rewrite both fractions with a common denominator."),
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("Rewrite both fractions with a common denominator."),
    ).toBeInTheDocument();
  });

  it("falls back to a generic placeholder when no hint is supplied — never hardcodes a topic's shape", () => {
    render(
      <FreeTextStepper
        lockedTexts={[]}
        activeText=""
        onActiveTextChange={vi.fn()}
        onCommit={vi.fn()}
        disabled={false}
        solved={false}
      />,
    );
    expect(screen.getByPlaceholderText("Type this step")).toBeInTheDocument();
  });

  it("commits on Enter and on the button click, but not while empty", async () => {
    const onCommit = vi.fn();
    const user = userEvent.setup();
    render(
      <FreeTextStepper
        lockedTexts={["1/4 + 1/6"]}
        activeText="3/12 + 2/12"
        onActiveTextChange={vi.fn()}
        onCommit={onCommit}
        disabled={false}
        solved={false}
      />,
    );

    expect(screen.getByDisplayValue("1/4 + 1/6")).toBeDisabled();

    const active = screen.getByLabelText("Step 2 input");
    await user.type(active, "{Enter}");
    expect(onCommit).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "Next step →" }));
    expect(onCommit).toHaveBeenCalledTimes(2);
  });

  it("renders each step's tutor messages directly below that step, not grouped at the end (Bug4)", () => {
    render(
      <FreeTextStepper
        lockedTexts={["units 2 < 7"]}
        activeText="12 - 7 = 4"
        onActiveTextChange={vi.fn()}
        onCommit={vi.fn()}
        disabled={false}
        solved={false}
        messagesByStepIndex={[
          [{ id: "m1", text: "Explanation for step 1's wrong attempt.", stepIndex: 0 }],
          [{ id: "m2", text: "Explanation for the current step's wrong attempt.", stepIndex: 1 }],
        ]}
      />,
    );

    const container = screen.getByText("Explanation for step 1's wrong attempt.").closest(
      ".free-text-stepper",
    ) as HTMLElement;
    const blocks = Array.from(container.children);
    // Block order must be [locked step 1, its explanation, active step,
    // its explanation] — the real event order, not all steps then all
    // explanations.
    expect(blocks).toHaveLength(2);
    const [firstBlock, secondBlock] = blocks as [HTMLElement, HTMLElement];
    expect(within(firstBlock).getByDisplayValue("units 2 < 7")).toBeInTheDocument();
    expect(firstBlock.textContent).toContain("Explanation for step 1's wrong attempt.");
    expect(within(secondBlock).getByDisplayValue("12 - 7 = 4")).toBeInTheDocument();
    expect(secondBlock.textContent).toContain("Explanation for the current step's wrong attempt.");
  });

  it("renders no active box once solved, only locked history", () => {
    render(
      <FreeTextStepper
        lockedTexts={["1/4 + 1/6", "5/12"]}
        activeText=""
        onActiveTextChange={vi.fn()}
        onCommit={vi.fn()}
        disabled={false}
        solved={true}
      />,
    );
    expect(screen.queryByRole("button", { name: "Next step →" })).not.toBeInTheDocument();
    expect(screen.getAllByLabelText("Correct")).toHaveLength(2);
  });
});
