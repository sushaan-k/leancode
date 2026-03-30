#!/usr/bin/env python3
"""Example: verify a balanced BST insertion with vericode.

Demonstrates using the Verus backend for verifying a Rust-targeted
balanced BST insertion that preserves the BST invariant.

Usage:
    export ANTHROPIC_API_KEY=sk-...
    python examples/balanced_bst.py
"""

from __future__ import annotations

import asyncio

from vericode import Spec, verify


async def main() -> None:
    """Verify a BST insertion implementation."""
    print("=" * 60)
    print("Balanced BST Insertion -- Lean 4 Backend")
    print("=" * 60)

    spec = Spec(
        description=(
            "Implement insertion into a binary search tree. After insertion, "
            "the BST invariant must be preserved: for every node, all values "
            "in the left subtree are less than the node, and all values in "
            "the right subtree are greater than or equal to the node."
        ),
        function_name="bst_insert",
        input_types={"root": "Optional[TreeNode]", "val": "int"},
        output_type="TreeNode",
        preconditions=["is_bst(root)"],
        postconditions=[
            "is_bst(result)",
            "contains(result, val)",
            "size(result) == size(root) + (0 if contains(root, val) else 1)",
        ],
        edge_cases=["root is None", "val already in tree"],
    )

    result = await verify(
        spec,
        language="python",
        backend="lean4",
        max_iterations=10,
    )

    print(f"\nVerified: {result.verified}")
    print(f"Iterations: {result.iterations}")
    print(f"Backend: {result.backend}")

    if result.code:
        print(f"\n--- Implementation ---\n{result.code}")

    if result.proof:
        print(f"\n--- Lean 4 Proof ---\n{result.proof}")

    if result.certificate:
        print(f"\n--- Certificate ---\n{result.certificate.to_json()}")
    elif result.errors:
        print("\n--- Errors ---")
        for err in result.errors:
            print(f"  {err}")


if __name__ == "__main__":
    asyncio.run(main())
