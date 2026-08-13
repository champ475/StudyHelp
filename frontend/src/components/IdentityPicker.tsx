import { useState } from "react";

interface IdentityPickerProps {
  onCreate: (displayName: string) => void;
  isCreating: boolean;
}

// Dev-mode only (ARCHITECTURE.md D18) — a local name picker for testing
// the pipeline, not a real account/consent flow. Real student data
// collection is gated on DPDP legal review; this must never be pointed at
// actual children.
export function IdentityPicker({ onCreate, isCreating }: IdentityPickerProps) {
  const [name, setName] = useState("");

  return (
    <div className="identity-picker">
      <h2>Who&apos;s solving today?</h2>
      <p className="dev-mode-notice">
        Dev mode only — a local name picker for testing, not a real account or consent flow.
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (name.trim()) onCreate(name.trim());
        }}
      >
        <input
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Type a name"
          aria-label="Your name"
        />
        <button type="submit" disabled={!name.trim() || isCreating}>
          {isCreating ? "Starting…" : "Start"}
        </button>
      </form>
    </div>
  );
}
