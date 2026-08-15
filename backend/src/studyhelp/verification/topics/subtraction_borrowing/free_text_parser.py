"""Deterministic free-text parser for subtraction-with-borrowing step
submissions — this topic's port off tap-widget input onto the same
free-text pattern `fractions_addition/free_text_parser.py` established
(ARCHITECTURE.md D41, completing D43's frontend conversion). Same rules
apply: a small regex grammar, one shape per step type, never a general
expression evaluator, never handed to the LLM. Anything outside the
grammar raises `ValueError`, reported as `ErrorSignal(kind="malformed")`.

Grammar per step type (a student types one of these per box):
- compare_column:      "<column> <top> < <bottom>"   or   "<column> <top> >= <bottom>"
                        e.g. "units 2 < 7" (borrow needed), "tens 9 >= 5" (no borrow)
- borrow:               "<from_column> <before>->{after}, <to_column> <before>->{after}"
                        optionally ", result <digit>" for a combined borrow+subtract
                        alt-path action, e.g. "tens 4->3, units 2->12, result 5"
- subtract_column:      "<column> <top> - <bottom> = <result>"   e.g. "units 12 - 7 = 5"
- write_final_answer:   the plain final number, e.g. "355" — decomposed into a
                        per-column `digits` dict by place value (matching the
                        no-leading-zero-columns convention every seeded fixture uses).
"""

from __future__ import annotations

import re
from typing import Any

_COLUMNS = {"units", "tens", "hundreds", "thousands", "ten_thousands", "lakhs"}
_PLACE_ORDER = ["units", "tens", "hundreds", "thousands", "ten_thousands", "lakhs"]

_COMPARE = re.compile(r"^\s*(\w+)\s+(\d+)\s*(<|>=)\s*(\d+)\s*$")
_BORROW = re.compile(
    r"^\s*(\w+)\s+(\d+)\s*->\s*(\d+)\s*,\s*(\w+)\s+(\d+)\s*->\s*(\d+)"
    r"(?:\s*,\s*result\s+(\d+))?\s*$",
    re.IGNORECASE,
)
_SUBTRACT = re.compile(r"^\s*(\w+)\s+(\d+)\s*-\s*(\d+)\s*=\s*(\d+)\s*$")
_WHOLE_NUMBER = re.compile(r"^\s*(\d+)\s*$")


def _column(raw: str, text: str) -> str:
    column = raw.strip().lower()
    if column not in _COLUMNS:
        raise ValueError(f"'{text}': '{raw}' is not a known column ({', '.join(sorted(_COLUMNS))})")
    return column


def parse_compare_column(text: str) -> dict[str, Any]:
    match = _COMPARE.match(text)
    if not match:
        raise ValueError(f"'{text}' is not of the form '<column> <top> < <bottom>' or '>= '")
    column_raw, top, op, bottom = match.groups()
    return {
        "column": _column(column_raw, text),
        "minuend_digit": int(top),
        "subtrahend_digit": int(bottom),
        "borrow_needed": op == "<",
    }


def parse_borrow(text: str) -> dict[str, Any]:
    match = _BORROW.match(text)
    if not match:
        raise ValueError(
            f"'{text}' is not of the form "
            "'<from_column> <before>->{{after}}, <to_column> <before>->{{after}}'"
        )
    from_col, from_before, from_after, to_col, to_before, to_after, result = match.groups()
    fields: dict[str, Any] = {
        "from_column": _column(from_col, text),
        "from_digit_before": int(from_before),
        "from_digit_after": int(from_after),
        "to_column": _column(to_col, text),
        "to_digit_before": int(to_before),
        "to_digit_after": int(to_after),
    }
    if result is not None:
        fields["combined_result_digit"] = int(result)
    return fields


def parse_subtract_column(text: str) -> dict[str, Any]:
    match = _SUBTRACT.match(text)
    if not match:
        raise ValueError(f"'{text}' is not of the form '<column> <top> - <bottom> = <result>'")
    column_raw, top, bottom, result = match.groups()
    return {
        "column": _column(column_raw, text),
        "minuend_digit": int(top),
        "subtrahend_digit": int(bottom),
        "result_digit": int(result),
    }


def parse_write_final_answer(text: str) -> dict[str, Any]:
    match = _WHOLE_NUMBER.match(text)
    if not match:
        raise ValueError(f"'{text}' is not a whole number")
    value = int(match.group(1))
    digit_str = str(value)
    digits: dict[str, int] = {}
    for position, digit_char in enumerate(reversed(digit_str)):
        if position >= len(_PLACE_ORDER):
            raise ValueError(f"'{text}': value has more digits than this topic supports")
        digits[_PLACE_ORDER[position]] = int(digit_char)
    return {"digits": digits, "value": value}


_PARSERS = {
    "compare_column": parse_compare_column,
    "borrow": parse_borrow,
    "subtract_column": parse_subtract_column,
    "write_final_answer": parse_write_final_answer,
}


def parse_student_text(step_type: str, text: str) -> dict[str, Any]:
    """Raises `ValueError` (caught by the verifier, reported as
    `ErrorSignal(kind="malformed")`) if `text` doesn't match `step_type`'s
    grammar. Caller must confirm `step_type in _PARSERS` first."""
    return _PARSERS[step_type](text.strip())


def render_student_text(step_type: str, fields: dict[str, Any]) -> str:
    """Inverse of `parse_student_text` — not used by the verifier itself
    (which only ever parses real student input), but shared by test/tooling
    code (`scripts/build_golden_cases.py`,
    `tests/unit/verification/test_problem_fixtures_walkthrough.py`) that
    needs to turn a fixture's structured `expected_state` into the free
    text a student would actually type to produce it, so those tests keep
    exercising the real input path rather than a bypassed structured one."""
    if step_type == "compare_column":
        op = "<" if fields["borrow_needed"] else ">="
        return f"{fields['column']} {fields['minuend_digit']} {op} {fields['subtrahend_digit']}"
    if step_type == "borrow":
        text = (
            f"{fields['from_column']} {fields['from_digit_before']}->{fields['from_digit_after']}, "
            f"{fields['to_column']} {fields['to_digit_before']}->{fields['to_digit_after']}"
        )
        result = fields.get("combined_result_digit")
        if result is not None:
            text += f", result {result}"
        return text
    if step_type == "subtract_column":
        return (
            f"{fields['column']} {fields['minuend_digit']} - {fields['subtrahend_digit']} "
            f"= {fields['result_digit']}"
        )
    if step_type == "write_final_answer":
        return str(fields["value"])
    raise ValueError(f"no free-text renderer for step_type '{step_type}'")
