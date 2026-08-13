"""fakeredis backs these tests — a real Redis server isn't available in
this sandbox, but the DialogueStateStore's actual logic (not just a mock
of it) is exercised end-to-end against a real Redis-protocol-compatible
in-memory implementation."""

import fakeredis
import pytest

from studyhelp.dialogue.state import (
    ConversationTurn,
    DialogueState,
    DialogueStateName,
    DialogueStateStore,
)


@pytest.fixture
def store() -> DialogueStateStore:
    return DialogueStateStore(fakeredis.FakeAsyncRedis(decode_responses=True))


async def test_get_returns_none_when_absent(store: DialogueStateStore) -> None:
    assert await store.get("session-1", "problem-1") is None


async def test_save_and_get_round_trips(store: DialogueStateStore) -> None:
    state = DialogueState(
        session_id="session-1",
        problem_id="problem-1",
        state=DialogueStateName.AWAITING_RETRY,
        turn_count=1,
        nearest_matched_step_id="s1",
        conversation=[ConversationTurn(role="tutor", text="hi")],
    )
    await store.save(state)
    loaded = await store.get("session-1", "problem-1")
    assert loaded is not None
    assert loaded.turn_count == 1
    assert loaded.nearest_matched_step_id == "s1"
    assert loaded.conversation[0].text == "hi"


async def test_delete_clears_state(store: DialogueStateStore) -> None:
    state = DialogueState(session_id="s", problem_id="p", state=DialogueStateName.AWAITING_RETRY)
    await store.save(state)
    await store.delete("s", "p")
    assert await store.get("s", "p") is None


async def test_different_problems_are_isolated(store: DialogueStateStore) -> None:
    await store.save(
        DialogueState(
            session_id="s", problem_id="p1", state=DialogueStateName.AWAITING_RETRY, turn_count=1
        )
    )
    await store.save(
        DialogueState(
            session_id="s", problem_id="p2", state=DialogueStateName.AWAITING_RETRY, turn_count=2
        )
    )
    a = await store.get("s", "p1")
    b = await store.get("s", "p2")
    assert a is not None
    assert a.turn_count == 1
    assert b is not None
    assert b.turn_count == 2


async def test_different_sessions_are_isolated(store: DialogueStateStore) -> None:
    await store.save(
        DialogueState(
            session_id="s1", problem_id="p", state=DialogueStateName.AWAITING_RETRY, turn_count=1
        )
    )
    assert await store.get("s2", "p") is None
