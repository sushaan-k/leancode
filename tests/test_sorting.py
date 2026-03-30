"""End-to-end sorting verification tests.

These tests exercise the full pipeline for sorting-related specifications
using fake providers and backends.
"""

from __future__ import annotations

from tests.conftest import FakeBackend, FakeLLMProvider
from vericode.spec import Spec, parse_spec
from vericode.verifier import verify


class TestSortingVerification:
    """Pipeline tests for sorting specifications."""

    async def test_sort_integers(self) -> None:
        provider = FakeLLMProvider(
            code="def sort(lst: list[int]) -> list[int]:\n    return sorted(lst)",
            proof=(
                "theorem sort_correct :\n"
                "  forall (lst : List Int),\n"
                "  is_sorted (sort lst) := by\n"
                "    intro lst\n"
                "    simp [sort, is_sorted]"
            ),
        )
        backend = FakeBackend(succeed=True)

        result = await verify(
            "Sort a list of integers in non-decreasing order",
            language="python",
            backend=backend,
            provider=provider,
        )

        assert result.verified is True
        assert "sorted" in result.code
        assert result.certificate is not None

    async def test_sort_with_explicit_spec(self) -> None:
        spec = Spec(
            description="Sort integers",
            function_name="sort",
            input_types={"lst": "List[int]"},
            output_type="List[int]",
            postconditions=["is_sorted(result)", "is_permutation(result, lst)"],
            edge_cases=["lst == []"],
        )
        provider = FakeLLMProvider()
        backend = FakeBackend(succeed=True)

        result = await verify(
            spec,
            language="python",
            backend=backend,
            provider=provider,
        )

        assert result.verified is True

    async def test_sort_spec_parsing(self) -> None:
        spec = parse_spec(
            "Write a function that sorts a list of integers. "
            "The output must be a permutation of the input. "
            "The output must be in non-decreasing order."
        )
        assert spec.function_name == "sort"
        assert any("permutation" in p.lower() for p in spec.postconditions)
        # "non-decreasing" triggers a range-based ordering postcondition
        assert any(
            "non-decreasing" in p.lower() or "<=" in p for p in spec.postconditions
        )

    async def test_sort_empty_list_edge_case(self) -> None:
        spec = parse_spec("Sort a list, handle empty lists")
        assert any("empty" in e.lower() or "[]" in e for e in spec.edge_cases)
