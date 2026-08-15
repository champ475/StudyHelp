import json
from pathlib import Path

import pytest

from studyhelp.schemas.step_schema import Problem


@pytest.fixture(autouse=True)
def _force_mock_llm_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests must be deterministic and must never make a real network call,
    regardless of what a developer's local `backend/.env` has `LLM_PROVIDER`
    set to (e.g. `groq`, once a real key is wired in for manual/E2E use).
    Forcing `mock` here — independent of `.env` — is what actually
    guarantees that, rather than relying on every developer's local file
    happening to say `mock`."""
    from studyhelp import config

    # `setenv("", ...)`, not `delenv` — pydantic-settings falls back to
    # reading `backend/.env` directly for any var absent from the actual
    # process environment, so deleting an OS env var alone does not hide a
    # real value a developer has put in `.env` for local Groq testing.
    # Setting an empty string wins over the .env fallback and still reads
    # as falsy (`settings.groq_api_key` empty-string-or-None checks both).
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("GROQ_MODEL", "")
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()

FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "src"
    / "studyhelp"
    / "seed"
    / "fixtures"
    / "problems"
    / "ch1_subtraction_borrowing"
    / "problem_014_542_187.json"
)


@pytest.fixture
def problem_542_187() -> Problem:
    data = json.loads(FIXTURE_PATH.read_text())
    return Problem.model_validate(data)


FRACTIONS_FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "src"
    / "studyhelp"
    / "seed"
    / "fixtures"
    / "problems"
    / "ch_fractions"
    / "problem_003_1_2_plus_1_6.json"
)


@pytest.fixture
def problem_1_2_plus_1_6() -> Problem:
    """1/2 + 1/6 = 2/3 — the one fraction fixture that requires a real
    simplification step, so it exercises the F3-forgot-to-simplify path."""
    data = json.loads(FRACTIONS_FIXTURE_PATH.read_text())
    return Problem.model_validate(data)
