"""Semi-automated novel-error review-queue clustering (ARCHITECTURE.md D5,
Feldman et al. 2018, CHI): groups structurally similar novel errors —
same `(topic, step_type, discrepant-field signature)` — before a human
reviewer looks at the queue, so a reviewer confirms "this cluster of N
similar errors is a new bug" once rather than triaging near-duplicates one
at a time. No ML needed at this scale — a stable string key is enough to
group by.

Promoting a confirmed cluster into `buggy_rule_library`/`misconception_bank`
is real-pilot-data scope (Phase 6) and isn't built here; this module only
does the grouping.
"""

import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from studyhelp.db.models import NovelError


def cluster_signature(topic: str, step_type: str, discrepant_fields: list[str]) -> str:
    fields_key = "-".join(sorted(discrepant_fields)) or "none"
    raw = f"{topic}:{step_type}:{fields_key}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:12]
    return f"{topic}.{step_type}.{fields_key}.{digest}"


async def cluster_pending_novel_errors(session: AsyncSession) -> int:
    """Assigns `cluster_id` to every not-yet-clustered `NovelError` row.
    Idempotent and safe to re-run — already-clustered rows are untouched,
    and the signature is a pure function of stable fields, so re-running
    never changes an existing row's cluster assignment. Returns the number
    of rows newly clustered."""
    stmt = select(NovelError).where(NovelError.cluster_id.is_(None))
    rows = (await session.execute(stmt)).scalars().all()
    for row in rows:
        row.cluster_id = cluster_signature(row.topic, row.step_type, row.discrepant_fields)
    await session.flush()
    return len(rows)
