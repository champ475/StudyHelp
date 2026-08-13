import { useCallback, useEffect, useState } from "react";
import { fetchProblem, submitStep } from "../api/client";
import { frontierStepTypes } from "../frontier";
import type { PublicProblem, StudentStep, VerifyResult } from "../types";
import { ChatPanel, type ChatMessage } from "./ChatPanel";
import { StepWidgetSwitcher } from "./StepWidgetSwitcher";

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
              setMessages((prev) => [...prev, { id, text: accumulatedText }]);
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
    const terminalReached = acceptedStepIds.some((id) => {
      const node = problem.step_graph.find((n) => n.step_id === id);
      return node && node.type === "write_final_answer" && node.next.length === 0;
    });
    setSolved(terminalReached);
  }, [problem, acceptedStepIds]);

  if (loadError) {
    return <p className="error-banner">Could not load problem: {loadError}</p>;
  }
  if (!problem) {
    return <p>Loading problem…</p>;
  }

  const availableStepTypes = frontierStepTypes(problem, acceptedStepIds);

  return (
    <div className="problem-solver">
      <h2>
        {problem.given.minuend as number} − {problem.given.subtrahend as number}
      </h2>
      <p className="progress-note">Steps completed: {acceptedStepIds.length}</p>

      {solved ? (
        <p className="solved-banner">Solved! Great work.</p>
      ) : (
        <StepWidgetSwitcher
          availableStepTypes={availableStepTypes}
          onSubmit={(step) => void handleSubmit(step)}
          disabled={isSubmitting}
        />
      )}

      {lastVerdict && !lastVerdict.is_valid && (
        <p className="verdict-banner incorrect" role="alert">
          Not quite — let&apos;s look at it together.
        </p>
      )}

      <ChatPanel messages={messages} isThinking={isSubmitting} />
    </div>
  );
}
