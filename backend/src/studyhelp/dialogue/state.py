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

    def _topic_weakness_key(self, session_id: str, topic: str, misconception_key: str) -> str:
        return f"weak_concept:{session_id}:{topic}:{misconception_key}"

    async def increment_topic_weakness(
        self, session_id: str, topic: str, misconception_key: str
    ) -> int:
        """Session-scoped count of how many times this session has now
        been classified with this exact (topic, misconception) pairing —
        broader than `consecutive_errors_on_this_step` (same *step* only):
        this accumulates across different problems and different steps
        within the same weak concept, so a student who is generally shaky
        on a concept (not just stuck on one specific step) still reaches
        the register-switch-to-analogy threshold (`dialogue/orchestrator.py`
        `TOPIC_REGISTER_SWITCH_THRESHOLD`, open-ended review finding #2).

        An ephemeral orchestration signal, not a durable record: never
        explicitly reset (only expires via the same TTL as every other key
        here), and recomputable from the Postgres event log's
        classification events if ever lost — Redis stays active-cache-only
        (ARCHITECTURE.md); Postgres remains the source of truth."""
        key = self._topic_weakness_key(session_id, topic, misconception_key)
        count = await self._redis.incr(key)
        await self._redis.expire(key, self._ttl_seconds)
        return int(count)
