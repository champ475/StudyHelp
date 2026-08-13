"""Error classification orchestrator: buggy-rule matcher first, closed-set
LLM fallback second (ARCHITECTURE.md D3, D4). The LLM never diagnoses
freely — candidates are retrieved from the misconception bank *before* the
call, and the LLM's answer is validated against that exact candidate set
in application code regardless of what the model claims (D3). An LLM
classification is never auto-trusted at the same tier as a rule match: it
always carries `confidence="low"`, and anything that isn't a clean
in-candidate-set pick is routed to the novel-error review queue rather
than promoted into the trusted taxonomy (D5).
"""

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from studyhelp.classification.rule_matcher import match_buggy_rule
from studyhelp.db.repositories.misconception_repository import get_candidates
from studyhelp.db.repositories.novel_error_repository import log_novel_error
from studyhelp.llm.client import ClassifyRequest, LLMClient
from studyhelp.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ClassificationResult:
    source: Literal["rule", "llm", "novel"]
    misconception_id: str | None
    bug_code: str | None
    confidence: Literal["high", "low"]
    rationale: str | None = None


async def classify_error(
    session: AsyncSession,
    llm_client: LLMClient,
    *,
    topic: str,
    step_type: str,
    correct_fields: dict[str, Any],
    student_fields: dict[str, Any],
    discrepant_fields: list[str],
    event_id: int | None = None,
) -> ClassificationResult:
    rule_match = match_buggy_rule(step_type, correct_fields, student_fields)
    if rule_match is not None:
        return ClassificationResult(
            source="rule",
            misconception_id=rule_match.buggy_rule_id,
            bug_code=rule_match.bug_code,
            confidence="high",
        )

    candidates = await get_candidates(session, topic=topic, step_type=step_type)
    response = await llm_client.classify(
        ClassifyRequest(
            topic=topic,
            step_type=step_type,
            correct_step=correct_fields,
            student_step=student_fields,
            candidates=candidates,
        )
    )

    candidate_ids = {c.misconception_id for c in candidates}
    misconception_id = response.misconception_id

    if misconception_id is not None and misconception_id not in candidate_ids:
        logger.warning(
            "llm_classification_closed_set_violation",
            returned_id=misconception_id,
            candidate_ids=sorted(candidate_ids),
        )
        misconception_id = None  # never trusted, regardless of what the model claimed

    if misconception_id is None:
        await log_novel_error(
            session,
            topic=topic,
            step_type=step_type,
            correct_step=correct_fields,
            student_step=student_fields,
            discrepant_fields=discrepant_fields,
            llm_rationale=response.rationale,
            event_id=event_id,
        )
        return ClassificationResult(
            source="novel",
            misconception_id=None,
            bug_code=None,
            confidence="low",
            rationale=response.rationale,
        )

    return ClassificationResult(
        source="llm",
        misconception_id=misconception_id,
        bug_code=None,
        confidence="low",
        rationale=response.rationale,
    )
