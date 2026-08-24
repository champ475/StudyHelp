"""Resolves which distinct sub-concept a step belongs to, for the handful of
topics whose chapter genuinely covers more than one arithmetic operation
(CLAUDE.md live-testing Bug D).

`step_type` alone disambiguates most of these (`compute_area` vs.
`compute_perimeter`, `multiply_units` vs. `divide_tens`), but a shared
terminal step type (`write_final_answer`) doesn't carry that distinction, so
this falls back to the problem's own `given` dict — visible input, not a
protected answer value, so safe to consult here the same way the frontend
already shows it to the student.

Used for two purposes downstream: selecting the right (topic, step_family)
analogy-library entry instead of one conflated per-topic entry
(`llm/analogies.py`), and as an explicit grounding hint threaded into the
decide/generate prompts (`llm/prompts.py`) so the model names the actual
operation this step performs instead of drifting to generic phrasing.

Returns `None` for any topic that doesn't mix distinct operations — the
caller treats that as "no disambiguation needed," not an error.
"""

from typing import Any

_STEP_FAMILY_LABELS: dict[tuple[str, str], str] = {
    ("area_perimeter", "area"): "finding area (multiplying length by width)",
    ("area_perimeter", "perimeter"): "finding perimeter (adding up all the side lengths)",
    ("multiplication_division", "multiply"): "multiplying",
    ("multiplication_division", "divide"): "dividing",
    ("lcm_hcf", "lcm"): "finding the LCM (the lowest common multiple)",
    ("lcm_hcf", "hcf"): "finding the HCF (the highest common factor)",
}


def resolve_step_family(topic: str, step_type: str, given: dict[str, Any]) -> str | None:
    if topic == "area_perimeter":
        if step_type == "compute_area":
            return "area"
        if step_type == "compute_perimeter":
            return "perimeter"
        measure = given.get("measure")
        return measure if measure in ("area", "perimeter") else None

    if topic == "multiplication_division":
        if step_type.startswith("multiply"):
            return "multiply"
        if step_type.startswith("divide"):
            return "divide"
        op = given.get("op")
        if op == "x":
            return "multiply"
        if op == "/":
            return "divide"
        return None

    if topic == "lcm_hcf":
        op = given.get("op")
        return op if op in ("lcm", "hcf") else None

    return None


def step_family_label(topic: str, step_family: str | None) -> str | None:
    """A short, human-readable phrase naming the exact operation this step
    performs, for prompt grounding — `None` when `step_family` is `None`
    (topic doesn't mix operations, or the family couldn't be resolved)."""
    if step_family is None:
        return None
    return _STEP_FAMILY_LABELS.get((topic, step_family))
