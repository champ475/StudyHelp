// One diagram renderer per topic (mirrors the backend's one-verifier-per-
// topic module pattern), dispatched by topic key in `index.ts` — never a
// giant if/else in a single component.
//
// Every renderer takes ONLY `Problem.given` (already public, leakage-safe —
// see `api/routes/problems.py::_public_given()`), never `expected_state`/
// `final_answer` (never sent to the browser at all, D8/D75). A renderer
// must be a pure function of `given`: same `given`, same picture, for any
// problem in that topic — never hardcoded to one specific problem's
// numbers.
export interface DiagramProps {
  given: Record<string, unknown>;
  // `symmetry`-only, user-directed exception to the "never `expected_state`"
  // rule above (backend's `dialogue/diagram_hint.py::should_reveal_symmetry_lines()`):
  // the correct `answer` field, passed down ONLY once the backend has
  // decided to reveal it (2+ misses on the same step). Every renderer other
  // than `SymmetryDiagram` ignores this prop and stays a pure function of
  // `given` alone, exactly as documented above.
  revealAnswer?: string | null;
}

export type DiagramRenderer = (props: DiagramProps) => JSX.Element | null;
