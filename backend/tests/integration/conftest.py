"""Integration tests need a real Postgres (per CLAUDE.md — Postgres is the
source of truth, not mocked in these tests). CI provides one as a service
container. Local runs without Docker/Postgres available skip gracefully
rather than failing the whole suite."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from studyhelp.config import get_settings
from studyhelp.db.base import make_engine


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = make_engine(get_settings().database_url)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except (OperationalError, OSError) as exc:
        await engine.dispose()
        pytest.skip(f"Postgres not reachable for integration tests: {exc}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()
