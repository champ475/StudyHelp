import { useState } from "react";
import type { Column, WriteFinalAnswerFields } from "../../types";
import { DigitPad } from "./DigitPad";

const COLUMN_PLACE_VALUE: Record<Column, number> = {
  units: 1,
  tens: 10,
  hundreds: 100,
  thousands: 1000,
  ten_thousands: 10000,
  lakhs: 100000,
};

const COLUMNS_WIDEST_FIRST: Column[] = ["thousands", "hundreds", "tens", "units"];

interface WriteFinalAnswerWidgetProps {
  onSubmit: (fields: WriteFinalAnswerFields) => void;
  disabled: boolean;
}

export function WriteFinalAnswerWidget({ onSubmit, disabled }: WriteFinalAnswerWidgetProps) {
  const [digits, setDigits] = useState<Partial<Record<Column, number>>>({});

  const isComplete = digits.units !== undefined;

  return (
    <div className="step-widget">
      <h3>Write the final answer</h3>
      <p className="widget-hint">
        Fill in each column&apos;s digit. Skip a column at the front if you don&apos;t need it.
      </p>
      {COLUMNS_WIDEST_FIRST.map((column) => (
        <DigitPad
          key={column}
          label={column.charAt(0).toUpperCase() + column.slice(1)}
          value={digits[column] ?? null}
          onChange={(digit) => setDigits((prev) => ({ ...prev, [column]: digit }))}
        />
      ))}
      <button
        type="button"
        className="submit-button"
        disabled={disabled || !isComplete}
        onClick={() => {
          if (!isComplete) return;
          const value = (Object.entries(digits) as [Column, number][]).reduce(
            (sum, [column, digit]) => sum + digit * COLUMN_PLACE_VALUE[column],
            0,
          );
          onSubmit({ digits, value });
        }}
      >
        Submit
      </button>
    </div>
  );
}
