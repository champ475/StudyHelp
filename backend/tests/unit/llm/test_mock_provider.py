from studyhelp.llm.client import (
    ClassifyCandidate,
    ClassifyRequest,
    DecideRequest,
    GenerateRequest,
)
from studyhelp.llm.providers.mock import MockLLMProvider


async def test_classify_returns_none_when_no_candidates() -> None:
    provider = MockLLMProvider()
    response = await provider.classify(
        ClassifyRequest(
            topic="subtraction_with_borrowing",
            step_type="subtract_column",
            correct_step={},
            student_step={},
            candidates=[],
        )
    )
    assert response.misconception_id is None


async def test_classify_picks_first_candidate_deterministically() -> None:
    provider = MockLLMProvider()
    candidates = [
        ClassifyCandidate(misconception_id="a", typical_mindset="mindset a"),
        ClassifyCandidate(misconception_id="b", typical_mindset="mindset b"),
    ]
    response = await provider.classify(
        ClassifyRequest(
            topic="t", step_type="s", correct_step={}, student_step={}, candidates=candidates
        )
    )
    assert response.misconception_id == "a"


async def test_decide_uses_procedural_when_misconception_given() -> None:
    provider = MockLLMProvider()
    response = await provider.decide(
        DecideRequest(
            topic="t",
            step_type="s",
            correct_step={},
            student_step={},
            misconception=ClassifyCandidate(misconception_id="a", typical_mindset="m"),
            turn_number=1,
        )
    )
    assert response.error_type == "procedural"


async def test_decide_uses_careless_without_misconception() -> None:
    provider = MockLLMProvider()
    response = await provider.decide(
        DecideRequest(
            topic="t",
            step_type="s",
            correct_step={},
            student_step={},
            misconception=None,
            turn_number=1,
        )
    )
    assert response.error_type == "careless"


async def test_generate_hint_level_increases_with_conversation_length() -> None:
    provider = MockLLMProvider()
    decision = await provider.decide(
        DecideRequest(
            topic="t",
            step_type="s",
            correct_step={},
            student_step={},
            misconception=None,
            turn_number=1,
        )
    )
    short = await provider.generate(
        GenerateRequest(decision=decision, conversation_so_far=[], correct_step={}, student_step={})
    )
    long = await provider.generate(
        GenerateRequest(
            decision=decision,
            conversation_so_far=[{"role": "tutor", "text": "x"}] * 6,
            correct_step={},
            student_step={},
        )
    )
    assert short.hint_level < long.hint_level


async def test_overrides_take_priority() -> None:
    from studyhelp.llm.client import ClassifyResponse

    override = ClassifyResponse(misconception_id="not-a-real-candidate", rationale="adversarial")
    provider = MockLLMProvider(classify_override=override)
    response = await provider.classify(
        ClassifyRequest(
            topic="t",
            step_type="s",
            correct_step={},
            student_step={},
            candidates=[ClassifyCandidate(misconception_id="a", typical_mindset="m")],
        )
    )
    assert response.misconception_id == "not-a-real-candidate"
