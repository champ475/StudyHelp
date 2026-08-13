// Tap-to-select single digit (0-9) — no typing (D13: minimize keystrokes
// for this age group; Shih et al. 2023 found keyboard input "time-consuming
// and inconvenient" for young learners in a real deployment).

interface DigitPadProps {
  label: string;
  value: number | null;
  onChange: (value: number) => void;
}

export function DigitPad({ label, value, onChange }: DigitPadProps) {
  const digits = Array.from({ length: 10 }, (_, i) => i);
  return (
    <fieldset className="digit-pad">
      <legend>{label}</legend>
      <div className="digit-pad-grid">
        {digits.map((digit) => (
          <button
            key={digit}
            type="button"
            className={digit === value ? "digit-button selected" : "digit-button"}
            aria-pressed={digit === value}
            onClick={() => onChange(digit)}
          >
            {digit}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
