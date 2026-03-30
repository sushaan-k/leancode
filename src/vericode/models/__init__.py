"""LLM provider integrations.

Each provider implements the ``LLMProvider`` protocol, giving the
pipeline a uniform way to request code + proof generation regardless
of whether the underlying model is Claude, GPT, or DeepSeek-Prover.
"""

from __future__ import annotations

from vericode.models.anthropic_provider import AnthropicProvider
from vericode.models.base import GenerationResponse, LLMProvider
from vericode.models.deepseek import DeepSeekProvider
from vericode.models.openai_provider import OpenAIProvider

__all__ = [
    "AnthropicProvider",
    "DeepSeekProvider",
    "GenerationResponse",
    "LLMProvider",
    "OpenAIProvider",
    "get_provider",
]

_REGISTRY: dict[str, type[LLMProvider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "deepseek": DeepSeekProvider,
}


def get_provider(name: str, **kwargs: object) -> LLMProvider:
    """Instantiate an LLM provider by name.

    Args:
        name: One of ``"anthropic"``, ``"openai"``, or ``"deepseek"``.
        **kwargs: Forwarded to the provider constructor (e.g. ``api_key``).

    Returns:
        An instance of the requested provider.

    Raises:
        ValueError: If the provider name is unrecognised.
    """
    cls = _REGISTRY.get(name.lower())
    if cls is None:
        supported = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown LLM provider '{name}'. Supported: {supported}")
    return cls(**kwargs)
