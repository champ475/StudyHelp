import type { DiagramProps } from "./types";

// Labeled rectangle from `given.length`/`given.width` — both genuine,
// visible input (the problem's own stated dimensions), never the computed
// area/perimeter value (never in `given`, and even if it were,
// `_public_given()` would have redacted it). `given.measure` ("area" |
// "perimeter") only changes which visual cue is drawn (a light interior
// fill vs. a highlighted border) — it never reveals a number.
export function AreaPerimeterDiagram({ given }: DiagramProps): JSX.Element | null {
  const length = Number(given.length);
  const width = Number(given.width);
  if (!Number.isFinite(length) || !Number.isFinite(width) || length <= 0 || width <= 0) {
    return null;
  }
  const measure = given.measure === "perimeter" ? "perimeter" : "area";
  const maxSide = 120;
  const scale = maxSide / Math.max(length, width);
  const w = Math.max(30, width * scale);
  const h = Math.max(30, length * scale);
  const topPadding = 24;
  // Wider than `topPadding` — the left-side "length N" label is drawn
  // right-anchored at `leftPadding - 8`, and needs room for its own text
  // width or it clips off the SVG's left edge (found live via a browser
  // screenshot: "length 6" rendered as "ıgth 6", the leading characters cut
  // off outside the viewBox).
  const leftPadding = 56;
  const viewW = w + leftPadding + 24;
  const viewH = h + topPadding * 2;

  return (
    <svg
      viewBox={`0 0 ${viewW} ${viewH}`}
      role="img"
      aria-label={`Rectangle with length ${length} and width ${width}`}
      className="diagram-svg"
    >
      <rect
        x={leftPadding}
        y={topPadding}
        width={w}
        height={h}
        fill={measure === "area" ? "#dcfce7" : "none"}
        stroke="#166534"
        strokeWidth={measure === "perimeter" ? 4 : 2}
        strokeDasharray={measure === "perimeter" ? "6 4" : undefined}
      />
      <text x={leftPadding + w / 2} y={topPadding - 8} textAnchor="middle" className="diagram-label">
        width {width}
      </text>
      <text
        x={leftPadding - 8}
        y={topPadding + h / 2}
        textAnchor="end"
        dominantBaseline="middle"
        className="diagram-label"
      >
        length {length}
      </text>
    </svg>
  );
}
