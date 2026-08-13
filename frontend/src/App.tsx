import { useState } from "react";
import { createSession } from "./api/client";
import { IdentityPicker } from "./components/IdentityPicker";
import { ProblemSolver } from "./components/ProblemSolver";

// Hardcoded for the dev/demo picker — there's no "list problems" endpoint
// yet (Phase 4 scope; a real catalog browsing UI is a fair later addition).
// Matches backend/src/studyhelp/seed/fixtures/problems/ch1_subtraction_borrowing/.
const DEFAULT_PROBLEM_ID = "subtraction-borrow-001";

const DEMO_PROBLEMS = [
  { id: DEFAULT_PROBLEM_ID, label: "52 − 25 (single borrow)" },
  { id: "subtraction-borrow-002", label: "503 − 178 (borrow across a zero)" },
  { id: "subtraction-borrow-003", label: "89 − 45 (no borrow needed)" },
  { id: "subtraction-borrow-004", label: "1000 − 1 (borrow across multiple zeros)" },
  { id: "subtraction-borrow-005", label: "542 − 89 (fewer digits in the subtrahend)" },
  { id: "subtraction-borrow-014", label: "542 − 187 (double cascading borrow)" },
];

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [problemId, setProblemId] = useState<string>(DEFAULT_PROBLEM_ID);

  const handleCreateSession = (displayName: string) => {
    setIsCreatingSession(true);
    setSessionError(null);
    createSession(displayName)
      .then((response) => setSessionId(response.session_id))
      .catch((error: unknown) => setSessionError(error instanceof Error ? error.message : String(error)))
      .finally(() => setIsCreatingSession(false));
  };

  return (
    <main className="app">
      <h1>StudyHelp</h1>
      {!sessionId ? (
        <>
          <IdentityPicker onCreate={handleCreateSession} isCreating={isCreatingSession} />
          {sessionError && <p className="error-banner">{sessionError}</p>}
        </>
      ) : (
        <>
          <label className="problem-picker">
            Problem:
            <select value={problemId} onChange={(event) => setProblemId(event.target.value)}>
              {DEMO_PROBLEMS.map((problem) => (
                <option key={problem.id} value={problem.id}>
                  {problem.label}
                </option>
              ))}
            </select>
          </label>
          <ProblemSolver key={problemId} sessionId={sessionId} problemId={problemId} />
        </>
      )}
    </main>
  );
}
