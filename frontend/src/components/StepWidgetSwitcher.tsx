import { useState } from "react";
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
}

// The student can pick among every step type currently reachable in the
// graph (the DAG-not-list requirement, ARCHITECTURE.md D11) — not forced
// down one prescribed path.
export function StepWidgetSwitcher({
  availableStepTypes,
  onSubmit,
  disabled,
}: StepWidgetSwitcherProps) {
  const validTypes = availableStepTypes.filter(isKnownStepType);
  const [active, setActive] = useState<StepType | null>(validTypes[0] ?? null);

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
