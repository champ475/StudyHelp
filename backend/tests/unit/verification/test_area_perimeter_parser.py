import pytest

from studyhelp.verification.topics.area_perimeter.free_text_parser import parse_student_text


def test_compute_area_parses() -> None:
    assert parse_student_text("compute_area", "6 x 4 = 24") == {"length": 6, "width": 4, "result": 24}


def test_compute_perimeter_parses() -> None:
    assert parse_student_text("compute_perimeter", "2 x (6 + 4) = 20") == {
        "length": 6,
        "width": 4,
        "result": 20,
    }


def test_write_final_answer_parses() -> None:
    assert parse_student_text("write_final_answer", "24") == {"value": 24}


def test_compute_area_rejects_perimeter_shape() -> None:
    with pytest.raises(ValueError, match="not of the form"):
        parse_student_text("compute_area", "2 x (6 + 4) = 20")


def test_compute_perimeter_rejects_area_shape() -> None:
    with pytest.raises(ValueError, match="not of the form"):
        parse_student_text("compute_perimeter", "6 x 4 = 24")


def test_garbage_text_rejected_for_every_step_type() -> None:
    for step_type in ("compute_area", "compute_perimeter", "write_final_answer"):
        with pytest.raises(ValueError):
            parse_student_text(step_type, "banana")
