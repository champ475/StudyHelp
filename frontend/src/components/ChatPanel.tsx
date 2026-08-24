import { getDiagramRenderer } from "../diagrams";
import type { PublicProblem } from "../types";

export interface ChatMessage {
  id: string;
  text: string;
  // Which step attempt this tutor message belongs to — the count of
  // already-accepted steps at the moment the student's (wrong) submission
  // that triggered it was sent. Lets ProblemSolver/FreeTextStepper render
  // each explanation directly under the step attempt it responds to,
  // instead of grouping every message into one block at the bottom
  // (CLAUDE.md Bug4: UI order should match the real event order).
  stepIndex: number;
  // True only for the one-off post-resolution "think about why that
  // works" aside (backend's `turn_complete` "resolved" event with a
  // non-null message). Rendered visibly differently from a normal
  // explanation bubble — lighter, with a reflective marker — so it never
  // reads as a question the student must answer before they can continue
  // (CLAUDE.md open-ended-review Issue C: there is no input path for a
  // reply to it; the next step's input box is already active regardless).
  isReflection?: boolean;
  // Mirrors the backend's `turn_complete.diagram_hint` (deterministic, see
  // `dialogue/diagram_hint.py`) — when true, this bubble re-shows the
  // problem's own diagram (same renderer/`given` as `DiagramPanel`, never
  // new answer-revealing content) as a visual aid for this specific error.
  showDiagram?: boolean;
  // `symmetry`-only, user-directed exception (see backend's
  // `dialogue/diagram_hint.py::should_reveal_symmetry_lines()` and
  // `types.ts`'s `TurnComplete.diagram_hint_reveal_answer`): when set,
  // `showDiagram`'s renderer draws the actual line(s) of symmetry instead
  // of the bare shape. `undefined`/`null` for every other topic.
  revealAnswer?: string | null;
}

interface ChatPanelProps {
  messages: ChatMessage[];
  isThinking: boolean;
  // Only needed to look up/re-render the topic's existing diagram for a
  // `showDiagram` message — same `given`, same renderer as the problem
  // header's `DiagramPanel`, so no new component/leakage surface here.
  problem: PublicProblem;
}

// Messages here only ever come from "message_chunk"/"turn_complete" SSE
// events — the only event types carrying LLM-generated, gate-cleared text
// (see api/client.ts, backend api/routes/sessions.py). Nothing rendered
// here is a speculative, unvetted draft.
export function ChatPanel({ messages, isThinking, problem }: ChatPanelProps) {
  const DiagramRenderer = getDiagramRenderer(problem.ncert_ref.topic);
  return (
    <div className="chat-panel" aria-live="polite" aria-label="Tutor messages">
      {messages.map((message) => {
        const hintDiagram =
          message.showDiagram && DiagramRenderer
            ? DiagramRenderer({ given: problem.given, revealAnswer: message.revealAnswer ?? null })
            : null;
        return (
          <div
            key={message.id}
            className={`chat-message tutor${message.isReflection ? " reflection" : ""}`}
          >
            {message.isReflection && <span className="reflection-marker" aria-hidden="true">💭 </span>}
            {message.text}
            {hintDiagram && <div className="diagram-panel diagram-hint">{hintDiagram}</div>}
          </div>
        );
      })}
      {isThinking && (
        <div className="chat-message thinking" aria-label="Tutor is thinking">
          <span className="thinking-dot" />
          <span className="thinking-dot" />
          <span className="thinking-dot" />
        </div>
      )}
    </div>
  );
}
