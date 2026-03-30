"""Abstract base for verification backends.

Every proof-assistant integration (Lean 4, Dafny, Verus) extends
``VerificationBackend`` so the rest of the pipeline can treat them
uniformly.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import UTC, datetime


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


@dataclass(frozen=True)
class VerificationResult:
    """The outcome of running a proof through a backend compiler.

    Attributes:
        success: Whether the proof compiled without errors.
        compiler_output: Raw stdout + stderr from the proof compiler.
        errors: Structured list of error messages (empty on success).
        elapsed_seconds: Wall-clock time for the compiler run.
        backend: Name of the backend that produced this result.
        timestamp: UTC time the verification completed.
    """

    success: bool
    compiler_output: str
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    backend: str = ""
    timestamp: datetime = field(default_factory=_utcnow)


_DEFAULT_TIMEOUT_SECONDS = 60


class VerificationBackend(abc.ABC):
    """Protocol that every proof-assistant backend must implement."""

    def __init__(self, *, timeout: int = _DEFAULT_TIMEOUT_SECONDS) -> None:
        self.timeout = timeout

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable name of this backend (e.g. ``'lean4'``)."""

    @abc.abstractmethod
    async def check_installed(self) -> bool:
        """Return ``True`` if the proof assistant is available on this system."""

    @abc.abstractmethod
    async def verify(self, proof_source: str) -> VerificationResult:
        """Compile *proof_source* and return the result.

        Args:
            proof_source: The full text of the proof file.

        Returns:
            A ``VerificationResult`` indicating success or failure.
        """

    @abc.abstractmethod
    def format_proof_template(
        self,
        function_name: str,
        implementation: str,
        spec_conditions: list[str],
    ) -> str:
        """Build a skeleton proof file from an implementation and its spec.

        This is fed to the LLM as a starting point for proof generation.

        Args:
            function_name: Name of the function being verified.
            implementation: Source code of the implementation.
            spec_conditions: Pre/postconditions to encode in the proof.

        Returns:
            A string containing the proof-file scaffold.
        """
