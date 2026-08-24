import type { DiagramProps } from "./types";

// `given.a`/`given.b` are the problem's own two stated numbers;
// `given.op` ("lcm" | "hcf") is which computation the problem ASKS for —
// visible input describing the question itself (like the display label
// already says, e.g. "HCF of 12 and 18"), never the computed answer.
export function LcmHcfDiagram({ given }: DiagramProps): JSX.Element | null {
  const a = given.a;
  const b = given.b;
  if (typeof a !== "number" || typeof b !== "number") return null;
  const label = given.op === "lcm" ? "LCM" : "HCF";

  return (
    <svg viewBox="0 0 220 135" role="img" aria-label={`${label} of ${a} and ${b}`} className="diagram-svg">
      <circle cx={85} cy={55} r={48} fill="#fef3c7" stroke="#b45309" strokeWidth={2} fillOpacity={0.7} />
      <circle cx={135} cy={55} r={48} fill="#dbeafe" stroke="#1d4ed8" strokeWidth={2} fillOpacity={0.7} />
      <text x={55} y={59} textAnchor="middle" className="diagram-label-strong">
        {a}
      </text>
      <text x={165} y={59} textAnchor="middle" className="diagram-label-strong">
        {b}
      </text>
      {/* Below both circles entirely (bottom tangent is at cy + r = 103),
          not overlapping their intersection — an earlier version placed
          this at the tangent point itself, hard to read against the
          overlapping fill (found live via a browser screenshot). */}
      <text x={110} y={122} textAnchor="middle" className="diagram-label">
        {label}?
      </text>
    </svg>
  );
}
