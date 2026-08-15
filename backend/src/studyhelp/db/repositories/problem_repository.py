"""Thin data-access layer: DB row <-> domain schema mapping. Application
code (routes, orchestrator) talks to `schemas.step_schema.Problem`, never
to the ORM row directly — keeps the DB representation free to evolve
without leaking into pipeline code."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from studyhelp.db.models import ProblemModel
from studyhelp.schemas.step_schema import AltPath, NcertRef, Problem, StepNode


class ProblemSummary:
    """One row of the GET /problems catalog -- just enough for a chapter ->
    problem picker UI, never the step graph or answer data (that stays
    behind GET /problems/{id}'s already-sanitized PublicProblem)."""

    def __init__(self, problem_id: str, ncert_ref: NcertRef, display_label: str) -> None:
        self.problem_id = problem_id
        self.ncert_ref = ncert_ref
        self.display_label = display_label


async def list_problems(session: AsyncSession) -> list[ProblemSummary]:
    """Ordered by chapter then problem_id so the catalog endpoint doesn't
    need to re-sort -- cheap column-only query, no step_graph JSONB pulled
    for 140 rows."""
    stmt = select(
        ProblemModel.id,
        ProblemModel.ncert_class,
        ProblemModel.ncert_chapter,
        ProblemModel.ncert_chapter_title,
        ProblemModel.topic,
        ProblemModel.display_label,
    ).order_by(ProblemModel.ncert_chapter, ProblemModel.id)
    rows = (await session.execute(stmt)).all()
    return [
        ProblemSummary(
            problem_id=row.id,
            ncert_ref=NcertRef(
                ncert_class=row.ncert_class,
                chapter=row.ncert_chapter,
                chapter_title=row.ncert_chapter_title,
                topic=row.topic,
            ),
            display_label=row.display_label,
        )
        for row in rows
    ]


async def get_problem(session: AsyncSession, problem_id: str) -> Problem | None:
    row = await session.get(ProblemModel, problem_id)
    if row is None:
        return None
    return Problem(
        problem_id=row.id,
        ncert_ref=NcertRef(
            ncert_class=row.ncert_class,
            chapter=row.ncert_chapter,
            chapter_title=row.ncert_chapter_title,
            topic=row.topic,
        ),
        display_label=row.display_label,
        given=row.given,
        final_answer=row.final_answer,
        step_graph=[StepNode.model_validate(node) for node in row.step_graph],
        alt_paths=[AltPath.model_validate(path) for path in (row.alt_paths or [])],
    )
