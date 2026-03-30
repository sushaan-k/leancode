"""Abstract base for LLM providers.

Defines the ``LLMProvider`` protocol and the ``GenerationResponse``
data class that all providers return.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field


@dataclass(frozen=True)
class GenerationResponse:
    """Structured response from an LLM generation call.

    Attributes:
        code: Generated implementation source code.
        proof: Generated formal proof source code.
        raw_text: The complete raw text returned by the model.
        model: Identifier of the model that produced this response.
        prompt_tokens: Number of tokens in the prompt.
        completion_tokens: Number of tokens in the completion.
        metadata: Additional provider-specific metadata.
    """

    code: str
    proof: str
    raw_text: str = ""
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    metadata: dict[str, object] = field(default_factory=dict)


class LLMProvider(abc.ABC):
    """Protocol that every LLM provider must implement."""

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Return a human-readable provider identifier."""

    @abc.abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> GenerationResponse:
        """Send a prompt to the model and return structured output.

        Args:
            prompt: The user prompt (typically the spec + context).
            system_prompt: Optional system-level instructions.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the completion.

        Returns:
            A ``GenerationResponse`` with parsed code and proof sections.
        """
