import type { DiagramProps } from "./types";

// Fallback for the 7 light-check topics (shapes_angles, how_many_squares,
// symmetry, patterns, mapping, boxes_sketches, smart_charts). Their
// `given` is a single free-text `question` string (e.g. "An angle
// measures 30 degrees. Classify it...") with no structured numeric fields
// — unlike the 7 heavy-DAG topics, there's nothing here to build a
// data-driven geometric/numeric diagram FROM without regex-guessing
// numbers out of prose, which would be fragile and could misrender a
// question it parsed wrong (worse than no diagram at all). Scoped down
// deliberately (per this round's own instructions) to an honest visual
// treatment of the question itself — a styled callout, not a fabricated
// picture — rather than forcing a diagram that isn't really data-driven.
export function QuestionCardDiagram({ given }: DiagramProps): JSX.Element | null {
  const question = given.question;
  if (typeof question !== "string" || !question.trim()) return null;
  return (
    <div className="diagram-question-card" role="img" aria-label="Problem question">
      <span className="diagram-question-icon" aria-hidden="true">
        🔍
      </span>
      <p>{question}</p>
    </div>
  );
}
