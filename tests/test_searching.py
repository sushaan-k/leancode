"""End-to-end searching verification tests.

These tests exercise the full pipeline for search-related specifications
using fake providers and backends.
"""

from __future__ import annotations

from tests.conftest import FakeBackend, FakeLLMProvider
from vericode.spec import Spec, parse_spec
from vericode.verifier import verify


class TestSearchingVerification:
    """Pipeline tests for searching specifications."""

    async def test_binary_search(self) -> None:
        provider = FakeLLMProvider(
            code=(
                "def binary_search(arr: list[int], target: int) -> int:\n"
                "    lo, hi = 0, len(arr) - 1\n"
                "    while lo <= hi:\n"
                "        mid = (lo + hi) // 2\n"
                "        if arr[mid] == target:\n"
                "            return mid\n"
                "        elif arr[mid] < target:\n"
                "            lo = mid + 1\n"
                "        else:\n"
                "            hi = mid - 1\n"
                "    return -1"
            ),
            proof=(
                "theorem binary_search_correct :\n"
                "  forall (arr : List Int) (target : Int),\n"
                "  is_sorted arr ->\n"
                "  let idx := binary_search arr target\n"
                "  idx = -1 \\/ arr[idx] = target := by\n"
                "    sorry"
            ),
        )
        backend = FakeBackend(succeed=True)

        result = await verify(
            Spec(
                description="Binary search for a target in a sorted array",
                function_name="binary_search",
                input_types={"arr": "List[int]", "target": "int"},
                output_type="int",
                preconditions=["is_sorted(arr)"],
                postconditions=[
                    "result == -1 or arr[result] == target",
                ],
            ),
            language="python",
            backend=backend,
            provider=provider,
        )

        assert result.verified is True
        assert "binary_search" in result.code

    async def test_linear_search(self) -> None:
        provider = FakeLLMProvider(
            code=(
                "def search(lst: list[int], target: int) -> int:\n"
                "    for i, v in enumerate(lst):\n"
                "        if v == target:\n"
                "            return i\n"
                "    return -1"
            ),
            proof="theorem search_correct := by sorry",
        )
        backend = FakeBackend(succeed=True)

        result = await verify(
            "Search for a value in a list, return index or -1",
            backend=backend,
            provider=provider,
        )

        assert result.verified is True

    async def test_search_spec_parsing(self) -> None:
        spec = parse_spec("Search for a target in a sorted array")
        assert spec.function_name == "search"

    async def test_binary_search_spec_parsing(self) -> None:
        spec = parse_spec(
            "Perform a binary search on a sorted array, "
            "returning the index or -1 if not found"
        )
        assert spec.function_name == "binary_search"
