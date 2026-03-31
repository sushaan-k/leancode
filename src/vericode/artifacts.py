"""Shared helpers for verified artifact hashing and binding."""

from __future__ import annotations

import hashlib
import json

from vericode.spec import Spec


def sha256_hex(text: str) -> str:
    """Return the hex SHA-256 digest of *text*."""
    return hashlib.sha256(text.encode()).hexdigest()


def canonical_spec(spec: Spec) -> str:
    """Return a canonical JSON representation of *spec*.

    All public fields participate in the digest, so any change to the
    specification changes the resulting hash.
    """
    return json.dumps(
        spec.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )


def comment_prefix(backend_name: str) -> str:
    """Return a line-comment prefix suitable for the backend."""
    return "--" if backend_name.lower().startswith("lean") else "//"


def bound_proof_source(spec: Spec, code: str, proof: str, backend_name: str) -> str:
    """Construct the exact proof source that gets verified.

    The generated proof is prefixed with a comment-only binding header so
    the verified artifact is cryptographically tied to the spec and the
    implementation that produced it.
    """
    prefix = comment_prefix(backend_name)
    spec_hash = sha256_hex(canonical_spec(spec))
    code_hash = sha256_hex(code)
    header = "\n".join(
        [
            f"{prefix} vericode binding",
            f"{prefix} backend: {backend_name}",
            f"{prefix} spec-sha256: {spec_hash}",
            f"{prefix} code-sha256: {code_hash}",
        ]
    )
    proof_body = proof.strip()
    return f"{header}\n\n{proof_body}" if proof_body else header
