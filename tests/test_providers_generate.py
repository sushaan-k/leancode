"""Tests for LLM provider generate() methods using mocked HTTP responses.

Covers the actual HTTP request/response logic of AnthropicProvider,
OpenAIProvider, and DeepSeekProvider including error handling paths.
"""

from __future__ import annotations

import httpx
import pytest
import respx
from httpx import Response

from vericode.exceptions import GenerationError, ModelConfigError
from vericode.models.anthropic_provider import AnthropicProvider
from vericode.models.deepseek import DeepSeekProvider
from vericode.models.openai_provider import OpenAIProvider

# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------


class TestAnthropicGenerate:
    """Tests for AnthropicProvider.generate()."""

    def _make_provider(self) -> AnthropicProvider:
        return AnthropicProvider(api_key="test-key-123")

    @respx.mock
    async def test_successful_generation(self) -> None:
        respx.post("https://api.anthropic.com/v1/messages").mock(
            return_value=Response(
                200,
                json={
                    "content": [
                        {
                            "text": (
                                "```python\ndef sort(lst): return sorted(lst)\n```\n\n"
                                "```lean4\ntheorem sort_correct := by sorry\n```"
                            )
                        }
                    ],
                    "model": "claude-sonnet-4-20250514",
                    "usage": {"input_tokens": 50, "output_tokens": 100},
                },
            )
        )
        provider = self._make_provider()
        resp = await provider.generate("sort a list", system_prompt="be helpful")
        assert "def sort" in resp.code
        assert "sort_correct" in resp.proof
        assert resp.model == "claude-sonnet-4-20250514"
        assert resp.prompt_tokens == 50
        assert resp.completion_tokens == 100

    @respx.mock
    async def test_api_error_raises_generation_error(self) -> None:
        respx.post("https://api.anthropic.com/v1/messages").mock(
            return_value=Response(429, json={"error": "rate limited"})
        )
        provider = self._make_provider()
        with pytest.raises(GenerationError, match="429"):
            await provider.generate("sort a list")

    @respx.mock
    async def test_network_error_raises_generation_error(self) -> None:
        respx.post("https://api.anthropic.com/v1/messages").mock(
            side_effect=httpx.ConnectError("connection reset")
        )
        provider = self._make_provider()
        with pytest.raises(GenerationError, match="request failed"):
            await provider.generate("sort a list")

    @respx.mock
    async def test_no_code_blocks_in_response(self) -> None:
        respx.post("https://api.anthropic.com/v1/messages").mock(
            return_value=Response(
                200,
                json={
                    "content": [{"text": "I cannot generate that, sorry."}],
                    "model": "claude-sonnet-4-20250514",
                    "usage": {"input_tokens": 10, "output_tokens": 20},
                },
            )
        )
        provider = self._make_provider()
        resp = await provider.generate("sort a list")
        assert resp.code == ""
        assert resp.proof == ""
        assert resp.raw_text == "I cannot generate that, sorry."

    @respx.mock
    async def test_malformed_response_shape_raises_generation_error(self) -> None:
        respx.post("https://api.anthropic.com/v1/messages").mock(
            return_value=Response(200, json={"content": []})
        )
        provider = self._make_provider()
        with pytest.raises(GenerationError, match="unexpected response shape"):
            await provider.generate("sort a list")

    @respx.mock
    async def test_generation_without_system_prompt(self) -> None:
        respx.post("https://api.anthropic.com/v1/messages").mock(
            return_value=Response(
                200,
                json={
                    "content": [{"text": "```python\ndef f(): pass\n```"}],
                    "model": "claude-sonnet-4-20250514",
                    "usage": {},
                },
            )
        )
        provider = self._make_provider()
        resp = await provider.generate("some prompt")
        assert resp.prompt_tokens == 0
        assert resp.completion_tokens == 0

    @respx.mock
    async def test_server_error_500(self) -> None:
        respx.post("https://api.anthropic.com/v1/messages").mock(
            return_value=Response(500, text="Internal server error")
        )
        provider = self._make_provider()
        with pytest.raises(GenerationError, match="500"):
            await provider.generate("test")

    def test_missing_api_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ModelConfigError, match="anthropic"):
            AnthropicProvider()

    def test_custom_model(self) -> None:
        provider = AnthropicProvider(api_key="key", model="claude-opus-4-20250514")
        assert provider.provider_name == "anthropic"


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------


