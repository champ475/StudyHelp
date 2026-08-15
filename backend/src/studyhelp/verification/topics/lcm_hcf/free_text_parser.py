"""Deterministic free-text parser for LCM/HCF step submissions
(ARCHITECTURE.md D41/D43) — one small regex grammar per step type, never a
general expression evaluator, never handed to the LLM. Anything outside
the grammar raises `ValueError`, reported as `ErrorSignal(kind="malformed")`.

Grammar per step type:
- find_common_values:  comma-separated integers, e.g. "1,2,3,6" — parsed
                        and returned SORTED ascending regardless of the
                        order typed, so `compare_to_expected`'s plain `==`
                        stays robust without needing list-order-independent
                        comparison logic elsewhere.
- write_final_answer:  a bare integer, e.g. "12".
"""

from __future__ import annotations

import re
from typing import Any

_VALUES_LIST = re.compile(r"^\s*\d+(?:\s*,\s*\d+)*\s*$")
_WHOLE_NUMBER = re.compile(r"^\s*(\d+)\s*$")


def parse_find_common_values(text: str) -> dict[str, Any]:
    if not _VALUES_LIST.match(text):
        raise ValueError(f"'{text}' is not a comma-separated list of numbers, e.g. '1,2,3,6'")
    values = sorted(int(part) for part in text.split(","))
    return {"values": values}


def parse_write_final_answer(text: str) -> dict[str, Any]:
    match = _WHOLE_NUMBER.match(text)
    if not match:
        raise ValueError(f"'{text}' is not a whole number")
    return {"value": int(match.group(1))}


_PARSERS = {
    "find_common_values": parse_find_common_values,
    "write_final_answer": parse_write_final_answer,
}


def parse_student_text(step_type: str, text: str) -> dict[str, Any]:
    """Raises `ValueError` (caught by the verifier, reported as
    `ErrorSignal(kind="malformed")`) if `text` doesn't match `step_type`'s
    grammar. Caller must confirm `step_type in _PARSERS` first."""
    return _PARSERS[step_type](text.strip())
