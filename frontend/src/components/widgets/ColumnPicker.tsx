import type { Column } from "../../types";

const COLUMNS: { value: Column; label: string }[] = [
  { value: "units", label: "Units" },
  { value: "tens", label: "Tens" },
  { value: "hundreds", label: "Hundreds" },
  { value: "thousands", label: "Thousands" },
];

interface ColumnPickerProps {
  label: string;
  value: Column | null;
  onChange: (value: Column) => void;
}

export function ColumnPicker({ label, value, onChange }: ColumnPickerProps) {
  return (
    <fieldset className="column-picker">
      <legend>{label}</legend>
      <div>
        {COLUMNS.map((column) => (
          <button
            key={column.value}
            type="button"
            className={column.value === value ? "column-button selected" : "column-button"}
            aria-pressed={column.value === value}
            onClick={() => onChange(column.value)}
          >
            {column.label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
