import { useEffect, useState } from "react";
import type { StepType, StudentStep } from "../types";
import { BorrowWidget } from "./widgets/BorrowWidget";
import { CompareColumnWidget } from "./widgets/CompareColumnWidget";
import { SubtractColumnWidget } from "./widgets/SubtractColumnWidget";
import { WriteFinalAnswerWidget } from "./widgets/WriteFinalAnswerWidget";

const STEP_TYPE_LABELS: Record<StepType, string> = {
  compare_column: "Compare",
  borrow: "Borrow",
  subtract_column: "Subtract",
  write_final_answer: "Final Answer",
};

function isKnownStepType(value: string): value is StepType {
  return value in STEP_TYPE_LABELS;
}

// The widgets emit their own precisely-typed field shapes
// (CompareColumnFields, BorrowFields, ...); StudentStep.fields is
// necessarily loose (Record<string, unknown>) since it's the wire format
// for *any* step type. This is the one, explicit, intentional widening —
// not a loss of type safety at the point the fields are actually built.
function toWireFields<T extends object>(fields: T): Record<string, unknown> {
  return fields as unknown as Record<string, unknown>;
}

interface StepWidgetSwitcherProps {
  availableStepTypes: string[];
  onSubmit: (step: StudentStep) => void;
  disabled: boolean;
  /** The step type that naturally follows the most recently *accepted*
   * step, if any. `availableStepTypes` deliberately still includes
   * already-completed-but-nominally-reachable types (ARCHITECTURE.md
   * D11's non-exclusion frontier) — without this hint, the switcher's
   * default tab stays on whichever type happens to sort first, which
   * can mean staying stuck on a step the student already completed
   * instead of advancing. Caught by actually watching the app run: a
   * student who correctly finished "Borrow" was left looking at the
   * Borrow widget again instead of moving on to Subtract. */
  preferredStepType?: string;
}

// The student can pick among every step type currently reachable in the
// graph (the DAG-not-list requirement, ARCHITECTURE.md D11) — not forced
// down one prescribed path.
export function StepWidgetSwitcher({
  availableStepTypes,
  onSubmit,
  disabled,
  preferredStepType,
}: StepWidgetSwitcherProps) {
  const validTypes = availableStepTypes.filter(isKnownStepType);
  const [active, setActive] = useState<StepType | null>(validTypes[0] ?? null);

  useEffect(() => {
    if (preferredStepType && isKnownStepType(preferredStepType)) {
      setActive(preferredStepType);
    }
    // Only re-run when the *preferred* type changes (i.e. a new step was
    // just accepted) — not on every availableStepTypes recompute, so a
    // manual tab click mid-fill-in isn't immediately overridden.
  }, [preferredStepType]);

  if (validTypes.length === 0) {
    return <p className="no-steps-available">No more steps available for this problem.</p>;
  }
  const current = active !== null && validTypes.includes(active) ? active : validTypes[0];

  return (
    <div className="step-widget-switcher">
      {validTypes.length > 1 && (
        <div className="step-type-tabs" role="tablist">
          {validTypes.map((stepType) => (
            <button
              key={stepType}
              type="button"
              role="tab"
              aria-selected={stepType === current}
              onClick={() => setActive(stepType)}
            >
              {STEP_TYPE_LABELS[stepType]}
            </button>
          ))}
        </div>
      )}
      {current === "compare_column" && (
        <CompareColumnWidget
          disabled={disabled}
          onSubmit={(fields) => onSubmit({ step_type: "compare_column", fields: toWireFields(fields) })}
        />
      )}
      {current === "borrow" && (
        <BorrowWidget
          disabled={disabled}
          onSubmit={(fields) => onSubmit({ step_type: "borrow", fields: toWireFields(fields) })}
        />
      )}
      {current === "subtract_column" && (
        <SubtractColumnWidget
          disabled={disabled}
          onSubmit={(fields) => onSubmit({ step_type: "subtract_column", fields: toWireFields(fields) })}
        />
      )}
      {current === "write_final_answer" && (
        <WriteFinalAnswerWidget
          disabled={disabled}
          onSubmit={(fields) =>
            onSubmit({ step_type: "write_final_answer", fields: toWireFields(fields) })
          }
        />
      )}
    </div>
  );
}
