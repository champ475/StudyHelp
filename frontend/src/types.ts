// Mirrors backend/src/studyhelp/schemas/step_schema.py and verify.py.
// Kept as plain types (not generated) since the backend is the single
// source of truth for the schema shape and this project has one frontend
// consumer; revisit generating these from the OpenAPI schema if that
// stops being true.

export type Column = "units" | "tens" | "hundreds" | "thousands" | "ten_thousands" | "lakhs";

// Mirrors the backend's PublicProblem/PublicStepNode (GET /problems/{id})
// — deliberately missing `expected_state` and `final_answer`. That's not
// an oversight: exposing them from a browser-reachable endpoint would let
// a student read every correct answer straight out of devtools, directly
// undermining the leakage filter (backend/.../api/routes/problems.py).
export interface PublicStepNode {
  step_id: string;
  type: string;
  next: string[];
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
  given: Record<string, unknown>;
  step_graph: PublicStepNode[];
  alt_paths: { path_id: string; entry: string; note?: string | null }[];
}

// --- structured per-step-type fields (never a raw string) -----------------

export interface CompareColumnFields {
  column: Column;
  minuend_digit: number;
  subtrahend_digit: number;
  borrow_needed: boolean;
}

export interface BorrowFields {
  from_column: Column;
  from_digit_before: number;
  from_digit_after: number;
  to_column: Column;
  to_digit_before: number;
  to_digit_after: number;
  combined_result_digit?: number | null;
}

export interface SubtractColumnFields {
  column: Column;
  minuend_digit: number;
  subtrahend_digit: number;
  result_digit: number;
}

export interface WriteFinalAnswerFields {
  digits: Partial<Record<Column, number>>;
  value: number;
}

export type StepType = "compare_column" | "borrow" | "subtract_column" | "write_final_answer";

export interface StudentStep {
  step_type: StepType;
  fields: Record<string, unknown>;
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
