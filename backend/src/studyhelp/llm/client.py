"""Provider-agnostic LLM client: classify / decide / generate.

No other code in this project imports a provider SDK directly — everything
downstream of the pipeline talks to the `LLMClient` Protocol only. This is
what makes swapping providers (or adding a fallback provider) a config
change (`LLM_PROVIDER`) rather than a rewrite (ARCHITECTURE.md D17).

`classify()` is the only method Phase 2 actually calls. `decide()` and
`generate()` are defined now (matching CLAUDE.md's instruction to build the
full interface up front) but aren't consumed until Phase 3's dialogue
orchestrator — see technical_architecture.md §6 for the decide-then-generate
split these correspond to.
"""

import time
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from studyhelp.config import get_settings
from studyhelp.logging import get_logger

# ---------------------------------------------------------------------------
# classify() — closed-set error classification (ARCHITECTURE.md D3).
# ---------------------------------------------------------------------------


class ClassifyCandidate(BaseModel):
    """One retrieved misconception-bank entry the model may pick from.
    Retrieval happens *before* this call (technical_architecture.md §5) —
    the model never sees the whole bank, only candidates already scoped to
    this (topic, step_type)."""

    misconception_id: str
    typical_mindset: str


class ClassifyRequest(BaseModel):
    topic: str
    step_type: str
    correct_step: dict[str, Any]
    student_step: dict[str, Any]
    candidates: list[ClassifyCandidate]


class ClassifyResponse(BaseModel):
    misconception_id: str | None
    """`None` means "none of these" — the model must never invent an id
    outside `candidates`; the caller validates this regardless (closed-set
    enforced in application code, not trusted from the model alone)."""
    rationale: str


# ---------------------------------------------------------------------------
# decide() — the "decide" half of decide-then-generate (Phase 3, ARCHITECTURE.md D7).
# ---------------------------------------------------------------------------

ErrorType = Literal["careless", "procedural", "conceptual"]


class DecideRequest(BaseModel):
    topic: str
    step_type: str
    correct_step: dict[str, Any]
    student_step: dict[str, Any]
    misconception: ClassifyCandidate | None
    turn_number: int
    repeat_count: int = 1
    """How many consecutive times the student has now gotten *this exact
    step* wrong (`DialogueState.consecutive_errors_on_this_step` —
    orchestrator.py), distinct from `turn_number` (how many dialogue turns
    have actually been shown, which can lag `repeat_count` under a delayed
    intervention policy). Drives the register switch to a concrete analogy
    at `repeat_count >= 2` (CLAUDE.md Bug2)."""
    analogy_hint: str | None = None
    """The fixed, topic-appropriate analogy (`llm/analogies.py`) to use once
    `repeat_count >= 2` — deterministically retrieved by application code,
    never left to the model to invent (see that module's docstring).
    `None` when `repeat_count < 2` or the topic has no library entry."""


class DecideResponse(BaseModel):
    error_type: ErrorType
    remediation_strategy: str
    instructional_intent: str


