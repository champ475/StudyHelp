import pytest

from studyhelp.verification.topics.lcm_hcf.free_text_parser import parse_student_text


def test_find_common_values_parses_and_sorts_hcf_list() -> None:
    assert parse_student_text("find_common_values", "1,2,3,6") == {"values": [1, 2, 3, 6]}


def test_find_common_values_sorts_out_of_order_input() -> None:
    assert parse_student_text("find_common_values", "6,1,3,2") == {"values": [1, 2, 3, 6]}


def test_find_common_values_parses_lcm_list_with_spaces() -> None:
    assert parse_student_text("find_common_values", "12, 24, 36") == {"values": [12, 24, 36]}


def test_write_final_answer_parses_whole_number() -> None:
    assert parse_student_text("write_final_answer", "6") == {"value": 6}


def test_find_common_values_rejects_non_numeric() -> None:
    with pytest.raises(ValueError, match="comma-separated"):
        parse_student_text("find_common_values", "one,two,three")


def test_write_final_answer_rejects_non_numeric() -> None:
    with pytest.raises(ValueError, match="not a whole number"):
        parse_student_text("write_final_answer", "six")


def test_garbage_text_rejected_for_every_step_type() -> None:
    for step_type in ("find_common_values", "write_final_answer"):
        with pytest.raises(ValueError):
            parse_student_text(step_type, "banana")
