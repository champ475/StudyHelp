"""LoggingLLMClient wrapping + the build_llm_client() factory's guardrails.
GroqLLMProvider is only smoke-tested for construction here — no network
call is made anywhere in this test file (no key exists yet, D17)."""

import pytest

from studyhelp.llm.client import (
    ClassifyCandidate,
    ClassifyRequest,
    LoggingLLMClient,
    build_llm_client,
)
from studyhelp.llm.providers.mock import MockLLMProvider


async def test_logging_client_passes_through_classify_response() -> None:
    client = LoggingLLMClient(MockLLMProvider(), provider_name="mock")
    response = await client.classify(
        ClassifyRequest(
            topic="t",
            step_type="s",
            correct_step={},
            student_step={},
            candidates=[ClassifyCandidate(misconception_id="a", typical_mindset="m")],
        )
    )
    assert response.misconception_id == "a"


def test_build_llm_client_defaults_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    from studyhelp import config

    # Explicit `setenv("mock", ...)`, not `delenv` — see conftest.py's
    # `_force_mock_llm_provider` docstring: a bare `delenv` would fall back
    # to whatever `backend/.env` has, not the field's true default.
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    config.get_settings.cache_clear()
    client = build_llm_client()
    assert isinstance(client, LoggingLLMClient)
    config.get_settings.cache_clear()


def test_build_llm_client_refuses_groq_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from studyhelp import config

    # `setenv("", ...)`, not `delenv` — see conftest.py's
    # `_force_mock_llm_provider` docstring: pydantic-settings falls back to
    # `backend/.env` for any var absent from the process environment, so a
    # real local key there would defeat a bare `delenv`.
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("GROQ_MODEL", "")
    config.get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="GROQ_API_KEY and GROQ_MODEL"):
            build_llm_client()
    finally:
        config.get_settings.cache_clear()


def test_groq_provider_constructs_without_network_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """Confirms the SDK client can be instantiated (import + constructor
    path work) — no request is sent, no key is required to be real."""
    from studyhelp.llm.providers.groq import GroqLLMProvider

    provider = GroqLLMProvider(api_key="not-a-real-key", model="not-a-real-model")
    assert provider is not None
