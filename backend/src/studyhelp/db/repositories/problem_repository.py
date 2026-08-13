"""Thin data-access layer: DB row <-> domain schema mapping. Application
code (routes, orchestrator) talks to `schemas.step_schema.Problem`, never
to the ORM row directly — keeps the DB representation free to evolve
without leaking into pipeline code."""

from sqlalchemy.ext.asyncio import AsyncSession

from studyhelp.db.models import ProblemModel
from studyhelp.schemas.step_schema import AltPath, NcertRef, Problem, StepNode


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
        given=row.given,
        final_answer=row.final_answer,
        step_graph=[StepNode.model_validate(node) for node in row.step_graph],
        alt_paths=[AltPath.model_validate(path) for path in (row.alt_paths or [])],
    )
