"""CLI: seed the database from the fixtures under
src/studyhelp/seed/fixtures/. Safe to re-run — the loader upserts by
natural key rather than inserting duplicates.

Usage: python scripts/seed_db.py
"""

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker

from studyhelp.db.base import make_engine
from studyhelp.seed.loader import seed_all


async def main() -> None:
    engine = make_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await seed_all(session)
        await session.commit()
    await engine.dispose()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
