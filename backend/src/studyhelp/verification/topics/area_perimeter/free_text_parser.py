"""Deterministic free-text parser for area/perimeter step submissions
(ARCHITECTURE.md D41/D43) — one small regex grammar per step type, never a
general expression evaluator, never handed to the LLM. Anything outside
the grammar raises `ValueError`, reported as `ErrorSignal(kind="malformed")`.

The grammar stays uniform regardless of shape (rectangle vs square) — the
parser only ever sees `(step_type, text)`, never the problem's `given`, so
it never special-cases "this is a square." A square is just a problem
whose `given.length == given.width`.

Grammar per step type:
- compute_area:        "<L> x <W> = <result>", e.g. "6 x 4 = 24".
- compute_perimeter:    "2 x (<L> + <W>) = <result>", e.g. "2 x (6 + 4) = 20".
- write_final_answer:   a bare integer, e.g. "24".
"""

from __future__ import annotations

import re
from typing import Any

_COMPUTE_AREA = re.compile(r"^\s*(\d+)\s*x\s*(\d+)\s*=\s*(\d+)\s*$", re.IGNORECASE)
_COMPUTE_PERIMETER = re.compile(
    r"^\s*2\s*x\s*\(\s*(\d+)\s*\+\s*(\d+)\s*\)\s*=\s*(\d+)\s*$", re.IGNORECASE
)
_WHOLE_NUMBER = re.compile(r"^\s*(\d+)\s*$")


def parse_compute_area(text: str) -> dict[str, Any]:
    match = _COMPUTE_AREA.match(text)
    if not match:
        raise ValueError(f"'{text}' is not of the form '<length> x <width> = <result>', e.g. '6 x 4 = 24'")
    length, width, result = match.groups()
    return {"length": int(length), "width": int(width), "result": int(result)}


def parse_compute_perimeter(text: str) -> dict[str, Any]:
    match = _COMPUTE_PERIMETER.match(text)
    if not match:
        raise ValueError(
            f"'{text}' is not of the form '2 x (<length> + <width>) = <result>', e.g. '2 x (6 + 4) = 20'"
        )
    length, width, result = match.groups()
    return {"length": int(length), "width": int(width), "result": int(result)}


def parse_write_final_answer(text: str) -> dict[str, Any]:
    match = _WHOLE_NUMBER.match(text)
    if not match:
        raise ValueError(f"'{text}' is not a whole number")
    return {"value": int(match.group(1))}


_PARSERS = {
    "compute_area": parse_compute_area,
    "compute_perimeter": parse_compute_perimeter,
    "write_final_answer": parse_write_final_answer,
}


def parse_student_text(step_type: str, text: str) -> dict[str, Any]:
    """Raises `ValueError` (caught by the verifier, reported as
    `ErrorSignal(kind="malformed")`) if `text` doesn't match `step_type`'s
    grammar. Caller must confirm `step_type in _PARSERS` first."""
    return _PARSERS[step_type](text.strip())
