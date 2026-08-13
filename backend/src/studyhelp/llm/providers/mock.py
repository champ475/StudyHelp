"""Realistic fake responses — the default provider until a Groq key is
provided (ARCHITECTURE.md D17, CLAUDE.md). Deterministic on purpose: tests
should not have to tolerate randomness to be reliable. Every method accepts
an optional override so a test can inject an adversarial response (e.g. a
misconception_id outside the candidate set) to exercise the caller's
closed-set validation.
"""

from studyhelp.llm.client import (
    ClassifyRequest,
    ClassifyResponse,
    DecideRequest,
    DecideResponse,
    GenerateRequest,
    GenerateResponse,
)


class MockLLMProvider:
    def __init__(
        self,
        *,
        classify_override: ClassifyResponse | None = None,
        decide_override: DecideResponse | None = None,
        generate_override: GenerateResponse | None = None,
    ) -> None:
        self._classify_override = classify_override
        self._decide_override = decide_override
        self._generate_override = generate_override

    async def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        if self._classify_override is not None:
            return self._classify_override
        if not request.candidates:
            return ClassifyResponse(
                misconception_id=None,
                rationale="No candidate misconceptions were retrieved for this (topic, step_type) — "
                "nothing to pick from, per the closed-set constraint.",
            )
        chosen = request.candidates[0]
        return ClassifyResponse(
            misconception_id=chosen.misconception_id,
            rationale=(
                f"[mock] The student's step does not follow from the correct approach; the "
                f"closest retrieved candidate mindset is: {chosen.typical_mindset[:120]}"
            ),
        )

    async def decide(self, request: DecideRequest) -> DecideResponse:
        if self._decide_override is not None:
            return self._decide_override
        if request.misconception is not None:
            return DecideResponse(
                error_type="procedural",
                remediation_strategy=(
                    "Re-anchor to the concrete procedure step-by-step using the retrieved "
                    "misconception's explanation strategy, rather than restating the rule."
                ),
                instructional_intent=(
                    "Guide the student to notice the specific mismatch themselves through a "
                    "question, without stating the correct step."
                ),
            )
        return DecideResponse(
            error_type="careless",
            remediation_strategy="Ask the student to recheck their own work on this step before offering any hint.",
            instructional_intent="Give the student a chance to self-correct before any explanation is offered.",
        )

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        if self._generate_override is not None:
            return self._generate_override
        hint_level = min(len(request.conversation_so_far) // 2 + 1, 3)
        return GenerateResponse(
            message=(
                "[mock tutor] Let's look at this step together. "
                f"({request.decision.instructional_intent})"
            ),
            expects_retry=True,
            hint_level=hint_level,
            concept_flag=None,
        )
