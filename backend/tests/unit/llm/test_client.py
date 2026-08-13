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

    config.get_settings.cache_clear()
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    client = build_llm_client()
    assert isinstance(client, LoggingLLMClient)
    config.get_settings.cache_clear()


def test_build_llm_client_refuses_groq_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from studyhelp import config

    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)
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
