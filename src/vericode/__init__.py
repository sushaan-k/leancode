"""vericode -- formally verified AI code generation.

The primary public API consists of:

- ``verify()``: Run the full pipeline (spec -> code + proof -> verified).
- ``Spec``: Structured specification for code generation.
- ``parse_spec()``: Parse natural language into a ``Spec``.

Example::

    from vericode import verify, Spec

    result = await verify(
        "sort a list of integers",
        language="python",
        backend="lean4",
    )
    print(result.code)
    print(result.verified)
"""

from vericode.spec import Spec, parse_spec
from vericode.verifier import ProofCertificate, VerificationOutput, verify

__all__ = [
    "ProofCertificate",
    "Spec",
    "VerificationOutput",
    "parse_spec",
    "verify",
]

__version__ = "0.1.0"