class TestOpenAIGenerate:
    """Tests for OpenAIProvider.generate()."""

    def _make_provider(self) -> OpenAIProvider:
        return OpenAIProvider(api_key="test-key-123")

    @respx.mock
    async def test_successful_generation(self) -> None:
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    "```python\ndef sort(lst): return sorted(lst)\n```\n\n"
                                    "```dafny\nmethod Sort() ensures true {}\n```"
                                )
                            }
                        }
                    ],
                    "model": "gpt-4o",
                    "usage": {"prompt_tokens": 30, "completion_tokens": 60},
                },
            )
        )
        provider = self._make_provider()
        resp = await provider.generate("sort a list", system_prompt="you are a coder")
        assert "def sort" in resp.code
        assert "method Sort" in resp.proof
        assert resp.model == "gpt-4o"
        assert resp.prompt_tokens == 30
        assert resp.completion_tokens == 60

    @respx.mock
    async def test_api_error_raises_generation_error(self) -> None:
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=Response(401, json={"error": "invalid key"})
        )
        provider = self._make_provider()
        with pytest.raises(GenerationError, match="401"):
            await provider.generate("test")

    @respx.mock
    async def test_network_error_raises_generation_error(self) -> None:
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            side_effect=httpx.ConnectError("timeout")
        )
        provider = self._make_provider()
        with pytest.raises(GenerationError, match="request failed"):
            await provider.generate("test")

    @respx.mock
    async def test_no_system_prompt(self) -> None:
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=Response(
                200,
                json={
                    "choices": [{"message": {"content": "plain text"}}],
                    "model": "gpt-4o",
                    "usage": {},
                },
            )
        )
        provider = self._make_provider()
        resp = await provider.generate("test", system_prompt=None)
        assert resp.code == ""

    @respx.mock
    async def test_malformed_response_shape_raises_generation_error(self) -> None:
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=Response(200, json={"choices": [{"message": {}}]})
        )
        provider = self._make_provider()
        with pytest.raises(GenerationError, match="unexpected response shape"):
            await provider.generate("test")

    @respx.mock
    async def test_rate_limit_error(self) -> None:
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=Response(429, text="Rate limit exceeded")
        )
        provider = self._make_provider()
        with pytest.raises(GenerationError, match="429"):
            await provider.generate("test")


# ---------------------------------------------------------------------------
# DeepSeek provider
# ---------------------------------------------------------------------------


class TestDeepSeekGenerate:
    """Tests for DeepSeekProvider.generate()."""

    def _make_provider(self) -> DeepSeekProvider:
        return DeepSeekProvider(api_key="test-key-123")

    @respx.mock
    async def test_successful_generation(self) -> None:
        respx.post("https://api.deepseek.com/v1/chat/completions").mock(
            return_value=Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    "```python\ndef sort(lst): return sorted(lst)\n```\n\n"
                                    "```lean4\ntheorem sort_correct := by sorry\n```"
                                )
                            }
                        }
                    ],
                    "model": "deepseek-prover-v2",
                    "usage": {"prompt_tokens": 40, "completion_tokens": 80},
                },
            )
        )
        provider = self._make_provider()
        resp = await provider.generate("sort a list", system_prompt="prove it")
        assert "def sort" in resp.code
        assert "sort_correct" in resp.proof
        assert resp.model == "deepseek-prover-v2"
        assert resp.prompt_tokens == 40
        assert resp.completion_tokens == 80

    @respx.mock
    async def test_api_error_raises_generation_error(self) -> None:
        respx.post("https://api.deepseek.com/v1/chat/completions").mock(
            return_value=Response(503, text="Service unavailable")
        )
        provider = self._make_provider()
        with pytest.raises(GenerationError, match="503"):
            await provider.generate("test")

    @respx.mock
    async def test_network_error_raises_generation_error(self) -> None:
        respx.post("https://api.deepseek.com/v1/chat/completions").mock(
            side_effect=httpx.ConnectError("dns resolution failed")
        )
        provider = self._make_provider()
        with pytest.raises(GenerationError, match="request failed"):
            await provider.generate("test")

    @respx.mock
    async def test_no_system_prompt(self) -> None:
        respx.post("https://api.deepseek.com/v1/chat/completions").mock(
            return_value=Response(
                200,
                json={
                    "choices": [{"message": {"content": "no blocks"}}],
                    "model": "deepseek-prover-v2",
                    "usage": {},
                },
            )
        )
        provider = self._make_provider()
        resp = await provider.generate("test")
        assert resp.code == ""
        assert resp.proof == ""

    @respx.mock
    async def test_malformed_response_shape_raises_generation_error(self) -> None:
        respx.post("https://api.deepseek.com/v1/chat/completions").mock(
            return_value=Response(200, json={"choices": []})
        )
        provider = self._make_provider()
        with pytest.raises(GenerationError, match="unexpected response shape"):
            await provider.generate("test")

    @respx.mock
    async def test_custom_temperature_and_max_tokens(self) -> None:
        respx.post("https://api.deepseek.com/v1/chat/completions").mock(
            return_value=Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": "```python\ndef f(): pass\n```"}}
                    ],
                    "model": "deepseek-prover-v2",
                    "usage": {"prompt_tokens": 5, "completion_tokens": 10},
                },
            )
        )
        provider = self._make_provider()
        resp = await provider.generate("test", temperature=0.8, max_tokens=2048)
        assert "def f" in resp.code
