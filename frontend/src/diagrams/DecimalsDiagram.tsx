import type { DiagramProps } from "./types";

function toDecimalParts(hundredths: number): { whole: string; frac: string } {
  const whole = Math.trunc(hundredths / 100);
  const frac = String(Math.abs(hundredths) % 100).padStart(2, "0");
  return { whole: String(whole), frac };
}

// `given.a_hundredths`/`given.b_hundredths` are the problem's own two
// stated decimal numbers (visible input), never the computed result.
export function DecimalsDiagram({ given }: DiagramProps): JSX.Element | null {
  const aH = given.a_hundredths;
  const bH = given.b_hundredths;
  if (typeof aH !== "number" || typeof bH !== "number") return null;
  const a = toDecimalParts(aH);
  const b = toDecimalParts(bH);
  const op = given.op === "-" ? "−" : "+";

  const row = (whole: string, frac: string, sign?: string) => (
    <div className="diagram-column-row">
      <span className="diagram-column-sign">{sign ?? ""}</span>
      <span className="diagram-column-digit">{whole}</span>
      <span className="diagram-column-digit diagram-decimal-point">.</span>
      {frac.split("").map((digit, index) => (
        <span key={index} className="diagram-column-digit">
          {digit}
        </span>
      ))}
    </div>
  );

  return (
    <div className="diagram-columns" role="img" aria-label={`${a.whole}.${a.frac} ${op} ${b.whole}.${b.frac}`}>
      {row(a.whole, a.frac)}
      {row(b.whole, b.frac, op)}
      <div className="diagram-column-line" style={{ width: "7rem" }} />
    </div>
  );
}
