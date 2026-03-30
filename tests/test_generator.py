"""Tests for the dual code + proof generator."""

from __future__ import annotations

import pytest

from tests.conftest import FakeLLMProvider
from vericode.exceptions import GenerationError
from vericode.generator import DualGenerationResult, DualGenerator
from vericode.models.base import GenerationResponse, LLMProvider
from vericode.spec import Spec

# ---------------------------------------------------------------------------
# DualGenerator tests
# ---------------------------------------------------------------------------


class TestDualGenerator:
    """Tests for ``DualGenerator.generate`` and ``DualGenerator.refine``."""

    @pytest.fixture
    def generator(self, fake_provider: FakeLLMProvider) -> DualGenerator:
        return DualGenerator(fake_provider, temperature=0.0, max_tokens=1024)

    async def test_generate_returns_result(
        self, generator: DualGenerator, sort_spec: Spec
    ) -> None:
        result = await generator.generate(sort_spec, language="python", backend="lean4")
        assert isinstance(result, DualGenerationResult)
        assert result.code != ""
        assert result.proof != ""
        assert result.model == "fake-model"

    async def test_generate_token_counts(
        self, generator: DualGenerator, sort_spec: Spec
    ) -> None:
        result = await generator.generate(sort_spec)
        assert result.prompt_tokens == 100
        assert result.completion_tokens == 200

    async def test_generate_empty_response_raises(self, sort_spec: Spec) -> None:
        """If the provider returns no code or proof, GenerationError is raised."""

        class EmptyProvider(LLMProvider):
            @property
            def provider_name(self) -> str:
                return "empty"

            async def generate(
                self,
                prompt: str,
                *,
                system_prompt: str | None = None,
                temperature: float = 0.2,
                max_tokens: int = 4096,
            ) -> GenerationResponse:
                return GenerationResponse(
                    code="",
                    proof="",
                    raw_text="I cannot generate that.",
                    model="empty-model",
                )

        gen = DualGenerator(EmptyProvider())
        with pytest.raises(GenerationError, match="no code or proof"):
            await gen.generate(sort_spec)

    async def test_refine_returns_updated_result(
        self, generator: DualGenerator, sort_spec: Spec
    ) -> None:
        result = await generator.refine(
            sort_spec,
            previous_code="def sort(lst): pass",
            previous_proof="sorry",
            error_messages=["error: unsolved goals"],
            backend="lean4",
        )
        assert isinstance(result, DualGenerationResult)
        assert result.code != ""

    async def test_refine_preserves_previous_on_empty(self, sort_spec: Spec) -> None:
        """If refinement returns empty blocks, keep previous code/proof."""

        class PartialProvider(LLMProvider):
            @property
            def provider_name(self) -> str:
                return "partial"

            async def generate(
                self,
                prompt: str,
                *,
                system_prompt: str | None = None,
                temperature: float = 0.2,
                max_tokens: int = 4096,
            ) -> GenerationResponse:
                return GenerationResponse(
                    code="",
                    proof="",
                    raw_text="No blocks here.",
                    model="partial-model",
                )

        gen = DualGenerator(PartialProvider())
        result = await gen.refine(
            sort_spec,
            previous_code="old code",
            previous_proof="old proof",
            error_messages=["error"],
        )
        assert result.code == "old code"
        assert result.proof == "old proof"

    async def test_refine_can_lock_existing_code(self, sort_spec: Spec) -> None:
        """When asked to preserve code, refinement must not rewrite it."""
        gen = DualGenerator(FakeLLMProvider(code="def mutated(lst): return lst"))

        result = await gen.refine(
            sort_spec,
            previous_code="def original(lst): return lst",
            previous_proof="old proof",
            error_messages=["error"],
            preserve_code=True,
        )

        assert result.code == "def original(lst): return lst"

    async def test_generate_preserves_existing_code(self, sort_spec: Spec) -> None:
        """When proving existing code, the implementation must stay fixed."""
        gen = DualGenerator(FakeLLMProvider(code="def mutated(lst): return lst"))

        result = await gen.generate(
            sort_spec,
            existing_code="def original(lst): return lst",
        )

        assert result.code == "def original(lst): return lst"

    async def test_generate_with_different_languages(
        self, generator: DualGenerator, sort_spec: Spec
    ) -> None:
        for lang in ("python", "rust", "typescript"):
            result = await generator.generate(sort_spec, language=lang)
            assert result.code != ""

    async def test_generate_with_different_backends(
        self, generator: DualGenerator, sort_spec: Spec
    ) -> None:
        for backend in ("lean4", "dafny", "verus"):
            result = await generator.generate(sort_spec, backend=backend)
            assert result.proof != ""
