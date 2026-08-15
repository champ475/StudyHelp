"""Deterministic free-text parser for multiplication/division step
submissions (ARCHITECTURE.md D41/D43) — one small regex grammar per step
type, never a general expression evaluator, never handed to the LLM.
Anything outside the grammar raises `ValueError`, reported as
`ErrorSignal(kind="malformed")`.

Grammar per step type:
- multiply_units:      "<digit> x <multiplier> = <product>", e.g. "4 x 6 = 24".
- multiply_tens:        "<digit> x <multiplier> + <carry_in> = <product>",
                        e.g. "3 x 6 + 2 = 20" — the student states the
                        carrying explicitly, which is what makes a
                        forgot-the-carry bug (MD1) checkable at all.
- divide_tens:          "<dividend_group> / <divisor> = <quotient_digit> remainder <remainder>",
                        e.g. "9 / 8 = 1 remainder 1".
- divide_units:         same grammar as divide_tens.
- write_final_answer:   a bare integer.
"""

from __future__ import annotations

import re
from typing import Any

_MULTIPLY_UNITS = re.compile(r"^\s*(\d+)\s*x\s*(\d+)\s*=\s*(\d+)\s*$", re.IGNORECASE)
_MULTIPLY_TENS = re.compile(
    r"^\s*(\d+)\s*x\s*(\d+)\s*\+\s*(\d+)\s*=\s*(\d+)\s*$", re.IGNORECASE
)
_DIVIDE = re.compile(
    r"^\s*(\d+)\s*/\s*(\d+)\s*=\s*(\d+)\s*remainder\s*(\d+)\s*$", re.IGNORECASE
)
_WHOLE_NUMBER = re.compile(r"^\s*(\d+)\s*$")


def parse_multiply_units(text: str) -> dict[str, Any]:
    match = _MULTIPLY_UNITS.match(text)
    if not match:
        raise ValueError(f"'{text}' is not of the form '<digit> x <multiplier> = <product>', e.g. '4 x 6 = 24'")
    digit, multiplier, product = match.groups()
    return {"digit": int(digit), "multiplier": int(multiplier), "product": int(product)}


def parse_multiply_tens(text: str) -> dict[str, Any]:
    match = _MULTIPLY_TENS.match(text)
    if not match:
        raise ValueError(
            f"'{text}' is not of the form '<digit> x <multiplier> + <carry_in> = <product>', "
            "e.g. '3 x 6 + 2 = 20'"
        )
    digit, multiplier, carry_in, product = match.groups()
    return {
        "digit": int(digit),
        "multiplier": int(multiplier),
        "carry_in": int(carry_in),
        "product": int(product),
    }


def parse_divide(text: str) -> dict[str, Any]:
    match = _DIVIDE.match(text)
    if not match:
        raise ValueError(
            f"'{text}' is not of the form '<dividend_group> / <divisor> = <quotient_digit> remainder <remainder>', "
            "e.g. '9 / 8 = 1 remainder 1'"
        )
    dividend_group, divisor, quotient_digit, remainder = match.groups()
    return {
        "dividend_group": int(dividend_group),
        "divisor": int(divisor),
        "quotient_digit": int(quotient_digit),
        "remainder": int(remainder),
    }


def parse_write_final_answer(text: str) -> dict[str, Any]:
    match = _WHOLE_NUMBER.match(text)
    if not match:
        raise ValueError(f"'{text}' is not a whole number")
    return {"value": int(match.group(1))}


_PARSERS = {
    "multiply_units": parse_multiply_units,
    "multiply_tens": parse_multiply_tens,
    "divide_tens": parse_divide,
    "divide_units": parse_divide,
    "write_final_answer": parse_write_final_answer,
}


def parse_student_text(step_type: str, text: str) -> dict[str, Any]:
    """Raises `ValueError` (caught by the verifier, reported as
    `ErrorSignal(kind="malformed")`) if `text` doesn't match `step_type`'s
    grammar. Caller must confirm `step_type in _PARSERS` first."""
    return _PARSERS[step_type](text.strip())
