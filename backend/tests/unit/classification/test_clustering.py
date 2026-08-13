from studyhelp.classification.clustering import cluster_signature


def test_signature_is_deterministic() -> None:
    a = cluster_signature(
        "subtraction_with_borrowing", "borrow", ["to_digit_after", "from_digit_after"]
    )
    b = cluster_signature(
        "subtraction_with_borrowing", "borrow", ["from_digit_after", "to_digit_after"]
    )
    assert a == b, "field order should not affect the signature"


def test_signature_differs_by_step_type() -> None:
    a = cluster_signature("subtraction_with_borrowing", "borrow", ["to_digit_after"])
    b = cluster_signature("subtraction_with_borrowing", "subtract_column", ["to_digit_after"])
    assert a != b


def test_signature_differs_by_field_set() -> None:
    a = cluster_signature("subtraction_with_borrowing", "borrow", ["to_digit_after"])
    b = cluster_signature("subtraction_with_borrowing", "borrow", ["from_digit_after"])
    assert a != b


def test_signature_handles_empty_discrepant_fields() -> None:
    sig = cluster_signature("subtraction_with_borrowing", "borrow", [])
    assert "none" in sig
