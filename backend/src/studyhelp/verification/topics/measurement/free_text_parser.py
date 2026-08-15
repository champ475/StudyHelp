"""Deterministic free-text parser for unit-conversion step submissions
(ARCHITECTURE.md D41/D43) — one small regex grammar per step type, never a
general expression evaluator, never handed to the LLM. Anything outside
the grammar raises `ValueError`, reported as `ErrorSignal(kind="malformed")`.

Grammar per step type:
- identify_conversion_factor: "x<factor>" or "/<factor>" (÷ also accepted
                              as an alternate spelling of "/", since a
                              student may not have a ÷ key), e.g. "x1000"
                              or "/1000". Always normalized to direction
                              "x" or "/" in the returned fields.
- convert_units:               a bare integer, e.g. "5000".
- write_final_answer:          same bare-integer grammar as convert_units.
"""

from __future__ import annotations

import re
from typing import Any

_CONVERSION_FACTOR = re.compile(r"^\s*(x|X|/|÷)\s*(\d+)\s*$")
_WHOLE_NUMBER = re.compile(r"^\s*(\d+)\s*$")


def parse_identify_conversion_factor(text: str) -> dict[str, Any]:
    match = _CONVERSION_FACTOR.match(text)
    if not match:
        raise ValueError(f"'{text}' is not of the form 'x<factor>' or '/<factor>', e.g. 'x1000'")
    raw_direction, factor = match.groups()
    direction = "x" if raw_direction.lower() == "x" else "/"
    return {"direction": direction, "factor": int(factor)}


def parse_convert_units(text: str) -> dict[str, Any]:
    match = _WHOLE_NUMBER.match(text)
    if not match:
        raise ValueError(f"'{text}' is not a whole number")
    return {"value": int(match.group(1))}


_PARSERS = {
    "identify_conversion_factor": parse_identify_conversion_factor,
    "convert_units": parse_convert_units,
    "write_final_answer": parse_convert_units,
}


def parse_student_text(step_type: str, text: str) -> dict[str, Any]:
    """Raises `ValueError` (caught by the verifier, reported as
    `ErrorSignal(kind="malformed")`) if `text` doesn't match `step_type`'s
    grammar. Caller must confirm `step_type in _PARSERS` first."""
    return _PARSERS[step_type](text.strip())
