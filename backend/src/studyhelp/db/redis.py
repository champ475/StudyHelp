"""Redis: active per-step dialogue-state cache ONLY. Postgres remains the
durable source of truth for everything else (CLAUDE.md; ARCHITECTURE.md
Postgres/Redis split)."""

from redis.asyncio import Redis

from studyhelp.config import get_settings


def make_redis_client(redis_url: str | None = None) -> Redis:
    return Redis.from_url(redis_url or get_settings().redis_url, decode_responses=True)


_redis_client = make_redis_client()


def get_redis() -> Redis:
    return _redis_client
