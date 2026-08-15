import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import App from "./App";
import * as client from "./api/client";
import type { ProblemSummary, PublicProblem } from "./types";

const PROBLEMS: ProblemSummary[] = [
  {
    problem_id: "subtraction-borrow-001",
    ncert_ref: { class: 5, chapter: 1, chapter_title: "The Fish Tale", topic: "subtraction_with_borrowing" },
    display_label: "52 − 25 (single borrow)",
  },
  {
    problem_id: "fractions-add-001",
    ncert_ref: { class: 5, chapter: 4, chapter_title: "Parts and Wholes", topic: "fractions_addition" },
    display_label: "1/4 + 1/6",
  },
];

const PUBLIC_PROBLEM: PublicProblem = {
  problem_id: "subtraction-borrow-001",
  ncert_ref: { class: 5, chapter: 1, chapter_title: "The Fish Tale", topic: "subtraction_with_borrowing" },
  display_label: "52 − 25 (single borrow)",
  given: { minuend: 52, subtrahend: 25 },
  step_graph: [
    { step_id: "s1", type: "compare_column", next: [], hint: "Compare the units column." },
  ],
  alt_paths: [],
};

describe("App", () => {
  it("groups the problem catalog by chapter and lets the student pick one", async () => {
    vi.spyOn(client, "fetchProblems").mockResolvedValue(PROBLEMS);
    vi.spyOn(client, "createSession").mockResolvedValue({ session_id: "s1", user_id: "u1" });
    vi.spyOn(client, "fetchProblem").mockResolvedValue(PUBLIC_PROBLEM);

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText("Your name"), "Asha");
    await user.click(screen.getByRole("button", { name: "Start" }));

    await waitFor(() => expect(screen.getByText("Chapter:")).toBeInTheDocument());

    const chapterSelect = screen.getByLabelText("Chapter:");
    const chapterOptions = within(chapterSelect).getAllByRole("option").map((o) => o.textContent);
    expect(chapterOptions).toEqual(["1. The Fish Tale", "4. Parts and Wholes"]);

    const problemSelect = screen.getByLabelText("Problem:");
    expect(within(problemSelect).getByRole("option", { name: "52 − 25 (single borrow)" })).toBeInTheDocument();

    // The selected problem's own display_label is what ProblemSolver renders
    // as its heading -- confirms the catalog selection actually drives the
    // loaded problem, not just the picker UI.
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "52 − 25 (single borrow)" })).toBeInTheDocument(),
    );
  });
});
