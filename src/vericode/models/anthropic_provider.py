"""Anthropic (Claude) LLM provider.

Uses ``httpx`` for async HTTP calls to the Anthropic Messages API.
Optionally uses the ``anthropic`` SDK when installed.
"""

from __future__ import annotations

import logging
import os

import httpx

from vericode.exceptions import GenerationError, ModelConfigError
from vericode.models.base import GenerationResponse, LLMProvider
from vericode.parsing import parse_code_and_proof

logger = logging.getLogger(__name__)

_API_URL = "https://api.anthropic.com/v1/messages"
_DEFAULT_MODEL = "claude-sonnet-4-20250514"


class AnthropicProvider(LLMProvider):
    """Claude model provider via the Anthropic API.

    Args:
        api_key: Anthropic API key.  Falls back to the
            ``ANTHROPIC_API_KEY`` environment variable.
        model: Model identifier (default: ``claude-sonnet-4-20250514``).
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = _DEFAULT_MODEL,
        **_kwargs: object,
    ) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._model = model
        if not self._api_key:
            raise ModelConfigError(
                "anthropic",
                "No API key provided. Set ANTHROPIC_API_KEY or pass api_key=.",
            )

    @property
    def provider_name(self) -> str:
        """Return the provider identifier."""
        return "anthropic"

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> GenerationResponse:
        """Call the Anthropic Messages API and parse the response.

        Args:
            prompt: User prompt containing the spec and context.
            system_prompt: Optional system instructions.
            temperature: Sampling temperature.
            max_tokens: Maximum completion tokens.

        Returns:
            A ``GenerationResponse`` with parsed code and proof.

        Raises:
            GenerationError: On API errors or unparseable responses.
        """
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body: dict[str, object] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            body["system"] = system_prompt

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(_API_URL, json=body, headers=headers)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise GenerationError(
                    f"Anthropic API returned {exc.response.status_code}",
                    model=self._model,
                    details=exc.response.text,
                ) from exc
            except httpx.HTTPError as exc:
                raise GenerationError(
                    f"Anthropic API request failed: {exc}",
                    model=self._model,
                ) from exc

        try:
            data = resp.json()
        except ValueError as exc:
            raise GenerationError(
                "Anthropic API returned invalid JSON",
                model=self._model,
                details="response body could not be parsed as JSON",
            ) from exc

        try:
            raw_text, usage = _extract_anthropic_response(data)
        except ValueError as exc:
            raise GenerationError(
                "Anthropic API returned an unexpected response shape",
                model=self._model,
                details="expected content[0].text and usage metadata",
            ) from exc

        code, proof = parse_code_and_proof(raw_text)

        return GenerationResponse(
            code=code,
            proof=proof,
            raw_text=raw_text,
            model=data.get("model", self._model),
            prompt_tokens=_usage_int(usage, "input_tokens"),
            completion_tokens=_usage_int(usage, "output_tokens"),
        )


def _extract_anthropic_response(data: object) -> tuple[str, dict[str, object]]:
    """Extract content and usage data from an Anthropic response payload."""
    if not isinstance(data, dict):
        raise ValueError("response payload must be a JSON object")

    content = data.get("content")
    if not isinstance(content, list) or not content:
        raise ValueError("content list missing")

    first_block = content[0]
    if not isinstance(first_block, dict):
        raise ValueError("content[0] must be an object")

    raw_text = first_block.get("text")
    if not isinstance(raw_text, str):
        raise ValueError("content[0].text must be a string")

    usage = data.get("usage", {})
    if not isinstance(usage, dict):
        usage = {}

    return raw_text, usage


def _usage_int(usage: dict[str, object], key: str) -> int:
    """Extract an integer token count from a provider usage payload."""
    value = usage.get(key, 0)
    return int(value) if isinstance(value, int | float) else 0
