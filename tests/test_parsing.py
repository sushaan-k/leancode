"""Tests for the shared LLM output parsing module."""

from __future__ import annotations

from vericode.parsing import parse_code_and_proof


class TestParseCodeAndProof:
    """Tests for ``parse_code_and_proof``."""

    def test_python_and_lean4(self) -> None:
        text = (
            "Here is the implementation:\n"
            "```python\ndef sort(lst):\n    return sorted(lst)\n```\n\n"
            "And the proof:\n"
            "```lean4\ntheorem sort_correct : True := trivial\n```"
        )
        code, proof = parse_code_and_proof(text)
        assert "def sort" in code
        assert "theorem sort_correct" in proof

    def test_rust_and_dafny(self) -> None:
        text = (
            "```rust\nfn sort(v: &mut Vec<i32>) { v.sort(); }\n```\n\n"
            "```dafny\nmethod Sort(s: seq<int>)\n  ensures true\n{}\n```"
        )
        code, proof = parse_code_and_proof(text)
        assert "fn sort" in code
        assert "method Sort" in proof

    def test_typescript_and_verus(self) -> None:
        text = (
            "```typescript\nfunction sort(arr: number[]): number[] { "
            "return arr.sort(); }\n```\n\n"
            "```verus\nverus! { fn sort() { } }\n```"
        )
        code, proof = parse_code_and_proof(text)
        assert "function sort" in code
        assert "verus!" in proof

    def test_no_code_block(self) -> None:
        text = "```lean4\ntheorem foo := trivial\n```"
        code, proof = parse_code_and_proof(text)
        assert code == ""
        assert "theorem foo" in proof

    def test_no_proof_block(self) -> None:
        text = "```python\ndef foo(): pass\n```"
        code, proof = parse_code_and_proof(text)
        assert "def foo" in code
        assert proof == ""

    def test_empty_text(self) -> None:
        code, proof = parse_code_and_proof("")
        assert code == ""
        assert proof == ""

    def test_no_fenced_blocks(self) -> None:
        code, proof = parse_code_and_proof("just some plain text")
        assert code == ""
        assert proof == ""

    def test_lean_without_4(self) -> None:
        """The regex accepts both ```lean and ```lean4."""
        text = "```lean\ntheorem bar := trivial\n```"
        _code, proof = parse_code_and_proof(text)
        assert "theorem bar" in proof

    def test_strips_whitespace(self) -> None:
        text = "```python\n\n  def f(): pass\n\n```"
        code, _proof = parse_code_and_proof(text)
        assert code == "def f(): pass"

    def test_multiple_code_blocks_picks_first(self) -> None:
        text = (
            "```python\ndef first(): pass\n```\n"
            "```python\ndef second(): pass\n```\n"
            "```lean4\ntheorem t := trivial\n```"
        )
        code, _proof = parse_code_and_proof(text)
        assert "first" in code
        assert "second" not in code
