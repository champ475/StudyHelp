"""One-off verification: does the configured GROQ_MODEL reliably return
valid structured (JSON-mode) output for classify/decide/generate?

CLAUDE.md requires verifying this directly before trusting a Groq model
anywhere beyond local, supervised testing (ARCHITECTURE.md D17/D25) — never
assume JSON mode "just works" for a given model. This script fires one real
call per method against the live API and reports pass/fail plainly; it does
not touch the database or any other part of the app.

Usage: GROQ_API_KEY=... GROQ_MODEL=... python scripts/verify_groq_structured_output.py
(reads from backend/.env via the normal Settings loader if not set in the
shell environment)
"""

import asyncio
import sys

from studyhelp.config import get_settings
from studyhelp.llm.client import ClassifyCandidate, ClassifyRequest, DecideRequest, GenerateRequest
from studyhelp.llm.providers.groq import GroqLLMProvider


async def main() -> int:
    settings = get_settings()
    if not settings.groq_api_key or not settings.groq_model:
        print("FAIL: GROQ_API_KEY / GROQ_MODEL not set in backend/.env or environment.")
        return 1

    print(f"Verifying structured-output reliability for model: {settings.groq_model}")
    provider = GroqLLMProvider(api_key=settings.groq_api_key, model=settings.groq_model)

    ok = True

    # --- classify() ---
    try:
        classify_result = await provider.classify(
            ClassifyRequest(
                topic="subtraction_borrowing",
                step_type="subtract_column",
                correct_step={"column": "units", "result_digit": 7},
                student_step={"column": "units", "result_digit": 3},
                candidates=[
                    ClassifyCandidate(
                        misconception_id="M-SUB-SMALLER-FROM-LARGER",
                        typical_mindset="Always subtracts the smaller digit from the larger one in a column, regardless of position, instead of borrowing.",
                    )
                ],
            )
        )
        assert classify_result.misconception_id is None or classify_result.misconception_id == "M-SUB-SMALLER-FROM-LARGER"
        assert isinstance(classify_result.rationale, str) and classify_result.rationale
        print(f"  classify(): OK -> {classify_result.model_dump()}")
    except Exception as exc:  # noqa: BLE001 - this is a diagnostic script, report anything
        ok = False
        print(f"  classify(): FAIL -> {exc!r}")

    # --- decide() ---
    decision = None
    try:
        decision = await provider.decide(
            DecideRequest(
                topic="subtraction_borrowing",
                step_type="subtract_column",
                correct_step={"column": "units", "result_digit": 7},
                student_step={"column": "units", "result_digit": 3},
                misconception=ClassifyCandidate(
                    misconception_id="M-SUB-SMALLER-FROM-LARGER",
                    typical_mindset="Always subtracts the smaller digit from the larger one in a column, regardless of position, instead of borrowing.",
                ),
                turn_number=1,
            )
        )
        assert decision.error_type in ("careless", "procedural", "conceptual")
        assert decision.remediation_strategy and decision.instructional_intent
        print(f"  decide(): OK -> {decision.model_dump()}")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"  decide(): FAIL -> {exc!r}")

    # --- generate() ---
    try:
        if decision is None:
            raise RuntimeError("skipped: decide() failed above, nothing to condition generate() on")
        generated = await provider.generate(
            GenerateRequest(
                decision=decision,
                conversation_so_far=[],
                correct_step={"column": "units", "result_digit": 7},
                student_step={"column": "units", "result_digit": 3},
            )
        )
        assert isinstance(generated.message, str) and generated.message
        assert "7" not in generated.message, "generated message may be leaking the correct result_digit"
        print(f"  generate(): OK -> {generated.model_dump()}")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"  generate(): FAIL -> {exc!r}")

    print()
    print("RESULT: model reliably supports structured output." if ok else "RESULT: model FAILED structured-output verification — do not trust LLM_PROVIDER=groq with this model yet.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
