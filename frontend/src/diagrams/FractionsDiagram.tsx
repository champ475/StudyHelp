import type { DiagramProps } from "./types";

function FractionCircle({ num, den, cx }: { num: number; den: number; cx: number }): JSX.Element {
  const r = 32;
  const cy = 40;
  const slices = [];
  for (let i = 0; i < den; i++) {
    const startAngle = (i / den) * 2 * Math.PI - Math.PI / 2;
    const endAngle = ((i + 1) / den) * 2 * Math.PI - Math.PI / 2;
    const x1 = cx + r * Math.cos(startAngle);
    const y1 = cy + r * Math.sin(startAngle);
    const x2 = cx + r * Math.cos(endAngle);
    const y2 = cy + r * Math.sin(endAngle);
    const largeArc = endAngle - startAngle > Math.PI ? 1 : 0;
    const filled = i < num;
    slices.push(
      <path
        key={i}
        d={`M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`}
        fill={filled ? "#4f46e5" : "#f5f5f4"}
        stroke="#78716c"
        strokeWidth={1}
      />,
    );
  }
  return (
    <g>
      {slices}
      <text x={cx} y={cy + r + 18} textAnchor="middle" className="diagram-label">
        {num}/{den}
      </text>
    </g>
  );
}

// `given.a_num`/`a_den`/`b_num`/`b_den` are the problem's own two stated
// fractions — visible input. The operator between them isn't in `given`
// (it lives in the DAG's first step, not the public schema), so this
// deliberately doesn't guess one; the problem title above already states
// it in words/symbols.
export function FractionsDiagram({ given }: DiagramProps): JSX.Element | null {
  const aNum = given.a_num;
  const aDen = given.a_den;
  const bNum = given.b_num;
  const bDen = given.b_den;
  if (
    typeof aNum !== "number" ||
    typeof aDen !== "number" ||
    typeof bNum !== "number" ||
    typeof bDen !== "number" ||
    aDen <= 0 ||
    bDen <= 0 ||
    aDen > 12 ||
    bDen > 12
  ) {
    return null;
  }
  return (
    <svg
      viewBox="0 0 200 100"
      role="img"
      aria-label={`Fractions ${aNum}/${aDen} and ${bNum}/${bDen}`}
      className="diagram-svg"
    >
      <FractionCircle num={aNum} den={aDen} cx={50} />
      <FractionCircle num={bNum} den={bDen} cx={150} />
    </svg>
  );
}
