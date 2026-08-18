"""Idempotent seed loader: reads pydantic-validated JSON fixtures and
upserts them into Postgres by natural key (`topic`+`step_type_key`, or a
stable slug `id`) — safe to re-run, never duplicates rows.

Note on topic-awareness: each topic's `validate_problem_arithmetic` is
specific to that topic's field names, so `_ARITHMETIC_VALIDATORS` below
dispatches on `problem.ncert_ref.topic` rather than hardcoding one import
(ARCHITECTURE.md D19 — sequence, don't front-load; this dict is what that
sequencing turned into once a second topic existed).
"""

import json
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from studyhelp.db.models import BuggyRuleEntry as BuggyRuleRow
from studyhelp.db.models import MisconceptionBankEntry as MisconceptionRow
from studyhelp.db.models import ProblemModel
from studyhelp.db.models import StepType as StepTypeRow
from studyhelp.schemas.buggy_rule import BuggyRuleEntry
from studyhelp.schemas.misconception import MisconceptionEntry
from studyhelp.schemas.step_schema import Problem, StepTypeEntry
from studyhelp.verification.topics._light_check.base import validate_light_check_problem
from studyhelp.verification.topics.area_perimeter.sympy_utils import (
    validate_problem_arithmetic as validate_area_perimeter_arithmetic,
)
from studyhelp.verification.topics.decimals.sympy_utils import (
    validate_problem_arithmetic as validate_decimals_arithmetic,
)
from studyhelp.verification.topics.fractions_addition.sympy_utils import (
    validate_problem_arithmetic as validate_fractions_addition_arithmetic,
)
from studyhelp.verification.topics.lcm_hcf.sympy_utils import (
    validate_problem_arithmetic as validate_lcm_hcf_arithmetic,
)
from studyhelp.verification.topics.measurement.sympy_utils import (
    validate_problem_arithmetic as validate_measurement_arithmetic,
)
from studyhelp.verification.topics.multiplication_division.sympy_utils import (
    validate_problem_arithmetic as validate_multiplication_division_arithmetic,
)
from studyhelp.verification.topics.subtraction_borrowing.sympy_utils import (
    validate_problem_arithmetic as validate_subtraction_borrowing_arithmetic,
)

FIXTURES_ROOT = Path(__file__).parent / "fixtures"

_ARITHMETIC_VALIDATORS = {
    "subtraction_with_borrowing": validate_subtraction_borrowing_arithmetic,
    "fractions_addition": validate_fractions_addition_arithmetic,
    "lcm_hcf": validate_lcm_hcf_arithmetic,
    "decimals": validate_decimals_arithmetic,
    "area_perimeter": validate_area_perimeter_arithmetic,
    "multiplication_division": validate_multiplication_division_arithmetic,
    "measurement": validate_measurement_arithmetic,
    "shapes_angles": validate_light_check_problem,
    "how_many_squares": validate_light_check_problem,
    "symmetry": validate_light_check_problem,
    "patterns": validate_light_check_problem,
    "mapping": validate_light_check_problem,
    "boxes_sketches": validate_light_check_problem,
    "smart_charts": validate_light_check_problem,
}
"""Per-topic seed-time structural/arithmetic cross-check hook (ARCHITECTURE.md
D19 — sequence, don't front-load: this became a dict the moment a second
topic existed, rather than staying the single hardcoded import it was for
one topic). The 7 light-check topics (D47) share one validator since they
share one verifier — there's no per-topic arithmetic identity to check,
only the shared 1-2-step/non-empty-answer structural shape."""


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_step_types() -> list[StepTypeEntry]:
    entries: list[StepTypeEntry] = []
    for path in sorted((FIXTURES_ROOT / "step_types").glob("*.json")):
        entries.extend(StepTypeEntry.model_validate(row) for row in _load_json(path))
    return entries


def load_problems() -> list[Problem]:
    problems: list[Problem] = []
    for path in sorted((FIXTURES_ROOT / "problems").rglob("*.json")):
        problem = Problem.model_validate(_load_json(path))
        validator = _ARITHMETIC_VALIDATORS.get(problem.ncert_ref.topic)
        if validator is not None:
            validator(problem)
        problems.append(problem)
    return problems


def load_misconceptions() -> list[MisconceptionEntry]:
    entries: list[MisconceptionEntry] = []
    for path in sorted((FIXTURES_ROOT / "misconception_bank").glob("*.json")):
        entries.extend(MisconceptionEntry.model_validate(row) for row in _load_json(path))
    return entries


