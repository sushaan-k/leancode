#!/usr/bin/env python3
"""Example: verify a binary search implementation with vericode.

This example demonstrates both the one-liner API and the explicit Spec API
for generating and formally verifying a binary search algorithm.

Usage:
    export ANTHROPIC_API_KEY=sk-...
    python examples/binary_search.py
"""

from __future__ import annotations

import asyncio

from vericode import Spec, verify


async def one_liner_example() -> None:
    """Use the simple one-liner API."""
    print("=" * 60)
    print("Binary Search -- One-liner API")
    print("=" * 60)

    result = await verify(
        "Write a binary search that returns the index of a target "
        "in a sorted array, or -1 if not found.",
        language="python",
        backend="lean4",
    )

    print(f"\nVerified: {result.verified}")
    print(f"Iterations: {result.iterations}")
    print(f"Backend: {result.backend}")

    if result.code:
        print(f"\n--- Implementation ---\n{result.code}")

    if result.proof:
        print(f"\n--- Proof ---\n{result.proof}")

    if result.certificate:
        print(f"\n--- Certificate ---\n{result.certificate.to_json()}")


async def explicit_spec_example() -> None:
    """Use the explicit Spec API for fine-grained control."""
    print("\n" + "=" * 60)
    print("Binary Search -- Explicit Spec API")
    print("=" * 60)

    spec = Spec(
        description=(
            "Binary search: given a sorted array of integers and a target, "
            "return the index of the target or -1 if not found."
        ),
        function_name="binary_search",
        input_types={"arr": "List[int]", "target": "int"},
        output_type="int",
        preconditions=["is_sorted(arr)"],
        postconditions=[
            "result == -1 or (0 <= result < len(arr) and arr[result] == target)",
            "result == -1 implies target not in arr",
        ],
        edge_cases=["arr == []", "len(arr) == 1", "target < arr[0]"],
    )

    result = await verify(
        spec,
        language="python",
        backend="lean4",
        max_iterations=10,
        temperature=0.1,
    )

    print(f"\nVerified: {result.verified}")
    print(f"Iterations: {result.iterations}")

    if result.verified:
        print("\nThe implementation is PROVEN CORRECT against the spec.")
    else:
        print("\nVerification did not succeed.")
        for err in result.errors:
            print(f"  Error: {err}")


async def main() -> None:
    """Run both examples."""
    await one_liner_example()
    await explicit_spec_example()


if __name__ == "__main__":
    asyncio.run(main())
