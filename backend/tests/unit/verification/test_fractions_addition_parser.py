import pytest

from studyhelp.verification.topics.fractions_addition.free_text_parser import parse_student_text


def test_rewrite_common_denominator_parses_plus_expression() -> None:
    fields = parse_student_text("rewrite_common_denominator", "3/12 + 2/12")
    assert fields == {"left_num": 3, "left_den": 12, "op": "+", "right_num": 2, "right_den": 12}


def test_rewrite_common_denominator_rejects_single_fraction() -> None:
    with pytest.raises(ValueError, match="not of the form"):
        parse_student_text("rewrite_common_denominator", "5/12")


def test_add_numerators_parses_single_fraction() -> None:
    assert parse_student_text("add_numerators", "5/12") == {"num": 5, "den": 12}


def test_final_answer_normalizes_mixed_number() -> None:
    assert parse_student_text("write_final_answer", "1 1/2") == {"num": 3, "den": 2}


def test_final_answer_reduces_unsimplified_fraction() -> None:
    assert parse_student_text("write_final_answer", "4/6") == {"num": 2, "den": 3}


def test_final_answer_parses_whole_number() -> None:
    assert parse_student_text("write_final_answer", "2") == {"num": 2, "den": 1}


def test_zero_denominator_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be zero"):
        parse_student_text("add_numerators", "5/0")


def test_garbage_text_rejected() -> None:
    with pytest.raises(ValueError):
        parse_student_text("add_numerators", "banana")
