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
_FRACTION_COMPARISON = re.compile(rf"^\s*{_FRACTION}\s*(<|>|=)\s*{_FRACTION}\s*$")


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


def parse_final_answer(text: str, *, reduce: bool = True) -> dict[str, Any]:
    """Accepts a fraction, a mixed number, or a whole number. With
    `reduce=True` (the default — used whenever `write_final_answer` is the
    prescribed next step), always normalizes to a reduced improper-fraction
    `num`/`den` pair, since the final answer's `expected_state` is authored
    in the same reduced form and a student writing "1 1/2" and one writing
    "3/2" must compare equal there.

    `reduce=False` returns the literal, unreduced `num`/`den` the student
    typed. The verifier uses this when checking `write_final_answer` as a
    *non-adjacent* (skip-ahead) candidate (ARCHITECTURE.md D59): without it,
    an unsimplified-but-numerically-equivalent submission at an earlier step
    (e.g. "4/6" typed at `simplify_fraction`) would silently reduce to match
    the final node's expected value and get accepted as "the student jumped
    to the end," masking exactly the "forgot to simplify" error this
    topic's buggy-rule library exists to catch."""
    mixed = _MIXED_NUMBER.match(text)
    if mixed:
        whole, num, den = (int(g) for g in mixed.groups())
        den = _nonzero_denominator(den, text)
        total_num = whole * den + num
        return _reduce(total_num, den) if reduce else {"num": total_num, "den": den}

    fraction = _SINGLE_FRACTION.match(text)
    if fraction:
        num, den = (int(g) for g in fraction.groups())
        den = _nonzero_denominator(den, text)
        return _reduce(num, den) if reduce else {"num": num, "den": den}

    whole_match = _WHOLE_NUMBER.match(text)
    if whole_match:
        num = int(whole_match.group(1))
        return _reduce(num, 1) if reduce else {"num": num, "den": 1}

    raise ValueError(f"'{text}' is not a whole number, fraction, or mixed number")


def _reduce(num: int, den: int) -> dict[str, Any]:
    divisor = gcd(num, den) or 1
    return {"num": num // divisor, "den": den // divisor}


def parse_compare_fractions(text: str) -> dict[str, Any]:
    match = _FRACTION_COMPARISON.match(text)
    if not match:
        raise ValueError(f"'{text}' is not of the form 'a/b < c/d', 'a/b > c/d', or 'a/b = c/d'")
    left_num, left_den, op, right_num, right_den = match.groups()
    return {
        "left_num": int(left_num),
        "left_den": _nonzero_denominator(int(left_den), text),
        "op": op,
        "right_num": int(right_num),
        "right_den": _nonzero_denominator(int(right_den), text),
    }


_PARSERS = {
    "rewrite_common_denominator": parse_rewrite_common_denominator,
    "add_numerators": parse_single_fraction,
    "subtract_numerators": parse_single_fraction,
    "simplify_fraction": parse_single_fraction,
    "write_final_answer": parse_final_answer,
    "compare_fractions": parse_compare_fractions,
}


def parse_student_text(step_type: str, text: str) -> dict[str, Any]:
    """Raises `ValueError` (caught by the verifier, reported as
    `ErrorSignal(kind="malformed")`) if `text` doesn't match `step_type`'s
    grammar. Caller must confirm `step_type in _PARSERS` first."""
    return _PARSERS[step_type](text.strip())
