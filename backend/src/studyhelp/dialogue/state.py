"""Per-(session, problem) dialogue state, held in Redis — the durable
event log (Postgres `events` table) remains the source of truth for what
happened; this is only the *active* working state a mid-dialogue turn
needs (ARCHITECTURE.md: Redis is active per-step cache only).

State machine (technical_architecture.md §6):
`ErrorDetected -> Explaining -> AwaitingRetry -> [Resolved | Explaining(next turn) | Escalated]`.
`ErrorDetected`/`Explaining` are transient, in-request-only states while a
turn is being produced; only `AwaitingRetry` is ever persisted between
calls (`Resolved`/`Escalated` end the dialogue and clear the stored key).
"""

import enum
from typing import Literal

from pydantic import BaseModel, Field
from redis.asyncio import Redis


class DialogueStateName(enum.StrEnum):
    ERROR_DETECTED = "ErrorDetected"
    EXPLAINING = "Explaining"
    AWAITING_RETRY = "AwaitingRetry"
    RESOLVED = "Resolved"
    ESCALATED = "Escalated"


class ConversationTurn(BaseModel):
    role: Literal["tutor", "student"]
    text: str


class DialogueState(BaseModel):
    session_id: str
    problem_id: str
    state: DialogueStateName
    turn_count: int = 0
    consecutive_errors_on_this_step: int = 1
    nearest_matched_step_id: str | None = None
    misconception_id: str | None = None
    bug_code: str | None = None
    conversation: list[ConversationTurn] = Field(default_factory=list)


class DialogueStateStore:
    """A dialogue key is scoped to (session, problem) — a session can only
    have one unresolved error-dialogue in progress per problem at a time,
    matching the state machine's single active thread."""

    def __init__(self, redis: Redis, *, ttl_seconds: int = 7200) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    def _key(self, session_id: str, problem_id: str) -> str:
        return f"dialogue:{session_id}:{problem_id}"

    async def get(self, session_id: str, problem_id: str) -> DialogueState | None:
        raw = await self._redis.get(self._key(session_id, problem_id))
        if raw is None:
            return None
        return DialogueState.model_validate_json(raw)

    async def save(self, state: DialogueState) -> None:
        key = self._key(state.session_id, state.problem_id)
        await self._redis.set(key, state.model_dump_json(), ex=self._ttl_seconds)

    async def delete(self, session_id: str, problem_id: str) -> None:
        await self._redis.delete(self._key(session_id, problem_id))
