import { useState } from "react";
import type { Column, CompareColumnFields } from "../../types";
import { BooleanToggle } from "./BooleanToggle";
import { ColumnPicker } from "./ColumnPicker";
import { DigitPad } from "./DigitPad";

interface CompareColumnWidgetProps {
  onSubmit: (fields: CompareColumnFields) => void;
  disabled: boolean;
}

export function CompareColumnWidget({ onSubmit, disabled }: CompareColumnWidgetProps) {
  const [column, setColumn] = useState<Column | null>(null);
  const [minuendDigit, setMinuendDigit] = useState<number | null>(null);
  const [subtrahendDigit, setSubtrahendDigit] = useState<number | null>(null);
  const [borrowNeeded, setBorrowNeeded] = useState<boolean | null>(null);

  const isComplete =
    column !== null && minuendDigit !== null && subtrahendDigit !== null && borrowNeeded !== null;

  return (
    <div className="step-widget">
      <h3>Compare a column</h3>
      <ColumnPicker label="Which column?" value={column} onChange={setColumn} />
      <DigitPad label="Top digit (minuend)" value={minuendDigit} onChange={setMinuendDigit} />
      <DigitPad label="Bottom digit (subtrahend)" value={subtrahendDigit} onChange={setSubtrahendDigit} />
      <BooleanToggle label="Do we need to borrow?" value={borrowNeeded} onChange={setBorrowNeeded} />
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
            borrow_needed: borrowNeeded,
          });
        }}
      >
        Submit
      </button>
    </div>
  );
}
