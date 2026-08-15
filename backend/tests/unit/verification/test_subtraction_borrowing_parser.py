import pytest

from studyhelp.verification.topics.subtraction_borrowing.free_text_parser import parse_student_text


def test_compare_column_parses_borrow_needed() -> None:
    assert parse_student_text("compare_column", "units 2 < 7") == {
        "column": "units",
        "minuend_digit": 2,
        "subtrahend_digit": 7,
        "borrow_needed": True,
    }


def test_compare_column_parses_no_borrow_needed() -> None:
    assert parse_student_text("compare_column", "tens 9 >= 5") == {
        "column": "tens",
        "minuend_digit": 9,
        "subtrahend_digit": 5,
        "borrow_needed": False,
    }


def test_compare_column_rejects_unknown_column() -> None:
    with pytest.raises(ValueError, match="not a known column"):
        parse_student_text("compare_column", "crores 2 < 7")


def test_borrow_parses_granular_form() -> None:
    assert parse_student_text("borrow", "tens 4->3, units 2->12") == {
        "from_column": "tens",
        "from_digit_before": 4,
        "from_digit_after": 3,
        "to_column": "units",
        "to_digit_before": 2,
        "to_digit_after": 12,
    }


def test_borrow_parses_combined_result_suffix() -> None:
    assert parse_student_text("borrow", "tens 4->3, units 2->12, result 5") == {
        "from_column": "tens",
        "from_digit_before": 4,
        "from_digit_after": 3,
        "to_column": "units",
        "to_digit_before": 2,
        "to_digit_after": 12,
        "combined_result_digit": 5,
    }


def test_subtract_column_parses() -> None:
    assert parse_student_text("subtract_column", "units 12 - 7 = 5") == {
        "column": "units",
        "minuend_digit": 12,
        "subtrahend_digit": 7,
        "result_digit": 5,
    }


def test_write_final_answer_decomposes_by_place_value() -> None:
    assert parse_student_text("write_final_answer", "355") == {
        "digits": {"hundreds": 3, "tens": 5, "units": 5},
        "value": 355,
    }


def test_write_final_answer_omits_leading_zero_places() -> None:
    assert parse_student_text("write_final_answer", "27") == {
        "digits": {"tens": 2, "units": 7},
        "value": 27,
    }


def test_write_final_answer_rejects_non_numeric() -> None:
    with pytest.raises(ValueError, match="not a whole number"):
        parse_student_text("write_final_answer", "three fifty five")


def test_garbage_text_rejected_for_every_step_type() -> None:
    for step_type in ("compare_column", "borrow", "subtract_column", "write_final_answer"):
        with pytest.raises(ValueError):
            parse_student_text(step_type, "banana")
