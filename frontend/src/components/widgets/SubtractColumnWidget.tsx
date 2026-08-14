import { useState } from "react";
import type { Column, SubtractColumnFields } from "../../types";
import { ColumnPicker } from "./ColumnPicker";
import { DigitPad } from "./DigitPad";
import { Stepper } from "./Stepper";

interface SubtractColumnWidgetProps {
  onSubmit: (fields: SubtractColumnFields) => void;
  disabled: boolean;
}

export function SubtractColumnWidget({ onSubmit, disabled }: SubtractColumnWidgetProps) {
  const [column, setColumn] = useState<Column | null>(null);
  const [minuendDigit, setMinuendDigit] = useState<number | null>(null);
  const [subtrahendDigit, setSubtrahendDigit] = useState<number | null>(null);
  const [resultDigit, setResultDigit] = useState<number | null>(null);

  const isComplete =
    column !== null && minuendDigit !== null && subtrahendDigit !== null && resultDigit !== null;

  return (
    <div className="step-widget">
      <h3>Subtract a column</h3>
      <ColumnPicker label="Which column?" value={column} onChange={setColumn} />
      {/* A borrowed column's top digit can be 10-19 (e.g. 12) — a single
          DigitPad (0-9) can't represent that, so this field uses the
          same +/- Stepper as BorrowWidget's two-digit-range fields.
          Caught by driving the actual UI as a real user would (a wrong
          step following any borrow was previously impossible to
          submit correctly) — see CHANGELOG. */}
      <Stepper label="Top digit (after any borrowing)" value={minuendDigit} onChange={setMinuendDigit} />
      <DigitPad label="Bottom digit" value={subtrahendDigit} onChange={setSubtrahendDigit} />
      <DigitPad label="Your answer for this column" value={resultDigit} onChange={setResultDigit} />
      <button
        type="button"
        className="submit-button"
        disabled={disabled || !isComplete}
        onClick={() => {
          if (!isComplete) return;
          onSubmit({
            column,
            minuend_digit: minuendDigit,
            subtrahend_digit: subtrahendDigit,
            result_digit: resultDigit,
          });
        }}
      >
        Submit
      </button>
    </div>
  );
}
