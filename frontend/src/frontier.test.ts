import { describe, expect, it } from "vitest";
import { computeFrontier } from "./frontier";
import type { PublicProblem } from "./types";

const problem: PublicProblem = {
  problem_id: "p",
  ncert_ref: { class: 5, chapter: 1, chapter_title: "x", topic: "subtraction_with_borrowing" },
  display_label: "52 − 25",
  given: { minuend: 52, subtrahend: 25 },
  step_graph: [
    { step_id: "s1", type: "compare_column", next: ["s2"], hint: "Compare the units column." },
    { step_id: "s2", type: "borrow", next: ["s3"], hint: "Borrow from the next column." },
    { step_id: "s3", type: "subtract_column", next: [], hint: "Subtract the units column." },
  ],
  alt_paths: [],
};

describe("computeFrontier", () => {
  it("starts at the first node when nothing is accepted", () => {
    expect(computeFrontier(problem, []).map((node) => node.type)).toEqual(["compare_column"]);
  });

  it("advances to the next node's type once a step is accepted", () => {
    expect(computeFrontier(problem, ["s1"]).map((node) => node.type)).toEqual(["borrow"]);
  });

  it("includes alt-path entries alongside the canonical first node", () => {
    const withAlt: PublicProblem = { ...problem, alt_paths: [{ path_id: "alt", entry: "s2" }] };
    expect(computeFrontier(withAlt, []).map((node) => node.type)).toEqual(
      expect.arrayContaining(["compare_column", "borrow"]),
    );
  });

  it("returns nothing when the only accepted step is a terminal node", () => {
    // s3.next is []; a lone accepted terminal contributes nothing new.
    expect(computeFrontier(problem, ["s3"])).toEqual([]);
  });

  it("still nominally includes already-accepted steps reachable via another accepted step's `next`", () => {
    // Mirrors the backend verifier's _frontier() exactly (union of every
    // accepted step's `next`, with no exclusion of already-accepted
    // nodes) — s1's `next` still contributes s2, s2's still contributes
    // s3, even once all three are accepted. This is intentional, not a
    // bug: frontier membership only affects which candidate is preferred
    // among several exact field matches, never whether a step is valid.
    const frontier = computeFrontier(problem, ["s1", "s2", "s3"]);
    expect(frontier.map((node) => node.step_id)).toEqual(["s2", "s3"]);
  });

  it("ignores an unknown accepted step id rather than throwing", () => {
    expect(() => computeFrontier(problem, ["not-a-real-step"])).not.toThrow();
  });
});
