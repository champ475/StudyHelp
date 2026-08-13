export interface ChatMessage {
  id: string;
  text: string;
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
        <div key={message.id} className="chat-message tutor">
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
