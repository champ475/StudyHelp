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
}

interface ChatPanelProps {
  messages: ChatMessage[];
  isThinking: boolean;
}

// Messages here only ever come from "message_chunk"/"turn_complete" SSE
// events — the only event types carrying LLM-generated, gate-cleared text
// (see api/client.ts, backend api/routes/sessions.py). Nothing rendered
// here is a speculative, unvetted draft.
export function ChatPanel({ messages, isThinking }: ChatPanelProps) {
  return (
    <div className="chat-panel" aria-live="polite" aria-label="Tutor messages">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`chat-message tutor${message.isReflection ? " reflection" : ""}`}
        >
          {message.isReflection && <span className="reflection-marker" aria-hidden="true">💭 </span>}
          {message.text}
        </div>
      ))}
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
