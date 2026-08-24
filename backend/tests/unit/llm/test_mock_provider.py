from studyhelp.llm.client import (
    ClassifyCandidate,
    ClassifyRequest,
    DecideRequest,
    DecideResponse,
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


async def test_procedural_message_varies_by_topic() -> None:
    """Open-ended-review finding #3 regression: the non-analogy procedural/
    conceptual branch used to be one fixed string regardless of topic —
    confirmed misleadingly identical across topics in the e2e sweep."""
    provider = MockLLMProvider()
    decision = DecideResponse(
        error_type="procedural", remediation_strategy="x", instructional_intent="y"
    )
    a = await provider.generate(
        GenerateRequest(
            decision=decision,
            conversation_so_far=[],
            correct_step={},
            student_step={},
            topic="fractions_addition",
        )
    )
    b = await provider.generate(
        GenerateRequest(
            decision=decision,
            conversation_so_far=[],
            correct_step={},
            student_step={},
            topic="area_perimeter",
        )
    )
    assert a.message != b.message


async def test_procedural_message_varies_by_hint_level() -> None:
    provider = MockLLMProvider()
    decision = DecideResponse(
        error_type="procedural", remediation_strategy="x", instructional_intent="y"
    )
    short = await provider.generate(
        GenerateRequest(
            decision=decision,
            conversation_so_far=[],
            correct_step={},
            student_step={},
            topic="decimals",
        )
    )
    long = await provider.generate(
        GenerateRequest(
            decision=decision,
            conversation_so_far=[{"role": "tutor", "text": "x"}] * 6,
            correct_step={},
            student_step={},
            topic="decimals",
        )
    )
    assert short.message != long.message


async def test_procedural_message_distinguishes_step_family_within_one_topic() -> None:
    """CLAUDE.md live-testing Bug D regression: area_perimeter's chapter
    mixes two distinct operations under one topic string — a pure-area step
    and a pure-perimeter step must not get identically-focused phrasing."""
    provider = MockLLMProvider()
    decision = DecideResponse(
        error_type="procedural", remediation_strategy="x", instructional_intent="y"
    )
    area = await provider.generate(
        GenerateRequest(
            decision=decision,
            conversation_so_far=[],
            correct_step={"length": 6, "width": 4, "result": 24},
            student_step={},
            topic="area_perimeter",
            step_type="compute_area",
            given={"shape": "rectangle", "length": 6, "width": 4, "measure": "area"},
        )
    )
    perimeter = await provider.generate(
        GenerateRequest(
            decision=decision,
            conversation_so_far=[],
            correct_step={"length": 6, "width": 4, "result": 20},
            student_step={},
            topic="area_perimeter",
            step_type="compute_perimeter",
            given={"shape": "rectangle", "length": 6, "width": 4, "measure": "perimeter"},
        )
    )
    assert area.message != perimeter.message
    assert "space inside" in area.message
    assert "distance around" in perimeter.message


async def test_procedural_message_falls_back_for_unknown_topic() -> None:
    provider = MockLLMProvider()
    decision = DecideResponse(
        error_type="procedural", remediation_strategy="x", instructional_intent="y"
    )
    response = await provider.generate(
        GenerateRequest(
            decision=decision,
            conversation_so_far=[],
            correct_step={},
            student_step={},
            topic="a_future_topic_not_in_the_dict",
        )
    )
    assert "idea behind this step" in response.message


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
