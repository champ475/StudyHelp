import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DiagramPanel } from "./DiagramPanel";
import type { PublicProblem } from "../types";

function problemWith(topic: string, given: Record<string, unknown>): PublicProblem {
  return {
    problem_id: "p1",
    ncert_ref: { class: 5, chapter: 1, chapter_title: "Test", topic },
    display_label: "Test problem",
    given,
    step_graph: [],
    alt_paths: [],
  };
}

describe("DiagramPanel", () => {
  it("renders a labeled rectangle for area_perimeter from given.length/width", () => {
    const { container } = render(
      <DiagramPanel
        problem={problemWith("area_perimeter", {
          shape: "rectangle",
          length: 6,
          width: 4,
          measure: "area",
        })}
      />,
    );
    expect(container.querySelector("svg")).toBeInTheDocument();
    expect(container.textContent).toContain("length 6");
    expect(container.textContent).toContain("width 4");
    // Must never show the computed area (24) — not in `given` at all, but
    // guard the rendered text explicitly in case a future edit adds it.
    expect(container.textContent).not.toContain("24");
  });

  it("renders place-value columns for subtraction_with_borrowing from given.minuend/subtrahend", () => {
    const { container } = render(
      <DiagramPanel problem={problemWith("subtraction_with_borrowing", { minuend: 52, subtrahend: 25 })} />,
    );
    expect(container.textContent).toContain("5");
    expect(container.textContent).toContain("2");
    expect(container.textContent).not.toContain("27"); // the answer
  });

  it("renders a division bracket layout for multiplication_division when op is '/'", () => {
    const { container } = render(
      <DiagramPanel problem={problemWith("multiplication_division", { a: 84, b: 4, op: "/" })} />,
    );
    expect(container.querySelector(".diagram-division")).toBeInTheDocument();
    expect(container.textContent).not.toContain("21"); // the quotient
  });

  it("renders stacked columns for multiplication_division when op is 'x'", () => {
    const { container } = render(
      <DiagramPanel problem={problemWith("multiplication_division", { a: 34, b: 6, op: "x" })} />,
    );
    expect(container.querySelector(".diagram-columns")).toBeInTheDocument();
    expect(container.textContent).not.toContain("204"); // the product
  });

  it("renders decimal place-value columns for decimals", () => {
    const { container } = render(
      <DiagramPanel
        problem={problemWith("decimals", { a_hundredths: 340, b_hundredths: 125, op: "+" })}
      />,
    );
    expect(container.textContent).toContain("3");
    expect(container.textContent).toContain(".");
    expect(container.textContent).not.toContain("465"); // the sum, in hundredths
  });

  it("renders two fraction circles for fractions_addition, without asserting an operator", () => {
    const { container } = render(
      <DiagramPanel
        problem={problemWith("fractions_addition", { a_num: 1, a_den: 4, b_num: 1, b_den: 6 })}
      />,
    );
    expect(container.querySelectorAll("path").length).toBeGreaterThan(0);
    expect(container.textContent).toContain("1/4");
    expect(container.textContent).toContain("1/6");
  });

  it("renders a labeled Venn diagram for lcm_hcf using given.op as the question label, not the answer", () => {
    const { container } = render(<DiagramPanel problem={problemWith("lcm_hcf", { a: 12, b: 18, op: "hcf" })} />);
    expect(container.textContent).toContain("HCF?");
    expect(container.textContent).not.toContain("6"); // the actual HCF
  });

  it("renders a from-to arrow for measurement, and given never includes the answer-bearing direction/factor", () => {
    const { container } = render(
      <DiagramPanel
        problem={problemWith("measurement", {
          value: 3,
          from_unit: "km",
          to_unit: "m",
          category: "length",
          // Deliberately no `direction`/`factor` — the backend redacts
          // them (ARCHITECTURE.md D75); this test documents that the
          // diagram must render sensibly even without them.
        })}
      />,
    );
    expect(container.textContent).toContain("3 km");
    expect(container.textContent).toContain("? m");
  });

  it("renders the question-card fallback for every light-check topic", () => {
    for (const topic of [
      "shapes_angles",
      "how_many_squares",
      "symmetry",
      "patterns",
      "mapping",
      "boxes_sketches",
      "smart_charts",
    ]) {
      const { container, unmount } = render(
        <DiagramPanel problem={problemWith(topic, { question: "An angle measures 30 degrees." })} />,
      );
      expect(container.querySelector(".diagram-question-card")).toBeInTheDocument();
      expect(container.textContent).toContain("An angle measures 30 degrees.");
      unmount();
    }
  });

  it("renders nothing for an unregistered topic", () => {
    const { container } = render(<DiagramPanel problem={problemWith("not_a_real_topic", {})} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when a registered topic's given doesn't have the expected shape", () => {
    const { container } = render(<DiagramPanel problem={problemWith("area_perimeter", {})} />);
    expect(container).toBeEmptyDOMElement();
  });
});
