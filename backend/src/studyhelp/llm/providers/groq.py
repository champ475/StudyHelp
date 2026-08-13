"""Real Groq provider.

**Not verified against a live API.** No Groq API key has been provided yet
(ARCHITECTURE.md D17); this module is written to the shape of Groq's
OpenAI-compatible chat-completions API (JSON mode for structured output),
but its actual structured-output reliability for the configured
`GROQ_MODEL` has not been tested. Per CLAUDE.md's explicit instruction,
verify this directly — don't assume — before `LLM_PROVIDER=groq` is used
anywhere beyond local, supervised testing. `build_llm_client()`
(llm/client.py) refuses to construct this provider at all unless both
`GROQ_API_KEY` and `GROQ_MODEL` are explicitly set, so nothing silently
ships with an unverified default model.
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
        raise NotImplementedError(
            "GroqLLMProvider.decide() is scoped to Phase 3 (dialogue orchestrator) — not wired yet."
        )

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        raise NotImplementedError(
            "GroqLLMProvider.generate() is scoped to Phase 3 (dialogue orchestrator) — "
            "not wired yet."
        )

    async def _chat_json(self, system_prompt: str, user_content: str) -> dict[str, object]:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("Groq response had no message content")
        result: dict[str, object] = json.loads(content)
        return result
