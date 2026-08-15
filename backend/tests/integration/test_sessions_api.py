"""Full pipeline round-trip via HTTP: session creation, then a wrong step
(verdict -> classification -> a gated dialogue message, streamed via SSE)
followed by a correct retry (resolution). Assumes the DB is already
migrated + seeded (matches CI's `test` job order). Skips gracefully
without a local Postgres, same as every other integration test.
"""

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from studyhelp.main import app


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Depends on `db_session` purely to inherit its Postgres-reachability
    skip check, same pattern as tests/integration/test_api.py."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _parse_sse(raw_text: str) -> list[tuple[str, str]]:
    """Returns a list of (event_name, raw_json_data) pairs, in order."""
    events = []
    for block in raw_text.strip().split("\n\n"):
        if not block.strip():
            continue
        lines = block.splitlines()
        event_name = next(
            line.removeprefix("event: ") for line in lines if line.startswith("event: ")
        )
        data = next(line.removeprefix("data: ") for line in lines if line.startswith("data: "))
        events.append((event_name, data))
    return events


async def test_create_session_returns_ids(client: AsyncClient) -> None:
    response = await client.post("/sessions", json={"display_name": "dev-tester"})
    assert response.status_code == 200
    body = response.json()
    assert "session_id" in body
    assert "user_id" in body


async def test_full_wrong_then_correct_step_round_trip(client: AsyncClient) -> None:
    created = await client.post("/sessions", json={"display_name": "dev-tester"})
    session_id = created.json()["session_id"]

    wrong_response = await client.post(
        f"/sessions/{session_id}/steps",
        json={
            "problem_id": "subtraction-borrow-001",
            "accepted_step_ids": ["s1_cmp_units", "s2_borrow_units"],
            "student_step": {
                "step_type": "free_text_step",
                "fields": {"text": "units 12 - 5 = 3"},
            },
            "timing_policy": "immediate",
        },
    )
    assert wrong_response.status_code == 200
    events = _parse_sse(wrong_response.text)
    event_names = [name for name, _ in events]
    assert "verdict" in event_names
    assert "classification" in event_names
    assert "turn_complete" in event_names

    import json

    verdict_data = json.loads(dict(events)["verdict"])
    assert verdict_data["is_valid"] is False

    turn_complete_data = json.loads(next(data for name, data in events if name == "turn_complete"))
    assert turn_complete_data["dialogue_event"] == "explaining"
    assert turn_complete_data["message"] is not None
    assert turn_complete_data["expects_retry"] is True

    correct_response = await client.post(
        f"/sessions/{session_id}/steps",
        json={
            "problem_id": "subtraction-borrow-001",
            "accepted_step_ids": ["s1_cmp_units", "s2_borrow_units"],
            "student_step": {
                "step_type": "free_text_step",
                "fields": {"text": "units 12 - 5 = 7"},
            },
            "timing_policy": "immediate",
        },
    )
    assert correct_response.status_code == 200
    correct_events = _parse_sse(correct_response.text)
    correct_turn_complete = json.loads(
        next(data for name, data in correct_events if name == "turn_complete")
    )
    assert correct_turn_complete["dialogue_event"] == "resolved"


async def test_correct_step_with_no_prior_error_is_a_no_op(client: AsyncClient) -> None:
    created = await client.post("/sessions", json={"display_name": "dev-tester"})
    session_id = created.json()["session_id"]

    response = await client.post(
        f"/sessions/{session_id}/steps",
        json={
            "problem_id": "subtraction-borrow-001",
            "accepted_step_ids": [],
            "student_step": {"step_type": "free_text_step", "fields": {"text": "units 2 < 5"}},
        },
    )
    assert response.status_code == 200
    events = _parse_sse(response.text)

    import json

    turn_complete_data = json.loads(next(data for name, data in events if name == "turn_complete"))
    assert turn_complete_data["dialogue_event"] == "no_action"
