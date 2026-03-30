"""Tests for the iterative proof-refinement engine."""

from __future__ import annotations

import pytest

from tests.conftest import (
    FailThenSucceedBackend,
    FakeBackend,
    FakeLLMProvider,
)
from vericode.exceptions import RefinementExhaustedError
from vericode.generator import DualGenerator
from vericode.proof_engine import ProofEngine
from vericode.spec import Spec


class TestProofEngine:
    """Tests for ``ProofEngine.run``."""

    async def test_success_on_first_try(self, sort_spec: Spec) -> None:
        """If the backend accepts the proof immediately, one iteration."""
        provider = FakeLLMProvider()
        backend = FakeBackend(succeed=True)
        generator = DualGenerator(provider)
        engine = ProofEngine(generator, backend, max_iterations=5)

        result = await engine.run(sort_spec, language="python")

        assert result.success is True
        assert result.iterations == 1
        assert len(result.attempts) == 1
        assert result.code != ""
        assert result.proof != ""

    async def test_success_after_refinement(self, sort_spec: Spec) -> None:
        """The engine should refine and eventually succeed."""
        provider = FakeLLMProvider()
        backend = FailThenSucceedBackend(fail_count=2)
        generator = DualGenerator(provider)
        engine = ProofEngine(generator, backend, max_iterations=5)

        result = await engine.run(sort_spec, language="python")

        assert result.success is True
        assert result.iterations == 3  # 2 failures + 1 success
        assert len(result.attempts) == 3

    async def test_exhaustion_raises(self, sort_spec: Spec) -> None:
        """If all iterations fail, RefinementExhaustedError is raised."""
        provider = FakeLLMProvider()
        backend = FakeBackend(succeed=False, errors=["error: proof failed"])
        generator = DualGenerator(provider)
        engine = ProofEngine(generator, backend, max_iterations=3)

        with pytest.raises(RefinementExhaustedError, match="3 iterations"):
            await engine.run(sort_spec)

    async def test_token_accounting(self, sort_spec: Spec) -> None:
        """Token counts should accumulate across iterations."""
        provider = FakeLLMProvider()
        backend = FailThenSucceedBackend(fail_count=1)
        generator = DualGenerator(provider)
        engine = ProofEngine(generator, backend, max_iterations=5)

        result = await engine.run(sort_spec)

        # Initial generation + 1 refinement = 2 calls
        assert result.total_prompt_tokens == 200  # 100 * 2
        assert result.total_completion_tokens == 400  # 200 * 2

    async def test_attempts_record_details(self, sort_spec: Spec) -> None:
        """Each attempt should record code, proof, and verification result."""
        provider = FakeLLMProvider()
        backend = FailThenSucceedBackend(fail_count=1)
        generator = DualGenerator(provider)
        engine = ProofEngine(generator, backend, max_iterations=5)

        result = await engine.run(sort_spec)

        for attempt in result.attempts:
            assert attempt.iteration >= 1
            assert attempt.code != ""
            assert attempt.proof != ""
            assert attempt.verification is not None

    async def test_single_iteration_limit(self, sort_spec: Spec) -> None:
        """With max_iterations=1 and failure, should raise."""
        provider = FakeLLMProvider()
        backend = FakeBackend(succeed=False)
        generator = DualGenerator(provider)
        engine = ProofEngine(generator, backend, max_iterations=1)

        with pytest.raises(RefinementExhaustedError, match="1 iteration"):
            await engine.run(sort_spec)

    async def test_provider_called_correct_number_of_times(
        self, sort_spec: Spec
    ) -> None:
        """Verify the LLM is called once for initial + once per refinement."""
        provider = FakeLLMProvider()
        backend = FailThenSucceedBackend(fail_count=2)
        generator = DualGenerator(provider)
        engine = ProofEngine(generator, backend, max_iterations=5)

        await engine.run(sort_spec)

        # 1 initial + 2 refinements = 3 calls
        assert provider.call_count == 3

    async def test_fatal_backend_failure_stops_after_one_attempt(
        self, sort_spec: Spec
    ) -> None:
        """Toolchain failures should not trigger refinement loops."""
        provider = FakeLLMProvider()
        backend = FakeBackend(succeed=False, errors=["lean binary not found on PATH"])
        generator = DualGenerator(provider)
        engine = ProofEngine(generator, backend, max_iterations=5)

        with pytest.raises(RefinementExhaustedError, match="binary not found"):
            await engine.run(sort_spec)

        assert provider.call_count == 1
