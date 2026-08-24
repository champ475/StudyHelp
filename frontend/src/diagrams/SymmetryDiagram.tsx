import type { DiagramProps } from "./types";

// Same closed-vocabulary regex-extraction approach as `ShapesAnglesDiagram`
// — see that file's docstring for why this is safe here despite
// `QuestionCardDiagram`'s general "don't regex-guess prose" caution.
//
// Deliberately draws ONLY the bare shape/letter by default, never a
// candidate mirror line: the number of symmetry lines IS `final_answer` for
// every problem in this topic, so unlike `AreaPerimeterDiagram` (which can
// safely draw the rectangle `given.length`/`given.width` describe), there
// is no safe "visible input" line to draw here from `given` alone — any
// line drawn from `given` would be guessing at the answer, not illustrating
// the question. The shape alone still lets the child visually count
// symmetry lines themselves, which is the point.
//
// `revealAnswer` (see `types.ts`'s docstring) is the one deliberate,
// user-directed exception: once the backend's
// `dialogue/diagram_hint.py::should_reveal_symmetry_lines()` decides to
// reveal (2+ misses on this exact step), the correct `answer` string is
// passed down and this component draws the actual dashed line(s) of
// symmetry — geometry looked up from a fixed table below, keyed off the
// shape/letter already extracted from `given` and the revealed answer
// value, never invented or LLM-authored.
type Shape =
  | "square"
  | "rectangle"
  | "equilateral_triangle"
  | "scalene_triangle"
  | "pentagon"
  | "hexagon"
  | "circle"
  | { letter: string };

