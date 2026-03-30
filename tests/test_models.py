"""Tests for LLM model providers."""

from __future__ import annotations

import pytest

from vericode.exceptions import ModelConfigError
from vericode.models import get_provider
from vericode.models.anthropic_provider import AnthropicProvider
from vericode.models.deepseek import DeepSeekProvider
from vericode.models.openai_provider import OpenAIProvider

# ---------------------------------------------------------------------------
# Provider registry tests
# ---------------------------------------------------------------------------


class TestGetProvider:
    """Tests for the ``get_provider`` factory function."""

    def test_anthropic_with_key(self) -> None:
        provider = get_provider("anthropic", api_key="test-key")
        assert isinstance(provider, AnthropicProvider)
        assert provider.provider_name == "anthropic"

    def test_openai_with_key(self) -> None:
        provider = get_provider("openai", api_key="test-key")
        assert isinstance(provider, OpenAIProvider)
        assert provider.provider_name == "openai"

    def test_deepseek_with_key(self) -> None:
        provider = get_provider("deepseek", api_key="test-key")
        assert isinstance(provider, DeepSeekProvider)
        assert provider.provider_name == "deepseek"

    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_provider("llama")


# ---------------------------------------------------------------------------
# Provider construction tests
# ---------------------------------------------------------------------------


class TestAnthropicProvider:
    def test_requires_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ModelConfigError, match="anthropic"):
            AnthropicProvider()

    def test_accepts_explicit_key(self) -> None:
        provider = AnthropicProvider(api_key="sk-test")
        assert provider.provider_name == "anthropic"

    def test_reads_env_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env-test")
        provider = AnthropicProvider()
        assert provider.provider_name == "anthropic"


class TestOpenAIProvider:
    def test_requires_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ModelConfigError, match="openai"):
            OpenAIProvider()

    def test_accepts_explicit_key(self) -> None:
        provider = OpenAIProvider(api_key="sk-test")
        assert provider.provider_name == "openai"

    def test_reads_env_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-test")
        provider = OpenAIProvider()
        assert provider.provider_name == "openai"


class TestDeepSeekProvider:
    def test_requires_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        with pytest.raises(ModelConfigError, match="deepseek"):
            DeepSeekProvider()

    def test_accepts_explicit_key(self) -> None:
        provider = DeepSeekProvider(api_key="sk-test")
        assert provider.provider_name == "deepseek"

    def test_reads_env_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-test")
        provider = DeepSeekProvider()
        assert provider.provider_name == "deepseek"
