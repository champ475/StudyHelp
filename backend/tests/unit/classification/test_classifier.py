"""The rule-match path never touches the DB or the LLM client — testable
without either. The LLM-fallback path (candidate retrieval, closed-set
validation, novel-error logging) needs a real DB and is covered in
tests/integration/test_classifier.py."""

from studyhelp.classification.classifier import classify_error
from studyhelp.llm.providers.mock import MockLLMProvider


async def test_rule_match_short_circuits_before_touching_db_or_llm() -> None:
    correct = {"column": "units", "minuend_digit": 12, "subtrahend_digit": 5, "result_digit": 7}
    student = {"column": "units", "minuend_digit": 2, "subtrahend_digit": 5, "result_digit": 3}

    result = await classify_error(
        session=None,  # type: ignore[arg-type]  # unused on the rule-match path
        llm_client=MockLLMProvider(),
        topic="subtraction_with_borrowing",
        step_type="subtract_column",
        correct_fields=correct,
        student_fields=student,
        discrepant_fields=["minuend_digit", "result_digit"],
    )
    assert result.source == "rule"
    assert result.confidence == "high"
    assert result.bug_code == "B1-smaller-from-larger"
