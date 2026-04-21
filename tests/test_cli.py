"""Tests for the CLI interface."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from vericode.cli import main
from vericode.verifier import ProofCertificate, VerificationOutput


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestCLI:
    """Tests for the vericode CLI commands."""

    def test_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "formally verified" in result.output.lower()

    def test_version(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_verify_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["verify", "--help"])
        assert result.exit_code == 0
        assert "backend" in result.output.lower()

    def test_prove_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["prove", "--help"])
        assert result.exit_code == 0

    def test_batch_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["batch", "--help"])
        assert result.exit_code == 0

    def test_cache_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["cache", "--help"])
        assert result.exit_code == 0

    def test_verify_no_args(self, runner: CliRunner) -> None:
        """Verify with no description and no --spec should error."""
        result = runner.invoke(main, ["verify"])
        assert result.exit_code != 0

    def test_verify_with_description(self, runner: CliRunner) -> None:
        """Verify with a description should call the pipeline."""
        mock_output = VerificationOutput(
            code="def sort(lst): return sorted(lst)",
            proof="theorem sort_correct := trivial",
            verified=True,
            iterations=1,
            certificate=ProofCertificate(
                spec_hash="a" * 64,
                code_hash="b" * 64,
                proof_hash="c" * 64,
                backend="lean4",
                timestamp="2026-01-01T00:00:00+00:00",
            ),
            backend="lean4",
            language="python",
        )

        with (
            patch(
                "vericode.models.get_provider",
                return_value=AsyncMock(),
            ),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(
                main,
                ["verify", "sort a list of integers"],
            )
            assert result.exit_code == 0
            assert "Verification successful" in result.output

    def test_verify_failed_output(self, runner: CliRunner) -> None:
        """Verify with a failed result should display errors."""
        mock_output = VerificationOutput(
            code="",
            proof="",
            verified=False,
            iterations=5,
            backend="lean4",
            language="python",
            errors=["Proof refinement exhausted all iterations"],
        )

        with (
            patch(
                "vericode.models.get_provider",
                return_value=AsyncMock(),
            ),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(
                main,
                ["verify", "sort a list of integers"],
            )
            assert result.exit_code == 0
            assert "failed" in result.output.lower()

    def test_verbose_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["-v", "--help"])
        assert result.exit_code == 0

    def test_cache_json(self, runner: CliRunner, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "entry.json").write_text("{}")

        result = runner.invoke(
            main,
            ["cache", "--cache-dir", str(cache_dir), "--json"],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["entries"] == 1
        assert payload["cache_dir"] == str(cache_dir)
        assert payload["bytes"] == 2
        assert "entries_detail" not in payload

    def test_cache_json_lists_entries(self, runner: CliRunner, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "wrong-shape.json").write_text("[]")
        (cache_dir / "entry.json").write_text(
            json.dumps(
                {
                    "cache_key": "entry",
                    "backend": "lean4",
                    "language": "python",
                }
            )
        )

        result = runner.invoke(
            main,
            ["cache", "--cache-dir", str(cache_dir), "--json", "--list"],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["entries_detail"][0]["cache_key"] == "entry"
