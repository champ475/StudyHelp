import { getDiagramRenderer } from "../diagrams";
import type { PublicProblem } from "../types";

interface DiagramPanelProps {
  problem: PublicProblem;
}

// Renders the topic-appropriate visual aid for the current problem, built
// only from `problem.given` (already leakage-safe — see
// `api/routes/problems.py::_public_given()`, ARCHITECTURE.md D75). A
// renderer can legitimately return `null` (given shape doesn't match what
// it expects, or the light-check fallback has no `question` text) — in
// that case this panel renders nothing rather than an empty box.
export function DiagramPanel({ problem }: DiagramPanelProps): JSX.Element | null {
  const Renderer = getDiagramRenderer(problem.ncert_ref.topic);
  if (!Renderer) return null;
  const diagram = Renderer({ given: problem.given });
  if (!diagram) return null;
  return <div className="diagram-panel">{diagram}</div>;
}
