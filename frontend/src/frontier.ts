// Mirrors the backend verifier's `_frontier()` (SubtractionBorrowingVerifier)
// purely to decide which widget(s) to *offer* the student next — it has no
// bearing on correctness. The backend re-derives its own frontier
// independently from `accepted_step_ids` on every submission and is the
// only source of truth for whether a step is actually valid (D1); this is
// UI convenience only.

import type { PublicProblem, PublicStepNode } from "./types";

export function computeFrontier(problem: PublicProblem, acceptedStepIds: string[]): PublicStepNode[] {
  if (acceptedStepIds.length === 0) {
    const entryIds = new Set<string>(problem.alt_paths.map((path) => path.entry));
    const first = problem.step_graph[0];
    if (first) entryIds.add(first.step_id);
    return problem.step_graph.filter((node) => entryIds.has(node.step_id));
  }

  const frontierIds = new Set<string>();
  const byId = new Map(problem.step_graph.map((node) => [node.step_id, node]));
  for (const stepId of acceptedStepIds) {
    const node = byId.get(stepId);
    if (!node) continue;
    for (const nextId of node.next) frontierIds.add(nextId);
  }
  return problem.step_graph.filter((node) => frontierIds.has(node.step_id));
}
