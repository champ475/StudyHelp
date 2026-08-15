import { useCallback, useEffect, useState } from "react";
import { fetchProblem, submitStep } from "../api/client";
import { frontierStepTypes } from "../frontier";
import type { PublicProblem, StudentStep, VerifyResult } from "../types";
import { ChatPanel, type ChatMessage } from "./ChatPanel";
import { FreeTextStepper } from "./FreeTextStepper";
import { StepWidgetSwitcher } from "./StepWidgetSwitcher";

// Topics whose steps are typed free text (one box per step) rather than a
// math-aware structured widget — see FreeTextStepper's doc comment for why
// this deviates from ARCHITECTURE.md's original D12.
const FREE_TEXT_TOPICS = new Set(["fractions_addition"]);

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
  const isFreeTextTopic = problem !== null && FREE_TEXT_TOPICS.has(problem.ncert_ref.topic);

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

  // A step just got accepted: freeze what the student typed into a locked
  // box and clear the active one for the next step. Keyed on the accepted
  // count (not the verdict object) so a resubmission that fails doesn't
  // touch this at all — only an actual advance does.
  useEffect(() => {
    if (!isFreeTextTopic) return;
    if (acceptedStepIds.length > lockedTexts.length) {
      setLockedTexts((prev) => [...prev, activeText]);
      setActiveText("");
    }
  }, [acceptedStepIds, lockedTexts.length, activeText, isFreeTextTopic]);

  const handleFreeTextCommit = useCallback(() => {
    if (!activeText.trim()) return;
    void handleSubmit({ step_type: "fraction_step", fields: { text: activeText } });
  }, [activeText, handleSubmit]);

  if (loadError) {
    return <p className="error-banner">Could not load problem: {loadError}</p>;
  }
  if (!problem) {
    return <p>Loading problem…</p>;
  }

  const availableStepTypes = frontierStepTypes(problem, acceptedStepIds);

  // The type that naturally follows the most recently accepted step —
  // used to steer the widget switcher's default tab forward instead of
  // leaving it on an already-completed-but-still-nominally-reachable
  // type (see StepWidgetSwitcher's preferredStepType doc comment).
  const lastAcceptedId = acceptedStepIds[acceptedStepIds.length - 1];
  const lastAcceptedNode = problem.step_graph.find((node) => node.step_id === lastAcceptedId);
  const nextNodeId = lastAcceptedNode?.next[0];
  const preferredStepType = problem.step_graph.find((node) => node.step_id === nextNodeId)?.type;

  const heading = isFreeTextTopic
    ? `${problem.given.a_num as number}/${problem.given.a_den as number} + ${problem.given.b_num as number}/${problem.given.b_den as number}`
    : `${problem.given.minuend as number} − ${problem.given.subtrahend as number}`;

  return (
    <div className="problem-solver">
      <h2>{heading}</h2>
      <p className="progress-note">Steps completed: {acceptedStepIds.length}</p>

      {isFreeTextTopic ? (
        <FreeTextStepper
          lockedTexts={lockedTexts}
          activeText={activeText}
          onActiveTextChange={setActiveText}
          onCommit={handleFreeTextCommit}
          disabled={isSubmitting}
          solved={solved}
        />
      ) : solved ? (
        <p className="solved-banner">Solved! Great work.</p>
      ) : (
        <StepWidgetSwitcher
          availableStepTypes={availableStepTypes}
          preferredStepType={preferredStepType}
          onSubmit={(step) => void handleSubmit(step)}
          disabled={isSubmitting}
        />
      )}

      {isFreeTextTopic && solved && <p className="solved-banner">Solved! Great work.</p>}

      {lastVerdict && !lastVerdict.is_valid && (
        <p className="verdict-banner incorrect" role="alert">
          Not quite — let&apos;s look at it together.
        </p>
      )}

      <ChatPanel messages={messages} isThinking={isSubmitting} />
    </div>
  );
}
