import { parseSseStream } from "./sse";
import type {
  CreateSessionResponse,
  ProblemSummary,
  PublicProblem,
  SseEventPayload,
  StudentStep,
} from "../types";

const API_BASE = "/api";

export async function createSession(displayName: string): Promise<CreateSessionResponse> {
  const response = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ display_name: displayName }),
  });
  if (!response.ok) {
    throw new Error(`Failed to create session: ${response.status}`);
  }
  return (await response.json()) as CreateSessionResponse;
}

export async function fetchProblems(): Promise<ProblemSummary[]> {
  const response = await fetch(`${API_BASE}/problems`);
  if (!response.ok) {
    throw new Error(`Failed to load problem catalog: ${response.status}`);
  }
  return (await response.json()) as ProblemSummary[];
}

export async function fetchProblem(problemId: string): Promise<PublicProblem> {
  const response = await fetch(`${API_BASE}/problems/${problemId}`);
  if (!response.ok) {
    throw new Error(`Failed to load problem '${problemId}': ${response.status}`);
  }
  return (await response.json()) as PublicProblem;
}

export interface SubmitStepRequest {
  problem_id: string;
  accepted_step_ids: string[];
  student_step: StudentStep;
  timing_policy?: "immediate" | "after_nth_repeat" | "wait_for_completion";
}

export async function* submitStep(
  sessionId: string,
  request: SubmitStepRequest,
): AsyncGenerator<SseEventPayload> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/steps`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Step submission failed: ${response.status}`);
  }
  for await (const event of parseSseStream(response)) {
    yield event as SseEventPayload;
  }
}
