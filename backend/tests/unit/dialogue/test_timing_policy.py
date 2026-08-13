import pytest

from studyhelp.dialogue.timing_policy import InterventionPolicy, should_intervene


def test_immediate_always_intervenes() -> None:
    assert should_intervene(
        InterventionPolicy.IMMEDIATE, consecutive_errors_on_this_step=1, problem_is_complete=False
    )


def test_after_nth_repeat_waits_until_threshold() -> None:
    assert not should_intervene(
        InterventionPolicy.AFTER_NTH_REPEAT,
        consecutive_errors_on_this_step=1,
        problem_is_complete=False,
    )
    assert should_intervene(
        InterventionPolicy.AFTER_NTH_REPEAT,
        consecutive_errors_on_this_step=2,
        problem_is_complete=False,
    )


def test_after_nth_repeat_respects_custom_threshold() -> None:
    assert not should_intervene(
        InterventionPolicy.AFTER_NTH_REPEAT,
        consecutive_errors_on_this_step=2,
        problem_is_complete=False,
        repeat_threshold=3,
    )
    assert should_intervene(
        InterventionPolicy.AFTER_NTH_REPEAT,
        consecutive_errors_on_this_step=3,
        problem_is_complete=False,
        repeat_threshold=3,
    )


def test_wait_for_completion_ignores_repeat_count() -> None:
    assert not should_intervene(
        InterventionPolicy.WAIT_FOR_COMPLETION,
        consecutive_errors_on_this_step=5,
        problem_is_complete=False,
    )
    assert should_intervene(
        InterventionPolicy.WAIT_FOR_COMPLETION,
        consecutive_errors_on_this_step=0,
        problem_is_complete=True,
    )


def test_unknown_policy_raises() -> None:
    with pytest.raises(ValueError, match="Unknown intervention policy"):
        should_intervene(
            "not-a-real-policy", consecutive_errors_on_this_step=1, problem_is_complete=False
        )  # type: ignore[arg-type]
