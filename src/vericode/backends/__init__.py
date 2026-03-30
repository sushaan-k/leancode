"""Verification backends for proof assistants.

Each backend implements the ``VerificationBackend`` protocol, providing
a uniform interface for compiling and checking proofs across different
proof-assistant toolchains.
"""

from __future__ import annotations

from vericode.backends.base import VerificationBackend, VerificationResult
from vericode.backends.dafny import DafnyBackend
from vericode.backends.lean4 import Lean4Backend
from vericode.backends.verus import VerusBackend

__all__ = [
    "DafnyBackend",
    "Lean4Backend",
    "VerificationBackend",
    "VerificationResult",
    "VerusBackend",
    "get_backend",
]

_REGISTRY: dict[str, type[VerificationBackend]] = {
    "lean4": Lean4Backend,
    "dafny": DafnyBackend,
    "verus": VerusBackend,
}


def get_backend(name: str) -> VerificationBackend:
    """Instantiate a verification backend by name.

    Args:
        name: One of ``"lean4"``, ``"dafny"``, or ``"verus"``.

    Returns:
        An instance of the corresponding backend.

    Raises:
        ValueError: If the backend name is unrecognised.
    """
    cls = _REGISTRY.get(name.lower())
    if cls is None:
        supported = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown backend '{name}'. Supported backends: {supported}")
    return cls()
