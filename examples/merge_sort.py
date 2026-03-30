#!/usr/bin/env python3
"""Example: verify a merge-sort implementation with vericode.

Demonstrates using the Dafny backend for verifying a merge-sort
algorithm with explicit postconditions about sortedness and permutation.

Usage:
    export ANTHROPIC_API_KEY=sk-...
    python examples/merge_sort.py
"""

from __future__ import annotations

import asyncio

from vericode import Spec, verify


async def main() -> None:
    """Verify a merge-sort implementation."""
    print("=" * 60)
    print("Merge Sort -- Dafny Backend")
    print("=" * 60)

    spec = Spec(
        description=(
            "Implement merge sort for a list of integers. The algorithm "
            "should split the list in half, recursively sort each half, "
            "then merge the two sorted halves."
        ),
        function_name="merge_sort",
        input_types={"lst": "List[int]"},
        output_type="List[int]",
        preconditions=[],
        postconditions=[
            "is_sorted(result)",
            "is_permutation(result, lst)",
            "len(result) == len(lst)",
        ],
        invariants=[
            "merge preserves sortedness of both halves",
            "split produces lists of roughly equal length",
        ],
        edge_cases=["lst == []", "len(lst) == 1"],
    )

    result = await verify(
        spec,
        language="python",
        backend="dafny",
        max_iterations=8,
    )

    print(f"\nVerified: {result.verified}")
    print(f"Iterations: {result.iterations}")
    print(f"Backend: {result.backend}")

    if result.code:
        print(f"\n--- Implementation ---\n{result.code}")

    if result.proof:
        print(f"\n--- Dafny Proof ---\n{result.proof}")

    if result.certificate:
        print(f"\n--- Certificate ---\n{result.certificate.to_json()}")
    elif result.errors:
        print("\n--- Errors ---")
        for err in result.errors:
            print(f"  {err}")


if __name__ == "__main__":
    asyncio.run(main())
