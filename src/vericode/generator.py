"""Dual code + proof generator.

Takes a structured ``Spec`` and uses an LLM provider to generate both
implementation source code and a formal proof of correctness in a single
pass.  Generating them together ensures the proof and the implementation
stay aligned.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from vericode.exceptions import GenerationError
from vericode.models.base import GenerationResponse, LLMProvider
from vericode.spec import Spec

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt engineering
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a world-class software engineer and formal-verification expert.
Given a specification, you generate BOTH a correct implementation AND a
formal proof of correctness.

Rules:
1. Wrap the implementation in a fenced code block tagged with the target
   language (```python, ```rust, or ```typescript).
2. Wrap the proof in a fenced code block tagged with the proof backend
   (```lean4, ```dafny, or ```verus).
3. The proof must encode the preconditions and postconditions from the spec.
4. Do NOT use sorry, admit, or other proof-skipping tactics.
5. The implementation must be efficient and idiomatic.
6. If a postcondition cannot be proved, explain why in a comment.
"""


def _build_generation_prompt(
    spec: Spec,
    language: str,
    backend: str,
    existing_code: str | None = None,
) -> str:
    """Assemble the user prompt for initial generation.

    Args:
        spec: The structured specification.
        language: Target implementation language.
        backend: Target proof-assistant backend.
        existing_code: If provided, instruct the LLM to generate only a
            proof for this code rather than new code.

    Returns:
        A prompt string ready to send to the LLM.
    """
    preconditions = (
        "\n".join(f"  - {p}" for p in spec.preconditions)
        if spec.preconditions
        else "  (none)"
    )
    postconditions = (
        "\n".join(f"  - {p}" for p in spec.postconditions)
        if spec.postconditions
        else "  (none)"
    )
    edge_cases = (
        "\n".join(f"  - {e}" for e in spec.edge_cases)
        if spec.edge_cases
        else "  (none)"
    )

    spec_block = (
        f"## Specification\n\n"
        f"**Description:** {spec.description}\n\n"
        f"**Function name:** {spec.function_name}\n"
        f"**Input types:** {spec.input_types or '(infer from description)'}\n"
        f"**Output type:** {spec.output_type or '(infer from description)'}\n\n"
        f"**Preconditions:**\n{preconditions}\n\n"
        f"**Postconditions:**\n{postconditions}\n\n"
        f"**Edge cases:**\n{edge_cases}\n\n"
    )

    if existing_code is not None:
        return (
            spec_block + f"## Existing Implementation\n\n"
            f"```{language}\n{existing_code}\n```\n\n"
            f"## Task\n\n"
            f"The implementation above is provided and must NOT be changed.\n"
            f"Generate ONLY a formal proof in **{backend}** that the "
            f"implementation satisfies ALL postconditions.\n\n"
            f"Return the proof in a fenced code block. Also return the "
            f"existing implementation unchanged in a fenced code block."
        )

    return (
        spec_block + f"## Task\n\n"
        f"Generate:\n"
        f"1. A correct implementation in **{language}**.\n"
        f"2. A formal proof in **{backend}** that the implementation "
        f"satisfies ALL postconditions.\n\n"
        f"Return both in fenced code blocks as described in your instructions."
    )