def load_buggy_rules() -> list[BuggyRuleEntry]:
    entries: list[BuggyRuleEntry] = []
    for path in sorted((FIXTURES_ROOT / "buggy_rule_library").glob("*.json")):
        entries.extend(BuggyRuleEntry.model_validate(row) for row in _load_json(path))
    return entries


async def upsert_step_types(session: AsyncSession, entries: list[StepTypeEntry]) -> None:
    for entry in entries:
        stmt = pg_insert(StepTypeRow).values(
            topic=entry.topic,
            step_type_key=entry.step_type_key,
            description=entry.description,
            structured_input_schema=entry.structured_input_schema,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["topic", "step_type_key"],
            set_={
                "description": stmt.excluded.description,
                "structured_input_schema": stmt.excluded.structured_input_schema,
            },
        )
        await session.execute(stmt)


async def upsert_problems(session: AsyncSession, problems: list[Problem]) -> None:
    for problem in problems:
        stmt = pg_insert(ProblemModel).values(
            id=problem.problem_id,
            ncert_class=problem.ncert_ref.ncert_class,
            ncert_chapter=problem.ncert_ref.chapter,
            ncert_chapter_title=problem.ncert_ref.chapter_title,
            topic=problem.ncert_ref.topic,
            display_label=problem.display_label,
            given=problem.given,
            final_answer=problem.final_answer,
            step_graph=[node.model_dump(mode="json") for node in problem.step_graph],
            alt_paths=[p.model_dump(mode="json") for p in problem.alt_paths] or None,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "ncert_class": stmt.excluded.ncert_class,
                "ncert_chapter": stmt.excluded.ncert_chapter,
                "ncert_chapter_title": stmt.excluded.ncert_chapter_title,
                "topic": stmt.excluded.topic,
                "display_label": stmt.excluded.display_label,
                "given": stmt.excluded.given,
                "final_answer": stmt.excluded.final_answer,
                "step_graph": stmt.excluded.step_graph,
                "alt_paths": stmt.excluded.alt_paths,
            },
        )
        await session.execute(stmt)


async def upsert_misconceptions(session: AsyncSession, entries: list[MisconceptionEntry]) -> None:
    for entry in entries:
        stmt = pg_insert(MisconceptionRow).values(
            id=entry.id,
            topic=entry.topic,
            step_type=entry.step_type,
            bug_signature=entry.bug_signature,
            typical_mindset=entry.typical_mindset,
            explanation_strategy=entry.explanation_strategy,
            example_dialogue=[turn.model_dump() for turn in entry.example_dialogue],
            source=entry.source,
            version=entry.version,
            review_status=entry.review_status,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "bug_signature": stmt.excluded.bug_signature,
                "typical_mindset": stmt.excluded.typical_mindset,
                "explanation_strategy": stmt.excluded.explanation_strategy,
                "example_dialogue": stmt.excluded.example_dialogue,
                "source": stmt.excluded.source,
                "version": stmt.excluded.version,
                "review_status": stmt.excluded.review_status,
            },
        )
        await session.execute(stmt)


async def upsert_buggy_rules(session: AsyncSession, entries: list[BuggyRuleEntry]) -> None:
    for entry in entries:
        stmt = pg_insert(BuggyRuleRow).values(
            id=entry.id,
            topic=entry.topic,
            step_type=entry.step_type,
            bug_code=entry.bug_code,
            signature_matcher=entry.signature_matcher,
            citation=entry.citation,
            misconception_id=entry.misconception_id,
            example_pair=entry.example_pair.model_dump(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "bug_code": stmt.excluded.bug_code,
                "signature_matcher": stmt.excluded.signature_matcher,
                "citation": stmt.excluded.citation,
                "misconception_id": stmt.excluded.misconception_id,
                "example_pair": stmt.excluded.example_pair,
            },
        )
        await session.execute(stmt)


async def seed_all(session: AsyncSession) -> None:
    """Dependency order matters: step_types before misconception_bank/
    buggy_rule_library (composite FK), misconception_bank before
    buggy_rule_library (FK on misconception_id)."""
    await upsert_step_types(session, load_step_types())
    await upsert_problems(session, load_problems())
    await upsert_misconceptions(session, load_misconceptions())
    await upsert_buggy_rules(session, load_buggy_rules())
