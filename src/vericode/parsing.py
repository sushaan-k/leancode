"""Shared utilities for extracting fenced code blocks from LLM output.

The LLM is prompted to wrap generated code in ```language ... ``` blocks
and proofs in ```backend ... ``` blocks. This module provides a single
reusable parser so that every provider does not need its own copy.
"""

from __future__ import annotations

import re

# Fenced-block regexes
_CODE_BLOCK_RE = re.compile(
    r"```(?:python|rust|typescript)\s*\n(.*?)```",
    re.DOTALL,
)
_PROOF_BLOCK_RE = re.compile(
    r"```(?:lean4?|dafny|verus)\s*\n(.*?)```",
    re.DOTALL,
)


def parse_code_and_proof(text: str) -> tuple[str, str]:
    """Extract the first implementation code block and proof block from text.

    Args:
        text: Raw LLM output containing fenced code blocks.

    Returns:
        A ``(code, proof)`` tuple.  Either value may be the empty string
        if the corresponding block was not found.
    """
    code_match = _CODE_BLOCK_RE.search(text)
    proof_match = _PROOF_BLOCK_RE.search(text)

    code = code_match.group(1).strip() if code_match else ""
    proof = proof_match.group(1).strip() if proof_match else ""

    return code, proof
