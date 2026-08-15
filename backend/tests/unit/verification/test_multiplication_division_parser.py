import pytest

from studyhelp.verification.topics.multiplication_division.free_text_parser import (
    parse_student_text,
)


def test_multiply_units_parses() -> None:
    assert parse_student_text("multiply_units", "4 x 6 = 24") == {
        "digit": 4,
        "multiplier": 6,
        "product": 24,
    }


def test_multiply_tens_parses() -> None:
    assert parse_student_text("multiply_tens", "3 x 6 + 2 = 20") == {
        "digit": 3,
        "multiplier": 6,
        "carry_in": 2,
        "product": 20,
    }


def test_divide_parses() -> None:
    assert parse_student_text("divide_tens", "9 / 8 = 1 remainder 1") == {
        "dividend_group": 9,
        "divisor": 8,
        "quotient_digit": 1,
        "remainder": 1,
    }
    assert parse_student_text("divide_units", "16 / 8 = 2 remainder 0") == {
        "dividend_group": 16,
        "divisor": 8,
        "quotient_digit": 2,
        "remainder": 0,
    }


def test_write_final_answer_parses() -> None:
    assert parse_student_text("write_final_answer", "204") == {"value": 204}


def test_multiply_units_rejects_tens_shape() -> None:
    with pytest.raises(ValueError, match="not of the form"):
        parse_student_text("multiply_units", "3 x 6 + 2 = 20")


def test_divide_rejects_missing_remainder_keyword() -> None:
    with pytest.raises(ValueError, match="not of the form"):
        parse_student_text("divide_tens", "9 / 8 = 1")


def test_garbage_text_rejected_for_every_step_type() -> None:
    for step_type in ("multiply_units", "multiply_tens", "divide_tens", "divide_units", "write_final_answer"):
        with pytest.raises(ValueError):
            parse_student_text(step_type, "banana")