def _build_refinement_prompt(
    spec: Spec,
    previous_code: str,
    previous_proof: str,
    error_messages: list[str],
    backend: str,
    preserve_code: bool = False,
) -> str:
    """Assemble the prompt for an iterative refinement round.

    Args:
        spec: The original specification.
        previous_code: Code from the last attempt.
        previous_proof: Proof from the last attempt.
        error_messages: Errors from the proof compiler.
        backend: Target proof-assistant backend.

    Returns:
        A prompt string for the refinement attempt.
    """
    errors_block = "\n".join(error_messages)
    return (
        f"## Refinement Required\n\n"
        f"The previous proof attempt failed to compile in **{backend}**.\n\n"
        f"### Compiler errors\n```\n{errors_block}\n```\n\n"
        f"### Previous implementation\n```\n{previous_code}\n```\n\n"
        f"### Previous proof\n```\n{previous_proof}\n```\n\n"
        f"### Original specification\n{spec.description}\n\n"
        + (
            "The implementation is fixed and must remain byte-for-byte "
            "identical. Fix only the proof.\n\n"
            if preserve_code
            else "Fix the proof (and the implementation if needed) so that "
            "the proof compiles without errors.\n\n"
        )
        + "Return both in fenced code blocks."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass
class DualGenerationResult:
    """Result of generating both code and a proof.

    Attributes:
        code: Implementation source code.
        proof: Formal proof source code.
        raw_response: The full raw LLM response.
        model: Model identifier that produced the result.
        prompt_tokens: Tokens used in the prompt.
        completion_tokens: Tokens in the completion.
    """

    code: str
    proof: str
    raw_response: str = ""
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0


class DualGenerator:
    """Generates implementation code and a formal proof simultaneously.

    Args:
        provider: An LLM provider instance.
        temperature: Sampling temperature for generation.
        max_tokens: Maximum tokens in each LLM completion.
    """

    def __init__(
        self,
        provider: LLMProvider,
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> None:
        self._provider = provider
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def generate(
        self,
        spec: Spec,
        language: str = "python",
        backend: str = "lean4",
        existing_code: str | None = None,
    ) -> DualGenerationResult:
        """Generate code and a proof for the given spec.

        Args:
            spec: The structured specification to implement.
            language: Target implementation language.
            backend: Target proof-assistant backend.
            existing_code: If provided, generate only a proof for this
                code rather than generating new code.

        Returns:
            A ``DualGenerationResult`` with both code and proof.

        Raises:
            GenerationError: If the LLM returns an empty or unparseable
                response.
        """
        prompt = _build_generation_prompt(
            spec, language, backend, existing_code=existing_code
        )
        logger.info(
            "Generating code + proof",
            extra={
                "function": spec.function_name,
                "language": language,
                "backend": backend,
            },
        )

        response: GenerationResponse = await self._provider.generate(
            prompt,
            system_prompt=_SYSTEM_PROMPT,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )

        if not response.code and not response.proof:
            raise GenerationError(
                "LLM returned no code or proof blocks. "
                "The response may not have followed the expected format.",
                model=response.model,
                details=response.raw_text[:500],
            )

        return DualGenerationResult(
            code=existing_code if existing_code is not None else response.code,
            proof=response.proof,
            raw_response=response.raw_text,
            model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
        )

    async def refine(
        self,
        spec: Spec,
        previous_code: str,
        previous_proof: str,
        error_messages: list[str],
        backend: str = "lean4",
        preserve_code: bool = False,
    ) -> DualGenerationResult:
        """Refine a previous generation attempt given compiler errors.

        Args:
            spec: The original specification.
            previous_code: Code from the failed attempt.
            previous_proof: Proof from the failed attempt.
            error_messages: Errors reported by the proof compiler.
            backend: Target proof-assistant backend.
            preserve_code: Keep ``previous_code`` fixed even if the model
                returns a different implementation.

        Returns:
            An updated ``DualGenerationResult``.
        """
        prompt = _build_refinement_prompt(
            spec,
            previous_code,
            previous_proof,
            error_messages,
            backend,
            preserve_code=preserve_code,
        )
        logger.info(
            "Refining code + proof",
            extra={"errors": len(error_messages), "backend": backend},
        )

        response: GenerationResponse = await self._provider.generate(
            prompt,
            system_prompt=_SYSTEM_PROMPT,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )

        return DualGenerationResult(
            code=previous_code if preserve_code else response.code or previous_code,
            proof=response.proof or previous_proof,
            raw_response=response.raw_text,
            model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
        )
