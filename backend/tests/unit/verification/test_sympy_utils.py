from studyhelp.verification.topics.subtraction_borrowing.sympy_utils import (
    check_borrow_arithmetic,
    check_final_identity,
    check_subtract_arithmetic,
)


def test_check_final_identity_true_case() -> None:
    assert check_final_identity(542, 187, 355) is True


def test_check_final_identity_false_case() -> None:
    assert check_final_identity(542, 187, 300) is False


def test_check_borrow_arithmetic_true_case() -> None:
    assert (
        check_borrow_arithmetic(
            from_digit_before=4, from_digit_after=3, to_digit_before=2, to_digit_after=12
        )
        is True
    )


def test_check_borrow_arithmetic_false_when_lender_not_decremented() -> None:
    """Directly exercises the B2 bug shape (borrow without paying it back)."""
    assert (
        check_borrow_arithmetic(
            from_digit_before=4, from_digit_after=4, to_digit_before=2, to_digit_after=12
        )
        is False
    )


def test_check_subtract_arithmetic_true_case() -> None:
    assert check_subtract_arithmetic(12, 7, 5) is True


def test_check_subtract_arithmetic_false_case() -> None:
    assert check_subtract_arithmetic(12, 7, 6) is False
