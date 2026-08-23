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
            "student_step": {"step_type": "free_text_step", "fields": {"text": "units 2 < 5"}},
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
                "step_type": "free_text_step",
                "fields": {"text": "units 12 - 5 = 3"},
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
            "student_step": {"step_type": "free_text_step", "fields": {"text": "anything"}},
        },
    )
    assert response.status_code == 404


async def test_public_problem_endpoint_never_exposes_answers(client: AsyncClient) -> None:
    """The frontend fetches this from the browser — it must never contain
    expected_state values or the final answer, or a student could read
    every correct step straight out of devtools (undermining the leakage
    filter's whole purpose, D8)."""
    response = await client.get("/problems/subtraction-borrow-001")
    assert response.status_code == 200
    body = response.json()

    assert "final_answer" not in body
    assert body["problem_id"] == "subtraction-borrow-001"
    assert body["display_label"] == "52 − 25 (single borrow)"
    assert body["given"] == {"minuend": 52, "subtrahend": 25}

    for node in body["step_graph"]:
        assert set(node.keys()) == {"step_id", "type", "next", "hint"}
        assert "expected_state" not in node
        assert node["hint"]  # every step type has a seed-authored description

    raw_body = response.text
    assert "27" not in raw_body  # the final answer to 52-25, must never appear


async def test_public_problem_endpoint_redacts_given_fields_that_duplicate_a_step_answer(
    client: AsyncClient,
) -> None:
    """CLAUDE.md full-system-audit regression: `measurement-001`'s `given`
    dict includes `direction`/`factor`, which are ALSO the exact
    `expected_state` of the problem's first step (`identify_conversion_factor`)
    — before this fix, every measurement problem shipped the answer to its
    own first step in this endpoint's plain JSON on page load, no LLM or
    dialogue turn involved at all. `given.value` (the "3" in "3 km to m")
    must still come through — it's genuine, non-secret input, not a
    duplicate of any step's answer, even though it shares a key name with
    `write_final_answer`'s answer-bearing `value` field."""
    response = await client.get("/problems/measurement-001")
    assert response.status_code == 200
    body = response.json()

    assert body["given"] == {
        "value": 3,
        "from_unit": "km",
        "to_unit": "m",
        "category": "length",
    }
    assert "direction" not in body["given"]
    assert "factor" not in body["given"]

    raw_body = response.text
    assert "1000" not in raw_body  # the conversion factor, must never appear
    assert "3000" not in raw_body  # the final answer, must never appear


async def test_public_problem_endpoint_unknown_problem_returns_404(client: AsyncClient) -> None:
    response = await client.get("/problems/does-not-exist")
    assert response.status_code == 404
