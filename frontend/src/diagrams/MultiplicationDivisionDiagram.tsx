import type { DiagramProps } from "./types";

// `given.a`/`given.b`/`given.op` are the problem's own stated numbers and
// operation ("x" | "/") — visible input, not the product/quotient the
// student has to work out.
export function MultiplicationDivisionDiagram({ given }: DiagramProps): JSX.Element | null {
  const a = given.a;
  const b = given.b;
  if (typeof a !== "number" || typeof b !== "number") return null;
  const isDivide = given.op === "/";

  if (isDivide) {
    return (
      <div className="diagram-division" role="img" aria-label={`${a} divided by ${b}`}>
        <span className="diagram-division-divisor">{b}</span>
        <span className="diagram-division-bracket">
          <span className="diagram-division-dividend">{a}</span>
        </span>
      </div>
    );
  }

  const topDigits = String(a).split("");
  return (
    <div className="diagram-columns" role="img" aria-label={`${a} multiplied by ${b}`}>
      <div className="diagram-column-row">
        <span className="diagram-column-sign" />
        {topDigits.map((digit, index) => (
          <span key={index} className="diagram-column-digit">
            {digit}
          </span>
        ))}
      </div>
      <div className="diagram-column-row">
        <span className="diagram-column-sign">&times;</span>
        <span className="diagram-column-digit">{b}</span>
      </div>
      <div className="diagram-column-line" style={{ width: `${(topDigits.length + 1) * 1.6}rem` }} />
    </div>
  );
}
