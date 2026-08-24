"""Real Groq provider.

Structured-output/tool-calling reliability for the configured `GROQ_MODEL`
must be verified with `backend/scripts/verify_groq_structured_output.py`
before this provider is trusted anywhere beyond local, supervised testing
(CLAUDE.md, ARCHITECTURE.md D17/D25) — see that script's output for the
verification result recorded for the current default model. `decide()` and
`generate()` share the tutor persona system prompts in `llm/prompts.py`
(ARCHITECTURE.md D7) so both calls sound like the same tutor.
`build_llm_client()` (llm/client.py) refuses to construct this provider at
all unless both `GROQ_API_KEY` and `GROQ_MODEL` are explicitly set, so
nothing silently ships with an unverified default model.
"""

import json

from groq import AsyncGroq

from studyhelp.llm.client import (
    ClassifyRequest,
    ClassifyResponse,
    DecideRequest,
    DecideResponse,
    GenerateRequest,
    GenerateResponse,
)
from studyhelp.llm.prompts import DECIDE_SYSTEM_PROMPT, GENERATE_SYSTEM_PROMPT

_CLASSIFY_SYSTEM_PROMPT = """You are a diagnostic assistant for a Class 5 (age ~10) math tutor. \
You are NOT solving this problem — the correct answer is given to you. Your only job is to \
explain the specific reasoning path that would produce the STUDENT's incorrect answer, given \
their apparent approach. Do not re-derive the correct answer and simply note a discrepancy — \
reason about why *this* answer follows from a plausible (if flawed) student process.

You must pick the closest matching misconception from the CANDIDATES list provided, or say none \
of them fit. Never invent a misconception outside the candidates given.

Respond with a JSON object: {"misconception_id": <one of the candidate ids, or null if none fit>, \
"rationale": <short explanation of the student's apparent reasoning path>}."""


class GroqLLMProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncGroq(api_key=api_key)
        self._model = model

    async def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        user_content = json.dumps(
            {
                "topic": request.topic,
                "step_type": request.step_type,
                "correct_step": request.correct_step,
                "student_step": request.student_step,
                "candidates": [c.model_dump() for c in request.candidates],
            }
        )
        raw = await self._chat_json(_CLASSIFY_SYSTEM_PROMPT, user_content)
        return ClassifyResponse.model_validate(raw)

    async def decide(self, request: DecideRequest) -> DecideResponse:
        user_content = json.dumps(
            {
                "topic": request.topic,
                "step_type": request.step_type,
                "correct_step": request.correct_step,
                "student_step": request.student_step,
                "misconception": request.misconception.model_dump()
                if request.misconception
                else None,
                "turn_number": request.turn_number,
                "repeat_count": request.repeat_count,
                "analogy_hint": request.analogy_hint,
                "given": request.given,
            }
        )
        raw = await self._chat_json(DECIDE_SYSTEM_PROMPT, user_content)
        return DecideResponse.model_validate(raw)

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        payload: dict[str, object] = {
            "decision": request.decision.model_dump(),
            "conversation_so_far": request.conversation_so_far,
            "correct_step": request.correct_step,
            "student_step": request.student_step,
            "topic": request.topic,
            "step_type": request.step_type,
            "given": request.given,
            "protected_values": request.protected_values,
            "repeat_count": request.repeat_count,
            "analogy_hint": request.analogy_hint,
            "is_concept_check": request.is_concept_check,
        }
        if request.regeneration_feedback is not None:
            payload["regeneration_feedback"] = request.regeneration_feedback
        user_content = json.dumps(payload)
        # A gate-rejected retry needs actual variation, not a repeat of the
        # same rejected text — at temperature=0 (used everywhere else for
        # determinism) an unchanged prompt reliably reproduces the exact
        # same output, so a retry only helps once regeneration_feedback has
        # changed the prompt too; bumping temperature here is a second,
        # independent nudge toward a genuinely different draft.
        temperature = 0.0 if request.regeneration_feedback is None else 0.6
        raw = await self._chat_json(GENERATE_SYSTEM_PROMPT, user_content, temperature=temperature)
        return GenerateResponse.model_validate(raw)

    async def _chat_json(
        self, system_prompt: str, user_content: str, *, temperature: float = 0
    ) -> dict[str, object]:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("Groq response had no message content")
        result: dict[str, object] = json.loads(content)
        return result
