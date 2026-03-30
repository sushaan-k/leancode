"""OpenAI (GPT) LLM provider.

Uses ``httpx`` for async HTTP calls to the OpenAI Chat Completions API.
"""

from __future__ import annotations

import logging
import os

import httpx

from vericode.exceptions import GenerationError, ModelConfigError
from vericode.models.base import GenerationResponse, LLMProvider
from vericode.parsing import parse_code_and_proof

logger = logging.getLogger(__name__)

_API_URL = "https://api.openai.com/v1/chat/completions"
_DEFAULT_MODEL = "gpt-4o"


class OpenAIProvider(LLMProvider):
    """GPT model provider via the OpenAI API.

    Args:
        api_key: OpenAI API key.  Falls back to ``OPENAI_API_KEY``.
        model: Model identifier (default: ``gpt-4o``).
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = _DEFAULT_MODEL,
        **_kwargs: object,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model
        if not self._api_key:
            raise ModelConfigError(
                "openai",
                "No API key provided. Set OPENAI_API_KEY or pass api_key=.",
            )

    @property
    def provider_name(self) -> str:
        """Return the provider identifier."""
        return "openai"

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> GenerationResponse:
        """Call the OpenAI Chat Completions API and parse the response.

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
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body: dict[str, object] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(_API_URL, json=body, headers=headers)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise GenerationError(
                    f"OpenAI API returned {exc.response.status_code}",
                    model=self._model,
                    details=exc.response.text,
                ) from exc
            except httpx.HTTPError as exc:
                raise GenerationError(
                    f"OpenAI API request failed: {exc}",
                    model=self._model,
                ) from exc

        try:
            data = resp.json()
        except ValueError as exc:
            raise GenerationError(
                "OpenAI API returned invalid JSON",
                model=self._model,
                details="response body could not be parsed as JSON",
            ) from exc

        try:
            raw_text, usage = _extract_openai_response(data)
        except ValueError as exc:
            raise GenerationError(
                "OpenAI API returned an unexpected response shape",
                model=self._model,
                details="expected choices[0].message.content and usage metadata",
            ) from exc

        code, proof = parse_code_and_proof(raw_text)

        return GenerationResponse(
            code=code,
            proof=proof,
            raw_text=raw_text,
            model=data.get("model", self._model),
            prompt_tokens=_usage_int(usage, "prompt_tokens"),
            completion_tokens=_usage_int(usage, "completion_tokens"),
        )


def _extract_openai_response(data: object) -> tuple[str, dict[str, object]]:
    """Extract content and usage data from an OpenAI response payload."""
    if not isinstance(data, dict):
        raise ValueError("response payload must be a JSON object")

    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("choices list missing")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise ValueError("choices[0] must be an object")

    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise ValueError("choices[0].message must be an object")

    raw_text = message.get("content")
    if not isinstance(raw_text, str):
        raise ValueError("choices[0].message.content must be a string")

    usage = data.get("usage", {})
    if not isinstance(usage, dict):
        usage = {}

    return raw_text, usage


def _usage_int(usage: dict[str, object], key: str) -> int:
    """Extract an integer token count from a provider usage payload."""
    value = usage.get(key, 0)
    return int(value) if isinstance(value, int | float) else 0
