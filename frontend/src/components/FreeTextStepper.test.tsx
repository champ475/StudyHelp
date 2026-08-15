import { render, screen } from "@testing-library/react";
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