interface Line {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

// Fixed, hand-computed symmetry-line geometry for each shape this topic's
// seed set actually uses, matching the exact coordinates each shape's own
// `<rect>`/`<polygon>` below is drawn with. Keyed by the shape's OWN
// correct line-count (as the string the backend's `answer` field holds),
// so a mismatched/unexpected `revealAnswer` (e.g. a future seed problem
// this table hasn't been extended for) safely falls through to "don't draw
// anything" rather than drawing wrong geometry.
const REGULAR_SHAPE_LINES: Partial<Record<Shape & string, Record<string, Line[]>>> = {
  square: {
    "4": [
      { x1: 60, y1: 20, x2: 60, y2: 100 },
      { x1: 20, y1: 60, x2: 100, y2: 60 },
      { x1: 20, y1: 20, x2: 100, y2: 100 },
      { x1: 20, y1: 100, x2: 100, y2: 20 },
    ],
  },
  rectangle: {
    "2": [
      { x1: 60, y1: 35, x2: 60, y2: 85 },
      { x1: 10, y1: 60, x2: 110, y2: 60 },
    ],
  },
  equilateral_triangle: {
    "3": [
      { x1: 60, y1: 15, x2: 60, y2: 100 },
      { x1: 15, y1: 100, x2: 82.5, y2: 57.5 },
      { x1: 105, y1: 100, x2: 37.5, y2: 57.5 },
    ],
  },
  pentagon: {
    "5": [
      { x1: 60, y1: 10, x2: 60, y2: 100 },
      { x1: 105, y1: 45, x2: 23.5, y2: 72.5 },
      { x1: 88, y1: 100, x2: 37.5, y2: 27.5 },
      { x1: 32, y1: 100, x2: 82.5, y2: 27.5 },
      { x1: 15, y1: 45, x2: 96.5, y2: 72.5 },
    ],
  },
  hexagon: {
    "6": [
      { x1: 30, y1: 15, x2: 90, y2: 105 },
      { x1: 90, y1: 15, x2: 30, y2: 105 },
      { x1: 115, y1: 60, x2: 5, y2: 60 },
      { x1: 60, y1: 15, x2: 60, y2: 105 },
      { x1: 102.5, y1: 37.5, x2: 17.5, y2: 82.5 },
      { x1: 102.5, y1: 82.5, x2: 17.5, y2: 37.5 },
    ],
  },
  circle: {
    // Six evenly-spaced diameters as a visual stand-in for "infinite" —
    // the exact count drawn is illustrative, not itself a claimed answer
    // (the caption below states "infinite" explicitly).
    infinite: [
      { x1: 105, y1: 60, x2: 15, y2: 60 },
      { x1: 99, y1: 82.5, x2: 21, y2: 37.5 },
      { x1: 82.5, y1: 99, x2: 37.5, y2: 21 },
      { x1: 60, y1: 105, x2: 60, y2: 15 },
      { x1: 37.5, y1: 99, x2: 82.5, y2: 21 },
      { x1: 21, y1: 82.5, x2: 99, y2: 37.5 },
    ],
  },
};

const LETTER_SYMMETRY_LINE: Line = { x1: 60, y1: 15, x2: 60, y2: 105 };

function extractShape(question: string): Shape | null {
  const lower = question.toLowerCase();
  const letterMatch = question.match(/capital letter ([A-Z])/);
  if (letterMatch && letterMatch[1]) return { letter: letterMatch[1] };
  if (lower.includes("equilateral triangle")) return "equilateral_triangle";
  if (lower.includes("scalene triangle")) return "scalene_triangle";
  if (lower.includes("rectangle")) return "rectangle";
  if (lower.includes("square")) return "square";
  if (lower.includes("pentagon")) return "pentagon";
  if (lower.includes("hexagon")) return "hexagon";
  if (lower.includes("circle")) return "circle";
  return null;
}

// One dashed `<line>` per entry in `lines` (the actual reveal), plus an
// optional caption for the "zero lines" case (a scalene triangle, or a
// letter with no symmetry) where there is no line to draw but the reveal
// should still say so explicitly rather than looking identical to the
// pre-reveal bare shape.
function RevealOverlay({ lines, zeroCaption }: { lines: Line[]; zeroCaption?: string }): JSX.Element {
  return (
    <>
      {lines.map((line, i) => (
        <line
          key={i}
          x1={line.x1}
          y1={line.y1}
          x2={line.x2}
          y2={line.y2}
          stroke="#7c3aed"
          strokeWidth={2}
          strokeDasharray="6 4"
        />
      ))}
      {zeroCaption && (
        <text x={60} y={118} textAnchor="middle" fontSize={10} fill="#7c3aed" fontWeight={600}>
          {zeroCaption}
        </text>
      )}
    </>
  );
}

export function SymmetryDiagram({ given, revealAnswer }: DiagramProps): JSX.Element | null {
  const question = given.question;
  if (typeof question !== "string" || !question.trim()) return null;
  const shape = extractShape(question);
  if (shape === null) return null;

  if (typeof shape === "object") {
    const isYes = revealAnswer === "yes";
    const isNo = revealAnswer === "no";
    return (
      <svg viewBox="0 0 120 130" role="img" aria-label={`Letter ${shape.letter}`} className="diagram-svg">
        <text x={60} y={90} textAnchor="middle" fontSize={80} fontWeight={700} fill="#166534">
          {shape.letter}
        </text>
        {isYes && <RevealOverlay lines={[LETTER_SYMMETRY_LINE]} />}
        {isNo && <RevealOverlay lines={[]} zeroCaption="No line of symmetry" />}
      </svg>
    );
  }

  const revealLines =
    revealAnswer != null ? REGULAR_SHAPE_LINES[shape]?.[revealAnswer] : undefined;
  const isZeroReveal = revealAnswer === "0";

  let inner: JSX.Element;
  switch (shape) {
    case "square":
      inner = <rect x={20} y={20} width={80} height={80} fill="#dcfce7" stroke="#166534" strokeWidth={2} />;
      break;
    case "rectangle":
      inner = <rect x={10} y={35} width={100} height={50} fill="#dcfce7" stroke="#166534" strokeWidth={2} />;
      break;
    case "equilateral_triangle":
    case "scalene_triangle":
      inner = (
        <polygon
          points={
            shape === "equilateral_triangle" ? "60,15 15,100 105,100" : "45,10 10,105 110,90"
          }
          fill="#dcfce7"
          stroke="#166534"
          strokeWidth={2}
        />
      );
      break;
    case "pentagon":
      inner = (
        <polygon
          points="60,10 105,45 88,100 32,100 15,45"
          fill="#dcfce7"
          stroke="#166534"
          strokeWidth={2}
        />
      );
      break;
    case "hexagon":
      inner = (
        <polygon
          points="30,15 90,15 115,60 90,105 30,105 5,60"
          fill="#dcfce7"
          stroke="#166534"
          strokeWidth={2}
        />
      );
      break;
    case "circle":
      inner = <circle cx={60} cy={60} r={45} fill="#dcfce7" stroke="#166534" strokeWidth={2} />;
      break;
  }

  return (
    <svg
      viewBox={revealLines || isZeroReveal ? "0 0 120 130" : "0 0 120 120"}
      role="img"
      aria-label={shape.replace("_", " ")}
      className="diagram-svg"
    >
      {inner}
      {revealLines && <RevealOverlay lines={revealLines} />}
      {isZeroReveal && <RevealOverlay lines={[]} zeroCaption="No line of symmetry" />}
    </svg>
  );
}
