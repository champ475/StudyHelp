// Tap +/- to adjust a value that can exceed a single digit (e.g. a
// just-borrowed column can briefly hold 10-19) — still no typing.

interface StepperProps {
  label: string;
  value: number | null;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
}

export function Stepper({ label, value, onChange, min = 0, max = 19 }: StepperProps) {
  const current = value ?? min;
  return (
    <fieldset className="stepper">
      <legend>{label}</legend>
      <div className="stepper-controls">
        <button
          type="button"
          aria-label={`Decrease ${label}`}
          disabled={value !== null && current <= min}
          onClick={() => onChange(Math.max(min, current - 1))}
        >
          −
        </button>
        <output aria-live="polite">{value === null ? "?" : value}</output>
        <button
          type="button"
          aria-label={`Increase ${label}`}
          disabled={value !== null && current >= max}
          onClick={() => onChange(Math.min(max, current + 1))}
        >
          +
        </button>
      </div>
    </fieldset>
  );
}
