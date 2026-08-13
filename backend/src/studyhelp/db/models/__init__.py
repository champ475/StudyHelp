"""Import every model so `Base.metadata` is fully populated for Alembic."""

from studyhelp.db.models.buggy_rule import BuggyRuleEntry
from studyhelp.db.models.event import Event
from studyhelp.db.models.misconception import MisconceptionBankEntry, ReviewStatus
from studyhelp.db.models.problem import ProblemModel
from studyhelp.db.models.session import ExperimentCondition, SessionModel
from studyhelp.db.models.step_type import StepType
from studyhelp.db.models.user import User, UserRole

__all__ = [
    "BuggyRuleEntry",
    "Event",
    "ExperimentCondition",
    "MisconceptionBankEntry",
    "ProblemModel",
    "ReviewStatus",
    "SessionModel",
    "StepType",
    "User",
    "UserRole",
]
