import type { DiagramProps } from "./types";

// `given` for shapes_angles is a single free-text `question` string (no
// structured numeric fields — unlike the 7 heavy-DAG topics; see
// `QuestionCardDiagram`'s docstring on why that fallback existed). This
// topic's seed set uses a small, closed vocabulary ("N degrees", or one of
// a handful of named shapes), so — unlike free-form prose in general — a
// narrow regex extraction over that closed set is safe: it can only ever
// pull out a value ALREADY stated in the visible question text, never
// compute or guess one, and any question it doesn't recognize falls through
// to `null` (same fallback contract as every other renderer) rather than
// mis-rendering. Never draws the classification/count itself (that's
// `final_answer`, never sent to the browser at all).
function extractDegrees(question: string): number | null {
  const match = question.match(/(\d+)\s*degrees?/i);
  if (!match) return null;
  const value = Number(match[1]);
  return Number.isFinite(value) ? value : null;
}

const SHAPE_KEYWORDS: Record<string, "square" | "rectangle" | "triangle" | "pentagon"> = {
  square: "square",
  rectangle: "rectangle",
  triangle: "triangle",
  pentagon: "pentagon",
};

function extractShape(question: string): "square" | "rectangle" | "triangle" | "pentagon" | null {
  const lower = question.toLowerCase();
  for (const [keyword, shape] of Object.entries(SHAPE_KEYWORDS)) {
    if (lower.includes(keyword)) return shape;
  }
  return null;
}

function AngleArc({ degrees }: { degrees: number }): JSX.Element {
  const cx = 90;
  const cy = 110;
  const radius = 70;
  const clamped = Math.max(0, Math.min(360, degrees));
  const endAngleRad = (-clamped * Math.PI) / 180;
  const endX = cx + radius * Math.cos(endAngleRad);
  const endY = cy + radius * Math.sin(endAngleRad);
  const largeArc = clamped > 180 ? 1 : 0;

  return (
    <svg
      viewBox="0 0 200 140"
      role="img"
      aria-label={`Angle of ${degrees} degrees`}
      className="diagram-svg"
    >
      <line x1={cx} y1={cy} x2={cx + radius} y2={cy} stroke="#166534" strokeWidth={2} />
      <line x1={cx} y1={cy} x2={endX} y2={endY} stroke="#166534" strokeWidth={2} />
      <path
        d={`M ${cx + 24} ${cy} A 24 24 0 ${largeArc} 0 ${cx + 24 * Math.cos(endAngleRad)} ${
          cy + 24 * Math.sin(endAngleRad)
        }`}
        fill="none"
        stroke="#b45309"
        strokeWidth={2}
      />
      <text x={cx} y={cy + 12} textAnchor="middle" className="diagram-label">
        {degrees}°
      </text>
    </svg>
  );
}

function ShapeOutline({ shape }: { shape: "square" | "rectangle" | "triangle" | "pentagon" }): JSX.Element {
  const label = shape.charAt(0).toUpperCase() + shape.slice(1);
  let path: JSX.Element;
  switch (shape) {
    case "square":
      path = <rect x={50} y={20} width={80} height={80} fill="#dcfce7" stroke="#166534" strokeWidth={2} />;
      break;
    case "rectangle":
      path = <rect x={30} y={35} width={120} height={60} fill="#dcfce7" stroke="#166534" strokeWidth={2} />;
      break;
    case "triangle":
      path = (
        <polygon points="90,20 30,100 150,100" fill="#dcfce7" stroke="#166534" strokeWidth={2} />
      );
      break;
    case "pentagon":
      path = (
        <polygon
          points="90,15 150,60 128,125 52,125 30,60"
          fill="#dcfce7"
          stroke="#166534"
          strokeWidth={2}
        />
      );
      break;
  }
  return (
    <svg viewBox="0 0 180 140" role="img" aria-label={label} className="diagram-svg">
      {path}
    </svg>
  );
}

export function ShapesAnglesDiagram({ given }: DiagramProps): JSX.Element | null {
  const question = given.question;
  if (typeof question !== "string" || !question.trim()) return null;

  const degrees = extractDegrees(question);
  if (degrees !== null) return <AngleArc degrees={degrees} />;

  const shape = extractShape(question);
  if (shape !== null) return <ShapeOutline shape={shape} />;

  return null;
}
