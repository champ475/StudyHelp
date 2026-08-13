"""Round-trips a step through the real HTTP surface: DB-load -> verify_step()
-> events rows, with zero LLM involvement anywhere in the path. Assumes the
DB has already been migrated + seeded (CI's `test` job does this before
running integration tests; see .github/workflows/ci.yml). Skips gracefully
if Postgres isn't reachable, same as the other integration tests."""

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from studyhelp.main import app


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Depends on `db_session` purely to inherit its Postgres-reachability
    skip check — the route under test uses its own session via FastAPI's
    dependency injection, not this fixture's session directly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_verify_step_end_to_end_via_api_correct_step(client: AsyncClient) -> None:
    response = await client.post(
        "/problems/subtraction-borrow-001/verify-step",
        json={
            "accepted_step_ids": [],
            "student_step": {
                "step_type": "compare_column",
                "fields": {
                    "column": "units",
                    "minuend_digit": 2,
                    "subtrahend_digit": 5,
                    "borrow_needed": True,
                },
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is True
    assert body["matched_step_id"] == "s1_cmp_units"
    assert body["confidence"] == 1.0


async def test_verify_step_end_to_end_via_api_wrong_step(client: AsyncClient) -> None:
    response = await client.post(
        "/problems/subtraction-borrow-001/verify-step",
        json={
            "accepted_step_ids": ["s1_cmp_units", "s2_borrow_units"],
            "student_step": {
                "step_type": "subtract_column",
                "fields": {
                    "column": "units",
                    "minuend_digit": 12,
                    "subtrahend_digit": 5,
                    "result_digit": 3,
                },
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is False
    assert body["error_signal"]["kind"] == "field_mismatch"


async def test_verify_step_unknown_problem_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/problems/does-not-exist/verify-step",
        json={
            "accepted_step_ids": [],
            "student_step": {"step_type": "compare_column", "fields": {}},
        },
    )
    assert response.status_code == 404
