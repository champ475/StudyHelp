import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchProblem, submitStep } from "../api/client";
import { computeFrontier } from "../frontier";
import type { PublicProblem, StudentStep, VerifyResult } from "../types";
import type { ChatMessage } from "./ChatPanel";
import { DiagramPanel } from "./DiagramPanel";
import { FreeTextStepper } from "./FreeTextStepper";

interface ProblemSolverProps {
  sessionId: string;
  problemId: string;
}

let messageIdCounter = 0;
function nextMessageId(): string {
  messageIdCounter += 1;
  return `msg-${messageIdCounter}`;
}

export function ProblemSolver({ sessionId, problemId }: ProblemSolverProps) {
  const [problem, setProblem] = useState<PublicProblem | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [acceptedStepIds, setAcceptedStepIds] = useState<string[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastVerdict, setLastVerdict] = useState<VerifyResult | null>(null);
  const [solved, setSolved] = useState(false);
  const [lockedTexts, setLockedTexts] = useState<string[]>([]);
  const [activeText, setActiveText] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchProblem(problemId)
      .then((loaded) => {
        if (!cancelled) setProblem(loaded);
      })
      .catch((error: unknown) => {
        if (!cancelled) setLoadError(error instanceof Error ? error.message : String(error));
      });
    return () => {
      cancelled = true;
    };
  }, [problemId]);

  const handleSubmit = useCallback(
    async (step: StudentStep) => {
      setIsSubmitting(true);
      setLastVerdict(null);
      let streamingMessageId: string | null = null;
      let accumulatedText = "";
      // A submission that turns out wrong never advances `acceptedStepIds`,
      // so this is stable for every message this attempt produces — it's
      // what lets a tutor message render directly under the step attempt
      // it responds to (CLAUDE.md Bug4) instead of in one block at the end.
      const stepIndexForThisAttempt = acceptedStepIds.length;

      try {
        for await (const event of submitStep(sessionId, {
          problem_id: problemId,
          accepted_step_ids: acceptedStepIds,
          student_step: step,
        })) {
          if (event.event === "verdict") {
            setLastVerdict(event.data);
            if (event.data.is_valid && event.data.matched_step_id) {
              const matchedId = event.data.matched_step_id;
              setAcceptedStepIds((prev) => (prev.includes(matchedId) ? prev : [...prev, matchedId]));
            }
          } else if (event.event === "message_chunk") {
            accumulatedText = accumulatedText ? `${accumulatedText} ${event.data.text}` : event.data.text;
            if (streamingMessageId === null) {
              streamingMessageId = nextMessageId();
              const id = streamingMessageId;
              setMessages((prev) => [
                ...prev,
                { id, text: accumulatedText, stepIndex: stepIndexForThisAttempt },
              ]);
            } else {
              const id = streamingMessageId;
              const text = accumulatedText;
              setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, text } : m)));
            }
          } else if (event.event === "turn_complete") {
            if (event.data.dialogue_event === "resolved" || event.data.dialogue_event === "escalated") {
              const nearest = lastVerdict?.error_signal?.nearest_matched_step_id;
              if (event.data.dialogue_event === "escalated" && nearest) {
                setAcceptedStepIds((prev) => (prev.includes(nearest) ? prev : [...prev, nearest]));
              }
            }
            // A "resolved" message is the one-off post-correct reflection
            // (backend's `_generate_concept_check_message`) — mark it so
            // ChatPanel renders it visibly differently from a normal
            // explanation bubble, never as a question awaiting a reply
            // there's no input path for (open-ended-review Issue C).
            if (event.data.dialogue_event === "resolved" && streamingMessageId !== null) {
              const id = streamingMessageId;
              setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, isReflection: true } : m)));
            }
            // Deterministic per the backend (`dialogue/diagram_hint.py`) —
            // re-shows the problem's own diagram under this specific
            // explanation when the classified misconception is one this
            // topic's diagram visually clarifies.
            if (event.data.diagram_hint && streamingMessageId !== null) {
              const id = streamingMessageId;
              const revealAnswer = event.data.diagram_hint_reveal_answer;
              setMessages((prev) =>
                prev.map((m) => (m.id === id ? { ...m, showDiagram: true, revealAnswer } : m))
              );
            }
          } else if (event.event === "error") {
            setLoadError(event.data.detail);
          }
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [sessionId, problemId, acceptedStepIds, lastVerdict],
  );

  useEffect(() => {
    if (!problem) return;
    // Terminal means "no further DAG steps" (`next.length === 0`) — not a
    // hardcoded type name. `write_final_answer` is only what the 7 heavy
    // DAG topics call their terminal step; light-check topics use their
    // own topic-specific type name (e.g. `patterns_next_term`), so keying
    // off that string left every light-check problem's step box open
    // forever after the student actually finished (found via this
    // project's e2e sweep). Mirrors the backend's own `problem_is_complete`
    // check (api/routes/sessions.py), which already uses `not
    // target_node.next`, never a type-name check.
    const terminalReached = acceptedStepIds.some((id) => {
      const node = problem.step_graph.find((n) => n.step_id === id);
      return node && node.next.length === 0;
    });
    setSolved(terminalReached);
  }, [problem, acceptedStepIds]);

  // A step just got accepted: freeze what the student typed into a locked
  // box and clear the active one for the next step. Keyed on the accepted
  // count (not the verdict object) so a resubmission that fails doesn't
  // touch this at all — only an actual advance does.
  useEffect(() => {
    if (acceptedStepIds.length > lockedTexts.length) {
      setLockedTexts((prev) => [...prev, activeText]);
      setActiveText("");
    }
  }, [acceptedStepIds, lockedTexts.length, activeText]);

  const handleFreeTextCommit = useCallback(() => {
    if (!activeText.trim()) return;
    void handleSubmit({ step_type: "free_text_step", fields: { text: activeText } });
  }, [activeText, handleSubmit]);

  // Every hook must run on every render regardless of the early returns
  // below (Rules of Hooks) — this one stays above them even though its
  // result is only used once `problem` has loaded.
  const messagesByStepIndex = useMemo(() => {
    const grouped: ChatMessage[][] = [];
    for (const message of messages) {
      (grouped[message.stepIndex] ??= []).push(message);
    }
    return grouped;
  }, [messages]);

  if (loadError) {
    return <p className="error-banner">Could not load problem: {loadError}</p>;
  }
  if (!problem) {
    return <p>Loading problem…</p>;
  }

  // The current step's hint (placeholder + helper text) comes from
  // whichever type is first in the DAG frontier. Multiple types can be
  // simultaneously reachable (alt paths, D11) — the frontend doesn't need
  // to disambiguate which one the student means, since the backend tries
  // every reachable type's grammar against the typed text (D41); this is
  // just UI copy, not a correctness decision.
  const frontierHint = computeFrontier(problem, acceptedStepIds)[0]?.hint;

  return (
    <div className="problem-solver">
      <h2>{problem.display_label}</h2>
      <DiagramPanel problem={problem} />
      <p className="progress-note">Steps completed: {acceptedStepIds.length}</p>

      {lastVerdict && !lastVerdict.is_valid && (
        <p className="verdict-banner incorrect" role="alert">
          Not quite — let&apos;s look at it together.
        </p>
      )}

      <FreeTextStepper
        lockedTexts={lockedTexts}
        activeText={activeText}
        onActiveTextChange={setActiveText}
        onCommit={handleFreeTextCommit}
        disabled={isSubmitting}
        solved={solved}
        hint={frontierHint}
        messagesByStepIndex={messagesByStepIndex}
        isThinking={isSubmitting}
        problem={problem}
      />

      {solved && <p className="solved-banner">Solved! Great work.</p>}
    </div>
  );
}