# ---------------------------------------------------------------------------
# generate() — the "generate" half; conditioned on a DecideResponse, never
# called directly from an error (Phase 3, ARCHITECTURE.md D7).
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    decision: DecideResponse
    conversation_so_far: list[dict[str, str]]
    correct_step: dict[str, Any]
    student_step: dict[str, Any]
    protected_values: list[int | str] = Field(default_factory=list)
    """The exact values `dialogue/leakage_filter.py::contains_leakage()`
    will reject the draft for containing (`dialogue/orchestrator.py`'s
    `_protected_values(correct_step)` — the same list the gate itself
    checks against, not re-derived by the model from `correct_step`, which
    mixes protected output fields with non-secret visible-input fields the
    model can't reliably tell apart on its own). Confirmed live (CLAUDE.md
    open-ended-review Issue A) that without this, a model told to "use a
    demo example with different numbers" (rule 1) will still sometimes
    pick small illustrative numbers that coincidentally equal one of this
    problem's own protected values (e.g. a "1/2 + 1/3" demo colliding with
    a correct numerator of 3) and get rejected for an unrelated reason —
    telling it exactly what to avoid, including inside its own demo, fixes
    that at the source instead of relying on trial-and-error retries."""
    repeat_count: int = 1
    """Same value passed to `decide()` for this turn — see `DecideRequest`.
    Threaded independently to `generate()` (not just embedded in
    `decision`) so the register-switch instruction is enforced directly at
    generation time regardless of what `decision.remediation_strategy`'s
    free text happens to say."""
    analogy_hint: str | None = None
    """Same value passed to `decide()` for this turn — see `DecideRequest`."""
    is_concept_check: bool = False
    """True only for the one-off post-resolution "why does that work?"
    message (`dialogue/orchestrator.py::_generate_concept_check_message`,
    open-ended review finding #3) — the student just answered correctly, so
    this is NOT a remediation turn. An explicit flag rather than inferring
    it from `decision.error_type`/`repeat_count` alone, since a real
    explaining-turn decision can legitimately be `error_type="conceptual"`
    with `repeat_count=1` too — that combination is not unique to this
    case, and both the mock provider and the real prompt need an
    unambiguous signal to avoid mistaking a consolidation question for a
    fresh re-teach."""
    regeneration_feedback: str | None = None
    """Set only on a gate-rejected retry (dialogue/orchestrator.py):
    concretely what was wrong with the previous draft (leaked the answer /
    too complex), so the model has something to actually change. Without
    this, a deterministic provider (temperature=0) regenerates the exact
    same rejected text on every attempt, burning the whole retry budget on
    one guaranteed-identical draft before falling back to the generic
    canned message."""


class GenerateResponse(BaseModel):
    message: str
    expects_retry: bool
    hint_level: int
    concept_flag: str | None


# ---------------------------------------------------------------------------
# Client protocol + logging wrapper + factory.
# ---------------------------------------------------------------------------


class LLMClient(Protocol):
    async def classify(self, request: ClassifyRequest) -> ClassifyResponse: ...
    async def decide(self, request: DecideRequest) -> DecideResponse: ...
    async def generate(self, request: GenerateRequest) -> GenerateResponse: ...


class LoggingLLMClient:
    """Wraps any `LLMClient` implementation and logs every call — prompt,
    response, latency, cost — regardless of provider (CLAUDE.md: "Log every
    real call... this is both an ops necessity and a research artifact").
    Centralized here so no individual provider has to remember to do it."""

    def __init__(self, inner: LLMClient, *, provider_name: str, cost_per_call: float = 0.0) -> None:
        self._inner = inner
        self._provider_name = provider_name
        self._cost_per_call = cost_per_call
        self._logger = get_logger(__name__)

    async def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        start = time.monotonic()
        response = await self._inner.classify(request)
        self._log("classify", start, request, response)
        return response

    async def decide(self, request: DecideRequest) -> DecideResponse:
        start = time.monotonic()
        response = await self._inner.decide(request)
        self._log("decide", start, request, response)
        return response

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        start = time.monotonic()
        response = await self._inner.generate(request)
        self._log("generate", start, request, response)
        return response

    def _log(self, method: str, start: float, request: BaseModel, response: BaseModel) -> None:
        self._logger.info(
            "llm_call",
            provider=self._provider_name,
            method=method,
            request=request.model_dump(mode="json"),
            response=response.model_dump(mode="json"),
            latency_seconds=round(time.monotonic() - start, 4),
            cost=self._cost_per_call,
        )


def build_llm_client() -> LLMClient:
    settings = get_settings()
    if settings.llm_provider == "mock":
        from studyhelp.llm.providers.mock import MockLLMProvider

        return LoggingLLMClient(MockLLMProvider(), provider_name="mock", cost_per_call=0.0)

    from studyhelp.llm.providers.groq import GroqLLMProvider

    if not settings.groq_api_key or not settings.groq_model:
        raise RuntimeError(
            "LLM_PROVIDER=groq requires both GROQ_API_KEY and GROQ_MODEL to be set. "
            "GROQ_MODEL must be a model whose structured-output/tool-calling reliability "
            "has actually been verified (CLAUDE.md) — never assumed."
        )
    return LoggingLLMClient(
        GroqLLMProvider(api_key=settings.groq_api_key, model=settings.groq_model),
        provider_name=f"groq:{settings.groq_model}",
        cost_per_call=0.0,  # unset until real per-token pricing is wired in alongside the real key
    )
