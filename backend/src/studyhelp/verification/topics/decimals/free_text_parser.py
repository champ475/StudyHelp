"""Deterministic free-text parser for decimal-addition/subtraction step
submissions (ARCHITECTURE.md D41/D43) — one small regex grammar per step
type, never a general expression evaluator, never handed to the LLM.
Anything outside the grammar raises `ValueError`, reported as
`ErrorSignal(kind="malformed")`.

Every decimal is represented internally as an integer count of hundredths
(e.g. "3.4" -> 340, "3.40" -> 340, "3" -> 300) so all downstream comparison
and arithmetic stays exact-integer, never floating point.

Grammar per step type:
- align_place_value:  two decimal (or whole) numbers separated by a comma,
                       e.g. "3.4, 1.25" or "5, 2.35".
- compute_result:      a single decimal (or whole) number, e.g. "4.65".
- write_final_answer:  same single-number grammar as compute_result.
"""

from __future__ import annotations

import re
from typing import Any

_NUMBER = r"(\d+)(?:\.(\d{1,2}))?"
_TWO_NUMBERS = re.compile(rf"^\s*{_NUMBER}\s*,\s*{_NUMBER}\s*$")
_SINGLE_NUMBER = re.compile(rf"^\s*{_NUMBER}\s*$")


def _to_hundredths(whole: str, frac: str | None) -> int:
    if not frac:
        return int(whole) * 100
    if len(frac) == 1:
        return int(whole) * 100 + int(frac) * 10
    return int(whole) * 100 + int(frac)


def parse_align_place_value(text: str) -> dict[str, Any]:
    match = _TWO_NUMBERS.match(text)
    if not match:
        raise ValueError(f"'{text}' is not of the form 'a.bc, d.ef', e.g. '3.40, 1.25'")
    a_whole, a_frac, b_whole, b_frac = match.groups()
    return {
        "a_hundredths": _to_hundredths(a_whole, a_frac),
        "b_hundredths": _to_hundredths(b_whole, b_frac),
    }


def parse_compute_result(text: str) -> dict[str, Any]:
    match = _SINGLE_NUMBER.match(text)
    if not match:
        raise ValueError(f"'{text}' is not a decimal number, e.g. '4.65'")
    whole, frac = match.groups()
    return {"result_hundredths": _to_hundredths(whole, frac)}


_PARSERS = {
    "align_place_value": parse_align_place_value,
    "compute_result": parse_compute_result,
    "write_final_answer": parse_compute_result,
}


def parse_student_text(step_type: str, text: str) -> dict[str, Any]:
    """Raises `ValueError` (caught by the verifier, reported as
    `ErrorSignal(kind="malformed")`) if `text` doesn't match `step_type`'s
    grammar. Caller must confirm `step_type in _PARSERS` first."""
    return _PARSERS[step_type](text.strip())
