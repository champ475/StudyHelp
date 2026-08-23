import type { DiagramProps } from "./types";

// Place-value column layout from `given.minuend`/`given.subtrahend` —
// both genuine visible input (the two numbers the problem states), never
// the per-column borrow/result digits the student has to work out.
export function SubtractionDiagram({ given }: DiagramProps): JSX.Element | null {
  const minuend = given.minuend;
  const subtrahend = given.subtrahend;
  if (typeof minuend !== "number" || typeof subtrahend !== "number") return null;

  const topDigits = String(minuend).split("");
  const bottomRaw = String(subtrahend).split("");
  const width = Math.max(topDigits.length, bottomRaw.length);
  const bottomDigits = Array(width - bottomRaw.length)
    .fill("")
    .concat(bottomRaw);
  const topPadded = Array(width - topDigits.length)
    .fill("")
    .concat(topDigits);

  return (
    <div className="diagram-columns" role="img" aria-label={`${minuend} minus ${subtrahend}`}>
      <div className="diagram-column-row">
        <span className="diagram-column-sign" />
        {topPadded.map((digit, index) => (
          <span key={index} className="diagram-column-digit">
            {digit}
          </span>
        ))}
      </div>
      <div className="diagram-column-row">
        <span className="diagram-column-sign">&minus;</span>
        {bottomDigits.map((digit, index) => (
          <span key={index} className="diagram-column-digit">
            {digit}
          </span>
        ))}
      </div>
      <div className="diagram-column-line" style={{ width: `${(width + 1) * 1.6}rem` }} />
    </div>
  );
}
