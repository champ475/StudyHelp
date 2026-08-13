"""Async SQLAlchemy engine/session. Postgres is the durable source of truth
for everything except active per-step dialogue state, which lives in Redis
(ARCHITECTURE.md — Postgres/Redis split, CLAUDE.md)."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from studyhelp.config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str | None = None) -> AsyncEngine:
    return create_async_engine(database_url or get_settings().database_url, echo=False)


_engine = make_engine()
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with _session_factory() as session:
        yield session
