"""The uniform verifier interface every topic implements.

Called directly by application code as a hard pipeline gate — never a tool
the LLM decides when or how to invoke (ARCHITECTURE.md D1). Adding a topic
means writing a new `StepVerifier` and registering it here; the pipeline
that calls `verify_step()` never changes.
"""

from typing import Protocol, runtime_checkable

from studyhelp.schemas.verify import ProblemState, StudentStep, VerifyResult


@runtime_checkable
class StepVerifier(Protocol):
    topic: str

    def verify_step(
        self, problem_state: ProblemState, student_step: StudentStep
    ) -> VerifyResult: ...


class VerifierRegistry:
    def __init__(self) -> None:
        self._verifiers: dict[str, StepVerifier] = {}

    def register(self, verifier: StepVerifier) -> None:
        self._verifiers[verifier.topic] = verifier

    def get(self, topic: str) -> StepVerifier:
        try:
            return self._verifiers[topic]
        except KeyError:
            raise KeyError(f"No verifier registered for topic '{topic}'") from None


registry = VerifierRegistry()
