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

# Short, topic-grounded focus phrase for the non-analogy procedural/
# conceptual branch below — open-ended-review finding #3: that branch used
# to be one static string regardless of topic, so two different topics'
# first-ever mistake produced byte-identical mock text (confirmed in the
# e2e sweep table), making mock-only manual testing hard to tell topics
# apart by feel. `_DEFAULT_FOCUS` covers any topic not listed here so a
# future topic never breaks this path.
_TOPIC_FOCUS = {
    "subtraction_with_borrowing": "how each column works",
    "fractions_addition": "how the parts fit together",
    "lcm_hcf": "how the numbers relate to each other",
    "decimals": "how the place values line up",
    "area_perimeter": "how the shape is measured",
    "multiplication_division": "how the groups are built",
    "measurement": "how the units connect",
    "patterns": "how the pattern repeats",
    "shapes_angles": "how the angle is shaped",
    "how_many_squares": "how the squares are hiding in the grid",
    "symmetry": "how the two sides match",
    "mapping": "how the directions add up",
    "boxes_sketches": "how the shape is built",
    "smart_charts": "how the chart is read",
}
_DEFAULT_FOCUS = "the idea behind this step"


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
        if request.repeat_count >= 2 and request.analogy_hint:
            return DecideResponse(
                error_type="conceptual",
                remediation_strategy=(
                    "The student has missed this exact step more than once with the abstract/"
                    "numeric explanation — switch register entirely and re-teach the idea through "
                    "the given concrete analogy instead."
                ),
                instructional_intent=(
                    "Help the student map the concrete analogy onto their own step and notice "
                    "what it implies, without stating the correct value."
                ),
            )
        if request.misconception is not None:
            return DecideResponse(
                error_type="procedural",
                remediation_strategy=(
                    "Re-teach the concrete procedure behind this step using the retrieved "
                    "misconception's explanation strategy and a small demonstration example with "
                    "different numbers, rather than a bare restatement of the rule."
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
        # Deterministic stand-in for what a real generate() call should also
        # produce (CLAUDE.md Bug2, llm/prompts.py's GENERATE_SYSTEM_PROMPT
        # rules 3/8/9): a careless slip gets a short nudge; a procedural or
        # conceptual error gets a real, concrete re-teaching explanation, not
        # a one-line "look again". `analogy_hint` is only ever non-None when
        # the orchestrator has already decided the register should switch —
        # either the same step missed `REGISTER_SWITCH_REPEAT_THRESHOLD`
        # times in a row, or the same misconception recurring across
        # different steps/problems hit `TOPIC_REGISTER_SWITCH_THRESHOLD`
        # (dialogue/orchestrator.py) — so its mere presence here is the
        # trigger, not a repeat_count re-check.
        if request.is_concept_check:
            # Reflective, not interrogative (CLAUDE.md open-ended-review
            # Issue C): no input box exists for a reply to this message, so
            # it must never read like a question the student has to answer
            # before continuing — a direct "why does that work?" left the
            # student staring at it with nothing to do.
            message = (
                "Nice work fixing that! Take a moment to think about why that works, then "
                "let's move on to the next step."
            )
        elif request.analogy_hint:
            message = (
                f"Let's try this a different way. {request.analogy_hint} Now think about your "
                "own step. What do you notice that might need to change?"
            )
        elif request.decision.error_type == "careless":
            messages_by_hint_level = {
                1: "Let's look at this step again. What do you notice?",
                2: "Take another look at this column. Do you see anything to fix?",
                3: "Let's slow down. Can you check this step one more time?",
            }
            message = messages_by_hint_level[hint_level]
        else:
            # Short, simple sentences on purpose (Class-5 readability
            # gate) — a longer, concrete re-teach still has to stay easy
            # to read, not just short. Varies by topic (`_TOPIC_FOCUS`) and
            # by `hint_level`, same mechanism the "careless" branch above
            # already uses, so this branch isn't one fixed string either.
            focus = _TOPIC_FOCUS.get(request.topic, _DEFAULT_FOCUS)
            messages_by_hint_level = {
                1: (
                    f"Let's slow down and look at {focus}, not just the numbers. Picture a much "
                    "simpler version of this same kind of step. Notice what actually has to "
                    "happen there. Now look back at your own step. What do you notice that might "
                    "need to change?"
                ),
                2: (
                    f"Let's take this one part at a time and think about {focus}. Try a smaller, "
                    "easier example of the same idea first. See what happens in that small "
                    "example. Now try your own step again with that in mind."
                ),
                3: (
                    f"Let's really slow down and focus on {focus}. Think of the simplest possible "
                    "example of this idea. Walk through it slowly in your head. Then look at your "
                    "own step once more. What is different?"
                ),
            }
            message = messages_by_hint_level[hint_level]
        return GenerateResponse(
            message=message,
            expects_retry=True,
            hint_level=hint_level,
            concept_flag=None,
        )
