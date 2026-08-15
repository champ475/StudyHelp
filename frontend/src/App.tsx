import { useEffect, useMemo, useState } from "react";
import { createSession, fetchProblems } from "./api/client";
import { IdentityPicker } from "./components/IdentityPicker";
import { ProblemSolver } from "./components/ProblemSolver";
import type { ProblemSummary } from "./types";

interface Chapter {
  chapter: number;
  chapterTitle: string;
  problems: ProblemSummary[];
}

function groupByChapter(problems: ProblemSummary[]): Chapter[] {
  const byChapter = new Map<number, Chapter>();
  for (const problem of problems) {
    const { chapter, chapter_title: chapterTitle } = problem.ncert_ref;
    const existing = byChapter.get(chapter);
    if (existing) {
      existing.problems.push(problem);
    } else {
      byChapter.set(chapter, { chapter, chapterTitle, problems: [problem] });
    }
  }
  return Array.from(byChapter.values()).sort((a, b) => a.chapter - b.chapter);
}

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);

  const [problems, setProblems] = useState<ProblemSummary[] | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [selectedChapter, setSelectedChapter] = useState<number | null>(null);
  const [problemId, setProblemId] = useState<string | null>(null);

  useEffect(() => {
    fetchProblems()
      .then((loaded) => {
        setProblems(loaded);
        const first = loaded[0];
        if (first) {
          setSelectedChapter(first.ncert_ref.chapter);
          setProblemId(first.problem_id);
        }
      })
      .catch((error: unknown) =>
        setCatalogError(error instanceof Error ? error.message : String(error)),
      );
  }, []);

  const chapters = useMemo(() => groupByChapter(problems ?? []), [problems]);
  const currentChapter = chapters.find((c) => c.chapter === selectedChapter);

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
      ) : catalogError ? (
        <p className="error-banner">Could not load the problem catalog: {catalogError}</p>
      ) : !problems || !problemId ? (
        <p>Loading problems…</p>
      ) : (
        <>
          <div className="catalog-picker">
            <label>
              Chapter:
              <select
                value={selectedChapter ?? ""}
                onChange={(event) => {
                  const chapter = Number(event.target.value);
                  setSelectedChapter(chapter);
                  const first = chapters.find((c) => c.chapter === chapter)?.problems[0];
                  if (first) setProblemId(first.problem_id);
                }}
              >
                {chapters.map((chapter) => (
                  <option key={chapter.chapter} value={chapter.chapter}>
                    {chapter.chapter}. {chapter.chapterTitle}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Problem:
              <select value={problemId} onChange={(event) => setProblemId(event.target.value)}>
                {currentChapter?.problems.map((problem) => (
                  <option key={problem.problem_id} value={problem.problem_id}>
                    {problem.display_label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <ProblemSolver key={problemId} sessionId={sessionId} problemId={problemId} />
        </>
      )}
    </main>
  );
}
