"""Deterministic free-text math parser for fraction step submissions.

ARCHITECTURE.md D12 originally banned free-text math input outright; this
module is the one place that decision was deliberately superseded (see
ARCHITECTURE.md's dated supersede entry) at the founder's explicit request.
The supersede is narrow: the parser is a small regex grammar covering
exactly the handful of shapes a Class-5 fraction step can legally take
(a "a/b", "a b/c", "a/b + c/d", "a/b - c/d") — never a general expression
evaluator, and never handed to the LLM. Anything outside the grammar raises
`ValueError`, which the verifier reports as `ErrorSignal(kind="malformed")`
— the same fail-closed behavior `pydantic.ValidationError` gives the
structured-widget topics.
"""

from __future__ import annotations

import re
from math import gcd
from typing import Any

_FRACTION = r"(\d+)\s*/\s*(\d+)"
_TWO_FRACTION_EXPR = re.compile(rf"^\s*{_FRACTION}\s*([+\-])\s*{_FRACTION}\s*$")
_SINGLE_FRACTION = re.compile(rf"^\s*{_FRACTION}\s*$")
_MIXED_NUMBER = re.compile(rf"^\s*(\d+)\s+{_FRACTION}\s*$")
_WHOLE_NUMBER = re.compile(r"^\s*(\d+)\s*$")


def _nonzero_denominator(den: int, raw: str) -> int:
    if den == 0:
        raise ValueError(f"'{raw}': denominator cannot be zero")
    return den


def parse_rewrite_common_denominator(text: str) -> dict[str, Any]:
    match = _TWO_FRACTION_EXPR.match(text)
    if not match:
        raise ValueError(f"'{text}' is not of the form 'a/b + c/d' or 'a/b - c/d'")
    left_num, left_den, op, right_num, right_den = match.groups()
    return {
        "left_num": int(left_num),
        "left_den": _nonzero_denominator(int(left_den), text),
        "op": op,
        "right_num": int(right_num),
        "right_den": _nonzero_denominator(int(right_den), text),
    }


def parse_single_fraction(text: str) -> dict[str, Any]:
    match = _SINGLE_FRACTION.match(text)
    if not match:
        raise ValueError(f"'{text}' is not of the form 'a/b'")
    num, den = match.groups()
    return {"num": int(num), "den": _nonzero_denominator(int(den), text)}


def parse_final_answer(text: str) -> dict[str, Any]:
    """Accepts a fraction, a mixed number, or a whole number, and always
    normalizes to a reduced improper-fraction `num`/`den` pair — the final
    answer's `expected_state` is authored in the same reduced form, so a
    student writing "1 1/2" and one writing "3/2" must compare equal."""
    mixed = _MIXED_NUMBER.match(text)
    if mixed:
        whole, num, den = (int(g) for g in mixed.groups())
        den = _nonzero_denominator(den, text)
        return _reduce(whole * den + num, den)

    fraction = _SINGLE_FRACTION.match(text)
    if fraction:
        num, den = (int(g) for g in fraction.groups())
        return _reduce(num, _nonzero_denominator(den, text))

    whole_match = _WHOLE_NUMBER.match(text)
    if whole_match:
        return _reduce(int(whole_match.group(1)), 1)

    raise ValueError(f"'{text}' is not a whole number, fraction, or mixed number")


def _reduce(num: int, den: int) -> dict[str, Any]:
    divisor = gcd(num, den) or 1
    return {"num": num // divisor, "den": den // divisor}


_PARSERS = {
    "rewrite_common_denominator": parse_rewrite_common_denominator,
    "add_numerators": parse_single_fraction,
    "simplify_fraction": parse_single_fraction,
    "write_final_answer": parse_final_answer,
}


def parse_student_text(step_type: str, text: str) -> dict[str, Any]:
    """Raises `ValueError` (caught by the verifier, reported as
    `ErrorSignal(kind="malformed")`) if `text` doesn't match `step_type`'s
    grammar. Caller must confirm `step_type in _PARSERS` first."""
    return _PARSERS[step_type](text.strip())
