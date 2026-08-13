interface BooleanToggleProps {
  label: string;
  value: boolean | null;
  onChange: (value: boolean) => void;
  yesLabel?: string;
  noLabel?: string;
}

export function BooleanToggle({
  label,
  value,
  onChange,
  yesLabel = "Yes",
  noLabel = "No",
}: BooleanToggleProps) {
  return (
    <fieldset className="boolean-toggle">
      <legend>{label}</legend>
      <div>
        <button
          type="button"
          className={value === true ? "toggle-button selected" : "toggle-button"}
          aria-pressed={value === true}
          onClick={() => onChange(true)}
        >
          {yesLabel}
        </button>
        <button
          type="button"
          className={value === false ? "toggle-button selected" : "toggle-button"}
          aria-pressed={value === false}
          onClick={() => onChange(false)}
        >
          {noLabel}
        </button>
      </div>
    </fieldset>
  );
}
