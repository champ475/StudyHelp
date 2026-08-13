import { useState } from "react";
import type { Column, SubtractColumnFields } from "../../types";
import { ColumnPicker } from "./ColumnPicker";
import { DigitPad } from "./DigitPad";

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
      <DigitPad label="Top digit (after any borrowing)" value={minuendDigit} onChange={setMinuendDigit} />
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
