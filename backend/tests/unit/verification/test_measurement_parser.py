import pytest

from studyhelp.verification.topics.measurement.free_text_parser import parse_student_text


def test_identify_conversion_factor_parses_multiply() -> None:
    assert parse_student_text("identify_conversion_factor", "x1000") == {
        "direction": "x",
        "factor": 1000,
    }


def test_identify_conversion_factor_parses_divide_slash() -> None:
    assert parse_student_text("identify_conversion_factor", "/1000") == {
        "direction": "/",
        "factor": 1000,
    }


def test_identify_conversion_factor_accepts_division_symbol() -> None:
    assert parse_student_text("identify_conversion_factor", "÷100") == {
        "direction": "/",
        "factor": 100,
    }


def test_convert_units_parses() -> None:
    assert parse_student_text("convert_units", "3000") == {"value": 3000}


def test_write_final_answer_parses() -> None:
    assert parse_student_text("write_final_answer", "3000") == {"value": 3000}


def test_garbage_text_rejected_for_every_step_type() -> None:
    for step_type in ("identify_conversion_factor", "convert_units", "write_final_answer"):
        with pytest.raises(ValueError):
            parse_student_text(step_type, "banana")
