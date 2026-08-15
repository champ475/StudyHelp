import pytest

from studyhelp.verification.topics.decimals.free_text_parser import parse_student_text


def test_align_place_value_parses_two_decimals() -> None:
    assert parse_student_text("align_place_value", "3.40, 1.25") == {
        "a_hundredths": 340,
        "b_hundredths": 125,
    }


def test_align_place_value_pads_a_single_decimal_digit() -> None:
    assert parse_student_text("align_place_value", "3.4, 1.25") == {
        "a_hundredths": 340,
        "b_hundredths": 125,
    }


def test_align_place_value_accepts_a_bare_whole_number() -> None:
    assert parse_student_text("align_place_value", "5, 2.35") == {
        "a_hundredths": 500,
        "b_hundredths": 235,
    }


def test_align_place_value_rejects_missing_comma() -> None:
    with pytest.raises(ValueError, match="not of the form"):
        parse_student_text("align_place_value", "3.40 1.25")


def test_compute_result_parses_decimal() -> None:
    assert parse_student_text("compute_result", "4.65") == {"result_hundredths": 465}


def test_compute_result_pads_single_decimal_digit() -> None:
    assert parse_student_text("compute_result", "9.6") == {"result_hundredths": 960}


def test_write_final_answer_parses_whole_number() -> None:
    assert parse_student_text("write_final_answer", "15") == {"result_hundredths": 1500}


def test_garbage_text_rejected_for_every_step_type() -> None:
    for step_type in ("align_place_value", "compute_result", "write_final_answer"):
        with pytest.raises(ValueError):
            parse_student_text(step_type, "banana")
