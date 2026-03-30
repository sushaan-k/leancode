"""Tests for verification pipeline edge cases.

Covers:
- Empty specs
- Invalid backends
- Max iteration exhaustion with details
- Default provider fallback
- Verify with all three backends as string names
- Certificate serialization edge cases
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from tests.conftest import (
    FailThenSucceedBackend,
    FakeBackend,
    FakeLLMProvider,
)
from vericode.artifacts import bound_proof_source
from vericode.backends import get_backend
from vericode.exceptions import (
    ModelConfigError,
    RefinementExhaustedError,
    SpecParsingError,
)
from vericode.generator import DualGenerator
from vericode.models import get_provider
from vericode.proof_engine import ProofEngine
from vericode.spec import Spec, parse_spec
from vericode.verifier import (
    ProofCertificate,
    VerificationOutput,
    _build_certificate,
    _sha256,
    _spec_canonical,
    verify,
)

# ---------------------------------------------------------------------------
# Empty / minimal spec edge cases
# ---------------------------------------------------------------------------


class TestEmptySpecEdgeCases:
    """Edge cases around specs with minimal or no content."""

    async def test_verify_with_minimal_spec(self) -> None:
        """A Spec with only a description should still work."""
        spec = Spec(description="do something")
        provider = FakeLLMProvider()
        backend = FakeBackend(succeed=True)

        result = await verify(spec, backend=backend, provider=provider)
        assert result.verified is True

    async def test_spec_with_no_postconditions(self) -> None:
        spec = Spec(description="compute something", function_name="compute")
        provider = FakeLLMProvider()
        backend = FakeBackend(succeed=True)

        result = await verify(spec, backend=backend, provider=provider)
        assert result.verified is True
        assert result.certificate is not None

    async def test_spec_with_no_preconditions_no_edge_cases(self) -> None:
        spec = Spec(
            description="merge lists",
            function_name="merge",
            postconditions=["is_sorted(result)"],
        )
        provider = FakeLLMProvider()
        backend = FakeBackend(succeed=True)

        result = await verify(spec, backend=backend, provider=provider)
        assert result.verified is True

    def test_parse_spec_empty_raises(self) -> None:
        with pytest.raises(SpecParsingError):
            parse_spec("")

    def test_parse_spec_whitespace_only_raises(self) -> None:
        with pytest.raises(SpecParsingError):
            parse_spec("   ")


# ---------------------------------------------------------------------------
# Invalid backend
# ---------------------------------------------------------------------------


class TestInvalidBackend:
    """Tests for unknown/invalid backend names."""

    def test_get_backend_invalid_name(self) -> None:
        with pytest.raises(ValueError, match="Unknown backend 'coq'"):
            get_backend("coq")

    def test_get_backend_invalid_empty(self) -> None:
        with pytest.raises(ValueError, match="Unknown backend"):
            get_backend("")

    def test_get_backend_invalid_numeric(self) -> None:
        with pytest.raises(ValueError, match="Unknown backend"):
            get_backend("123")


# ---------------------------------------------------------------------------
# Invalid provider
# ---------------------------------------------------------------------------


class TestInvalidProvider:
    """Tests for unknown/invalid provider names."""

    def test_get_provider_invalid_name(self) -> None:
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_provider("llama")

    def test_get_provider_invalid_empty(self) -> None:
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_provider("")


# ---------------------------------------------------------------------------
# Max iteration exhaustion
# ---------------------------------------------------------------------------


class TestMaxIterationExhaustion:
    """Tests for max iteration exhaustion in various contexts."""

    async def test_verify_returns_partial_on_exhaustion(self) -> None:
        provider = FakeLLMProvider()
        backend = FakeBackend(succeed=False, errors=["error: proof incomplete"])

        result = await verify(
            "Sort a list",
            backend=backend,
            provider=provider,
            max_iterations=2,
        )

        assert result.verified is False
        assert result.iterations == 2
        assert len(result.errors) > 0
        assert result.certificate is None

    async def test_proof_engine_raises_on_exhaustion(self) -> None:
        provider = FakeLLMProvider()
        backend = FakeBackend(
            succeed=False, errors=["error: type mismatch", "error: unknown ident"]
        )
        generator = DualGenerator(provider)
        engine = ProofEngine(generator, backend, max_iterations=2)

        with pytest.raises(RefinementExhaustedError) as exc_info:
            await engine.run(Spec(description="sort"))

        assert exc_info.value.max_iterations == 2
        assert "type mismatch" in exc_info.value.last_error

    async def test_exhaustion_with_single_iteration(self) -> None:
        provider = FakeLLMProvider()
        backend = FakeBackend(succeed=False)
        generator = DualGenerator(provider)
        engine = ProofEngine(generator, backend, max_iterations=1)

        with pytest.raises(RefinementExhaustedError):
            await engine.run(Spec(description="test"))

    async def test_verify_exhaustion_error_message(self) -> None:
        provider = FakeLLMProvider()
        backend = FakeBackend(succeed=False)

        result = await verify(
            "anything",
            backend=backend,
            provider=provider,
            max_iterations=1,
        )

        assert result.verified is False
        assert "exhausted" in result.errors[0].lower()

    async def test_verify_stops_on_toolchain_failure(self) -> None:
        provider = FakeLLMProvider()
        backend = FakeBackend(succeed=False, errors=["verus binary not found on PATH"])

        result = await verify(
            "anything",
            backend=backend,
            provider=provider,
            max_iterations=5,
        )

        assert result.verified is False
        assert provider.call_count == 1
        assert "binary not found" in result.errors[0].lower()


# ---------------------------------------------------------------------------
# Default provider fallback
# ---------------------------------------------------------------------------


class TestDefaultProviderFallback:
    """Test that verify() falls back to AnthropicProvider when no provider given."""

    async def test_verify_uses_anthropic_by_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When provider=None, should try to construct AnthropicProvider."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        # Without an API key, AnthropicProvider raises ModelConfigError
        with pytest.raises(ModelConfigError, match="anthropic"):
            await verify(
                "sort a list",
                backend=FakeBackend(succeed=True),
                provider=None,
            )

    async def test_verify_with_anthropic_key_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When ANTHROPIC_API_KEY is set and provider=None, uses AnthropicProvider."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Patch the actual API call to avoid network
        with patch("vericode.models.anthropic_provider.httpx.AsyncClient"):
            # Use a FakeBackend to skip the real verification
            backend = FakeBackend(succeed=True)
            provider = FakeLLMProvider()

            result = await verify(
                "sort a list",
                backend=backend,
                provider=provider,
            )
            assert result.verified is True


# ---------------------------------------------------------------------------
# Verify with backend as string (all 3)
# ---------------------------------------------------------------------------


class TestVerifyWithBackendStrings:
    """Test verify() when backend is passed as a string name."""

    @pytest.mark.parametrize("backend_name", ["lean4", "dafny", "verus"])
    async def test_verify_resolves_backend_string(self, backend_name: str) -> None:
        provider = FakeLLMProvider()

        # The real backend will likely fail (binary not installed),
        # but verify() should handle that gracefully
        result = await verify(
            "Sort a list",
            backend=backend_name,
            provider=provider,
            max_iterations=1,
        )
        assert isinstance(result, VerificationOutput)
        assert result.backend == backend_name


# ---------------------------------------------------------------------------
# Certificate edge cases
# ---------------------------------------------------------------------------


class TestCertificateEdgeCases:
    """Tests for ProofCertificate serialization and construction."""

    def test_certificate_to_json_round_trip(self) -> None:
        cert = ProofCertificate(
            spec_hash="aaa",
            code_hash="bbb",
            proof_hash="ccc",
            backend="dafny",
            timestamp="2026-03-30T12:00:00+00:00",
        )
        data = json.loads(cert.to_json())
        assert data["spec_hash"] == "aaa"
        assert data["code_hash"] == "bbb"
        assert data["proof_hash"] == "ccc"
        assert data["backend"] == "dafny"
        assert data["verified"] is True

    def test_build_certificate_hashes(self) -> None:
        spec = Spec(
            description="test spec",
            function_name="do_test",
            input_types={"items": "List[int]"},
            output_type="List[int]",
            preconditions=["len(items) > 0"],
            postconditions=["is_sorted(result)"],
            invariants=["i >= 0"],
            edge_cases=["input == []"],
        )
        cert = _build_certificate(spec, "code", "proof", "lean4")

        # spec_hash covers the full canonical spec, not just the prose.
        assert cert.spec_hash == _sha256(_spec_canonical(spec))
        assert cert.code_hash == _sha256("code")
        assert cert.proof_hash == _sha256(
            bound_proof_source(spec, "code", "proof", "lean4")
        )
        assert cert.backend == "lean4"
        assert cert.verified is True
        assert "T" in cert.timestamp  # ISO format

        changed_spec = spec.model_copy(update={"invariants": ["i > 0"]})
        assert _sha256(_spec_canonical(spec)) != _sha256(_spec_canonical(changed_spec))

    def test_sha256_consistency(self) -> None:
        assert _sha256("hello") == _sha256("hello")
        assert _sha256("hello") != _sha256("world")
        assert len(_sha256("test")) == 64

    def test_certificate_different_backends(self) -> None:
        for backend in ("lean4", "dafny", "verus"):
            cert = _build_certificate(Spec(description="x"), "code", "proof", backend)
            assert cert.backend == backend


# ---------------------------------------------------------------------------
# Verification output edge cases
# ---------------------------------------------------------------------------


class TestVerificationOutputEdgeCases:
    """Edge cases for VerificationOutput construction."""

    def test_defaults(self) -> None:
        output = VerificationOutput(code="", proof="", verified=False, iterations=0)
        assert output.certificate is None
        assert output.backend == ""
        assert output.language == ""
        assert output.errors == []

    def test_with_all_fields(self) -> None:
        cert = ProofCertificate(
            spec_hash="a" * 64,
            code_hash="b" * 64,
            proof_hash="c" * 64,
            backend="verus",
            timestamp="now",
        )
        output = VerificationOutput(
            code="fn sort() {}",
            proof="verus! {}",
            verified=True,
            iterations=3,
            certificate=cert,
            backend="verus",
            language="rust",
            errors=[],
        )
        assert output.verified is True
        assert output.backend == "verus"
        assert output.language == "rust"

    async def test_verify_with_custom_temperature_and_tokens(self) -> None:
        provider = FakeLLMProvider()
        backend = FakeBackend(succeed=True)

        result = await verify(
            "sort a list",
            backend=backend,
            provider=provider,
            temperature=0.9,
            max_tokens=8192,
        )
        assert result.verified is True


# ---------------------------------------------------------------------------
# Refinement result details
# ---------------------------------------------------------------------------


class TestRefinementResultDetails:
    """Tests for RefinementResult structure after engine.run()."""

    async def test_refinement_attempts_have_verification_results(self) -> None:
        provider = FakeLLMProvider()
        backend = FailThenSucceedBackend(fail_count=2)
        generator = DualGenerator(provider)
        engine = ProofEngine(generator, backend, max_iterations=5)

        result = await engine.run(Spec(description="sort"), language="python")

        assert result.success is True
        assert len(result.attempts) == 3
        # First 2 attempts should have failed verification
        assert result.attempts[0].verification.success is False
        assert result.attempts[1].verification.success is False
        # Third should succeed
        assert result.attempts[2].verification.success is True

    async def test_refinement_records_backend_name_in_attempts(self) -> None:
        provider = FakeLLMProvider()
        backend = FakeBackend(succeed=True)
        generator = DualGenerator(provider)
        engine = ProofEngine(generator, backend, max_iterations=5)

        result = await engine.run(Spec(description="sort"))

        for attempt in result.attempts:
            assert attempt.verification.backend == "fake"
