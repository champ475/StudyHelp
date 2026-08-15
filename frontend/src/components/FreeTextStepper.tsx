// Free-text step input (ARCHITECTURE.md D41, superseding D12/D32's
// structured-widget default project-wide): one text box per step instead
// of a math-aware structured widget, universal across every topic. Each
// already-accepted step renders as a locked, read-only box; the one active
// box is where the student types the *next* step. Committing it (Enter, or
// the "Next step" button) is the moment verification happens — "mistake
// checking happens when I move to next step" — and a wrong submission
// keeps the box open (re-editable, re-verified on retry) with the
// interrupt/dialogue rendered immediately below it, rather than silently
// advancing.
//
// Topic-agnostic by construction: the only per-topic content is `hint`,
// which the backend supplies per step type (PublicStepNode.hint, sourced
// from that step type's seed-authored `step_types.description`) — this
// component never hardcodes a topic's shape.

interface FreeTextStepperProps {
  lockedTexts: string[];
  activeText: string;
  onActiveTextChange: (text: string) => void;
  onCommit: () => void;
  disabled: boolean;
  solved: boolean;
  hint?: string;
}

export function FreeTextStepper({
  lockedTexts,
  activeText,
  onActiveTextChange,
  onCommit,
  disabled,
  solved,
  hint,
}: FreeTextStepperProps) {
  return (
    <div className="free-text-stepper">
      {lockedTexts.map((text, index) => (
        <div key={index} className="free-text-step locked">
          <span className="step-number">Step {index + 1}</span>
          <input value={text} readOnly disabled className="free-text-input locked" />
          <span className="step-check" aria-label="Correct">
            ✓
          </span>
        </div>
      ))}
      {!solved && (
        <div className="free-text-step active">
          {hint && <p className="step-hint">{hint}</p>}
          <div className="free-text-step-row">
            <span className="step-number">Step {lockedTexts.length + 1}</span>
            <input
              value={activeText}
              onChange={(event) => onActiveTextChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  onCommit();
                }
              }}
              disabled={disabled}
              placeholder={hint || "Type this step"}
              className="free-text-input"
              aria-label={`Step ${lockedTexts.length + 1} input`}
              autoFocus
            />
            <button
              type="button"
              className="submit-button"
              onClick={onCommit}
              disabled={disabled || !activeText.trim()}
            >
              Next step →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
