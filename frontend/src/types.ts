// Mirrors backend/src/studyhelp/schemas/step_schema.py and verify.py.
// Kept as plain types (not generated) since the backend is the single
// source of truth for the schema shape and this project has one frontend
// consumer; revisit generating these from the OpenAPI schema if that
// stops being true.

// Mirrors the backend's PublicProblem/PublicStepNode (GET /problems/{id})
// — deliberately missing `expected_state` and `final_answer`. That's not
// an oversight: exposing them from a browser-reachable endpoint would let
// a student read every correct answer straight out of devtools, directly
// undermining the leakage filter (backend/.../api/routes/problems.py).
//
// `hint` is that step type's `step_types.description` (seed-authored,
// topic-agnostic) — what lets the universal `FreeTextStepper` show a
// meaningful placeholder for *any* topic's step type without this frontend
// knowing anything topic-specific (ARCHITECTURE.md D43).
export interface PublicStepNode {
  step_id: string;
  type: string;
  next: string[];
  hint: string;
}

export interface NcertRef {
  class: number;
  chapter: number;
  chapter_title: string;
  topic: string;
}

export interface PublicProblem {
  problem_id: string;
  ncert_ref: NcertRef;
  display_label: string;
  given: Record<string, unknown>;
  step_graph: PublicStepNode[];
  alt_paths: { path_id: string; entry: string; note?: string | null }[];
}

// One row of the GET /problems catalog — thin on purpose (no step graph,
// no `given`) so the chapter/problem picker can list all ~140 problems
// without pulling every DAG.
export interface ProblemSummary {
  problem_id: string;
  ncert_ref: NcertRef;
  display_label: string;
}

// Free-text input is universal across every topic (ARCHITECTURE.md D41,
// superseding D12/D32's structured-widget default) — the student never
// declares a step type; the backend verifier infers it from the DAG
// frontier by trying each reachable step type's grammar against the typed
// text (see any `verification/topics/<topic>/verifier.py`). `step_type`
// here is therefore always the fixed placeholder below; only `fields.text`
// carries real information.
export interface StudentStep {
  step_type: "free_text_step";
  fields: { text: string };
}

// --- verifier / pipeline response shapes -----------------------------------

export interface FieldDiscrepancy {
  field: string;
  expected: unknown;
  actual: unknown;
}

export interface ErrorSignal {
  kind: "field_mismatch" | "wrong_step_type" | "malformed" | "none";
  discrepant_fields: FieldDiscrepancy[];
  nearest_matched_step_id: string | null;
  note: string | null;
}

export interface VerifyResult {
  is_valid: boolean;
  matched_step_id: string | null;
  confidence: number;
  error_signal: ErrorSignal | null;
}

export type DialogueEvent = "no_action" | "resolved" | "explaining" | "escalated";

export interface TurnComplete {
  dialogue_event: DialogueEvent;
  turn_count: number;
  expects_retry: boolean;
  message: string | null;
  // Deterministically set by the backend (`dialogue/diagram_hint.py`), never
  // by the LLM — true only on an "explaining" turn whose classified
  // misconception is one of the curated, visually-clarifying ones. When
  // true, the frontend re-shows the SAME `given`-derived diagram the
  // problem header already shows (never new, answer-revealing content).
  diagram_hint: boolean;
  // `symmetry`-only, user-directed exception (see backend's
  // `dialogue/diagram_hint.py::should_reveal_symmetry_lines()`): the
  // correct `answer` field, present only once the student has missed this
  // exact step 2+ times in a row. When set, `SymmetryDiagram` draws the
  // actual line(s) of symmetry instead of the bare shape — every other
  // topic's `diagram_hint` never carries answer data, this is scoped
  // narrowly to symmetry alone.
  diagram_hint_reveal_answer: string | null;
}

export interface CreateSessionResponse {
  session_id: string;
  user_id: string;
}

// --- SSE event payloads (POST /sessions/{id}/steps) ------------------------
// Mirrors backend/src/studyhelp/api/routes/sessions.py's four event types.
// "verdict"/"classification" are structured diagnostic data, never gated —
// they are not generated prose. "message_chunk" is the ONLY event carrying
// LLM-generated child-facing text, and only ever arrives after the backend
// has already cleared the leakage filter and readability gate.

export interface VerdictEvent {
  event: "verdict";
  data: VerifyResult;
}

export interface ClassificationEvent {
  event: "classification";
  data: {
    source: "rule" | "llm" | "novel";
    misconception_id: string | null;
    bug_code: string | null;
    confidence: "high" | "low";
    rationale: string | null;
  };
}

export interface MessageChunkEvent {
  event: "message_chunk";
  data: { text: string };
}

export interface TurnCompleteEvent {
  event: "turn_complete";
  data: TurnComplete;
}

export interface ErrorEvent {
  event: "error";
  data: { detail: string };
}

export type SseEventPayload =
  | VerdictEvent
  | ClassificationEvent
  | MessageChunkEvent
  | TurnCompleteEvent
  | ErrorEvent;
