import type { DiagramProps } from "./types";

// `given.value`/`from_unit`/`to_unit` are the problem's own stated
// conversion (visible input). `given.direction`/`factor` are DELIBERATELY
// absent here — they're the exact answer to this problem's first step
// (`identify_conversion_factor`) and are redacted server-side
// (`api/routes/problems.py::_public_given()`, ARCHITECTURE.md D75) before
// `given` ever reaches the browser, so this diagram never had access to
// them in the first place — it can only ever draw the question, never the
// answer.
export function MeasurementDiagram({ given }: DiagramProps): JSX.Element | null {
  const value = given.value;
  const fromUnit = given.from_unit;
  const toUnit = given.to_unit;
  if (typeof value !== "number" || typeof fromUnit !== "string" || typeof toUnit !== "string") {
    return null;
  }
  return (
    <svg
      viewBox="0 0 240 70"
      role="img"
      aria-label={`Convert ${value} ${fromUnit} to ${toUnit}`}
      className="diagram-svg"
    >
      <text x={10} y={40} className="diagram-label-strong">
        {value} {fromUnit}
      </text>
      <line x1={95} y1={35} x2={150} y2={35} stroke="#57534e" strokeWidth={2} markerEnd="url(#arrow)" />
      <defs>
        <marker id="arrow" markerWidth={8} markerHeight={8} refX={6} refY={3} orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="#57534e" />
        </marker>
      </defs>
      <text x={160} y={40} className="diagram-label-strong">
        ? {toUnit}
      </text>
    </svg>
  );
}
