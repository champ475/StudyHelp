import { useState } from "react";
import type { BorrowFields, Column } from "../../types";
import { ColumnPicker } from "./ColumnPicker";
import { Stepper } from "./Stepper";

interface BorrowWidgetProps {
  onSubmit: (fields: BorrowFields) => void;
  disabled: boolean;
}

export function BorrowWidget({ onSubmit, disabled }: BorrowWidgetProps) {
  const [fromColumn, setFromColumn] = useState<Column | null>(null);
  const [fromBefore, setFromBefore] = useState<number | null>(null);
  const [fromAfter, setFromAfter] = useState<number | null>(null);
  const [toColumn, setToColumn] = useState<Column | null>(null);
  const [toBefore, setToBefore] = useState<number | null>(null);
  const [toAfter, setToAfter] = useState<number | null>(null);

  const isComplete =
    fromColumn !== null &&
    fromBefore !== null &&
    fromAfter !== null &&
    toColumn !== null &&
    toBefore !== null &&
    toAfter !== null;

  return (
    <div className="step-widget">
      <h3>Borrow a ten</h3>
      <p className="widget-hint">Which column are you borrowing from, and which is receiving it?</p>
      <ColumnPicker label="Borrow from" value={fromColumn} onChange={setFromColumn} />
      <Stepper label="That column, before" value={fromBefore} onChange={setFromBefore} />
      <Stepper label="That column, after" value={fromAfter} onChange={setFromAfter} />
      <ColumnPicker label="Borrow into" value={toColumn} onChange={setToColumn} />
      <Stepper label="That column, before" value={toBefore} onChange={setToBefore} />
      <Stepper label="That column, after" value={toAfter} onChange={setToAfter} />
      <button
        type="button"
        className="submit-button"
        disabled={disabled || !isComplete}
        onClick={() => {
          if (!isComplete) return;
          onSubmit({
            from_column: fromColumn,
            from_digit_before: fromBefore,
            from_digit_after: fromAfter,
            to_column: toColumn,
            to_digit_before: toBefore,
            to_digit_after: toAfter,
          });
        }}
      >
        Submit
      </button>
    </div>
  );
}
