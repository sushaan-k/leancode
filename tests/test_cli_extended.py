"""Extended CLI tests covering prove, batch, output writing, and edge cases."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml
from click.testing import CliRunner

from vericode.cli import main
from vericode.verifier import ProofCertificate, VerificationOutput


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _mock_verified_output(
    *,
    backend: str = "lean4",
    language: str = "python",
    verified: bool = True,
) -> VerificationOutput:
    """Build a mock VerificationOutput for CLI tests."""
    cert = (
        ProofCertificate(
            spec_hash="a" * 64,
            code_hash="b" * 64,
            proof_hash="c" * 64,
            backend=backend,
            timestamp="2026-01-01T00:00:00+00:00",
        )
        if verified
        else None
    )
    return VerificationOutput(
        code="def sort(lst): return sorted(lst)" if verified else "",
        proof="theorem sort_correct := trivial" if verified else "",
        verified=verified,
        iterations=1 if verified else 5,
        certificate=cert,
        backend=backend,
        language=language,
        errors=[] if verified else ["Proof refinement exhausted"],
    )


# ---------------------------------------------------------------------------
# verify subcommand -- spec file path
# ---------------------------------------------------------------------------


class TestVerifyWithSpecFile:
    """Test the verify command when --spec is used instead of a description."""

    def test_verify_with_spec_file(self, runner: CliRunner, tmp_path: Path) -> None:
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(
            yaml.dump(
                {
                    "description": "Sort a list of integers",
                    "function_name": "sort",
                    "postconditions": ["is_sorted(result)"],
                }
            )
        )
        mock_output = _mock_verified_output(language="lean")

        with (
            patch("vericode.models.get_provider", return_value=AsyncMock()),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(
                main,
                ["verify", "--spec", str(spec_file)],
            )
            assert result.exit_code == 0
            assert "Verification successful" in result.output


# ---------------------------------------------------------------------------
# verify subcommand -- output file
# ---------------------------------------------------------------------------


class TestVerifyOutputFile:
    """Test the verify command --output/-o flag for writing results to JSON."""

    def test_verify_writes_output_file(self, runner: CliRunner, tmp_path: Path) -> None:
        output_file = tmp_path / "result.json"
        mock_output = _mock_verified_output(language="lean")

        with (
            patch("vericode.models.get_provider", return_value=AsyncMock()),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(
                main,
                [
                    "verify",
                    "sort a list of integers",
                    "-o",
                    str(output_file),
                ],
            )
            assert result.exit_code == 0

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data["verified"] is True
        assert data["code"] != ""
        assert data["certificate"] is not None
        assert data["certificate"]["backend"] == "lean4"

    def test_verify_failed_output_file(self, runner: CliRunner, tmp_path: Path) -> None:
        output_file = tmp_path / "result.json"
        mock_output = _mock_verified_output(verified=False)

        with (
            patch("vericode.models.get_provider", return_value=AsyncMock()),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(
                main,
                [
                    "verify",
                    "sort a list",
                    "-o",
                    str(output_file),
                ],
            )
            assert result.exit_code == 0

        data = json.loads(output_file.read_text())
        assert data["verified"] is False
        assert data["certificate"] is None


# ---------------------------------------------------------------------------
# prove subcommand
# ---------------------------------------------------------------------------


class TestProveCommand:
    """Tests for the ``vericode prove`` subcommand."""

    def test_prove_with_code_file(self, runner: CliRunner, tmp_path: Path) -> None:
        code_file = tmp_path / "sort.py"
        code_file.write_text("def sort(lst): return sorted(lst)")

        mock_output = _mock_verified_output(language="lean")

        with (
            patch("vericode.models.get_provider", return_value=AsyncMock()),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(
                main,
                [
                    "prove",
                    "--code",
                    str(code_file),
                    "--spec",
                    "output is sorted permutation of input",
                ],
            )
            assert result.exit_code == 0
            assert "Verification successful" in result.output

    def test_prove_with_failed_result(self, runner: CliRunner, tmp_path: Path) -> None:
        code_file = tmp_path / "bad.py"
        code_file.write_text("def bad(): pass")

        mock_output = _mock_verified_output(verified=False)

        with (
            patch("vericode.models.get_provider", return_value=AsyncMock()),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(
                main,
                [
                    "prove",
                    "--code",
                    str(code_file),
                    "--spec",
                    "some specification",
                ],
            )
            assert result.exit_code == 0
            assert "failed" in result.output.lower()

    @pytest.mark.parametrize("backend", ["lean4", "dafny", "verus"])
    def test_prove_with_different_backends(
        self, runner: CliRunner, tmp_path: Path, backend: str
    ) -> None:
        code_file = tmp_path / "code.py"
        code_file.write_text("def f(): pass")
        mock_output = _mock_verified_output(backend=backend)

        with (
            patch("vericode.models.get_provider", return_value=AsyncMock()),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(
                main,
                [
                    "prove",
                    "--code",
                    str(code_file),
                    "--spec",
                    "some spec",
                    "--backend",
                    backend,
                ],
            )
            assert result.exit_code == 0

    @pytest.mark.parametrize("provider", ["anthropic", "openai", "deepseek"])
    def test_prove_with_different_providers(
        self, runner: CliRunner, tmp_path: Path, provider: str
    ) -> None:
        code_file = tmp_path / "code.py"
        code_file.write_text("def f(): pass")
        mock_output = _mock_verified_output(language="lean")

        with (
            patch("vericode.models.get_provider", return_value=AsyncMock()),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(
                main,
                [
                    "prove",
                    "--code",
                    str(code_file),
                    "--spec",
                    "some spec",
                    "--provider",
                    provider,
                ],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# batch subcommand
# ---------------------------------------------------------------------------


class TestBatchCommand:
    """Tests for the ``vericode batch`` subcommand."""

    def test_batch_no_yaml_files(self, runner: CliRunner, tmp_path: Path) -> None:
        """Empty specs directory should fail with exit code 1."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        output_dir = tmp_path / "output"

        result = runner.invoke(
            main,
            ["batch", "--specs", str(specs_dir), "-o", str(output_dir)],
        )
        assert result.exit_code != 0

    def test_batch_processes_yaml_files(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        output_dir = tmp_path / "output"

        # Create two yaml spec files
        for name in ("sort", "search"):
            (specs_dir / f"{name}.yaml").write_text(
                yaml.dump(
                    {
                        "description": f"{name} a list",
                        "function_name": name,
                    }
                )
            )

        mock_output = _mock_verified_output(language="lean")

        with (
            patch("vericode.models.get_provider", return_value=AsyncMock()),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(
                main,
                ["batch", "--specs", str(specs_dir), "-o", str(output_dir)],
            )
            assert result.exit_code == 0
            assert "2 spec file(s)" in result.output

        # Check that output files were created
        assert (output_dir / "sort.lean").exists()
        assert (output_dir / "sort.proof").exists()
        assert (output_dir / "sort.cert.json").exists()
        assert (output_dir / "search.lean").exists()

    def test_batch_handles_yml_extension(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        output_dir = tmp_path / "output"

        (specs_dir / "merge.yml").write_text(
            yaml.dump({"description": "merge lists", "function_name": "merge"})
        )

        mock_output = _mock_verified_output(language="lean")

        with (
            patch("vericode.models.get_provider", return_value=AsyncMock()),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(
                main,
                ["batch", "--specs", str(specs_dir), "-o", str(output_dir)],
            )
            assert result.exit_code == 0
            assert "1 spec file(s)" in result.output

        assert (output_dir / "merge.lean").exists()

    def test_batch_backend_selects_native_language(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        output_dir = tmp_path / "output"

        (specs_dir / "sort.yaml").write_text(
            yaml.dump({"description": "sort a list", "function_name": "sort"})
        )

        mock_output = _mock_verified_output(backend="verus", language="rust")

        with (
            patch("vericode.models.get_provider", return_value=AsyncMock()),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(
                main,
                [
                    "batch",
                    "--specs",
                    str(specs_dir),
                    "-o",
                    str(output_dir),
                    "--backend",
                    "verus",
                ],
            )
            assert result.exit_code == 0

        assert (output_dir / "sort.rs").exists()

    def test_batch_failed_verification_no_output_files(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        output_dir = tmp_path / "output"

        (specs_dir / "bad.yaml").write_text(
            yaml.dump({"description": "bad spec", "function_name": "bad"})
        )

        mock_output = _mock_verified_output(verified=False)

        with (
            patch("vericode.models.get_provider", return_value=AsyncMock()),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(
                main,
                ["batch", "--specs", str(specs_dir), "-o", str(output_dir)],
            )
            assert result.exit_code == 0
            assert "Failed" in result.output
            # No output files for failed verification
            assert not (output_dir / "bad.py").exists()


# ---------------------------------------------------------------------------
# verify subcommand -- backend/provider parametrized
# ---------------------------------------------------------------------------


class TestVerifyParametrized:
    """Parametrized tests for the verify command with all backends/providers."""

    @pytest.mark.parametrize("backend", ["lean4", "dafny", "verus"])
    def test_verify_all_backends(self, runner: CliRunner, backend: str) -> None:
        mock_output = _mock_verified_output(backend=backend)

        with (
            patch("vericode.models.get_provider", return_value=AsyncMock()),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(
                main,
                [
                    "verify",
                    "sort a list",
                    "--backend",
                    backend,
                ],
            )
            assert result.exit_code == 0

    @pytest.mark.parametrize("provider", ["anthropic", "openai", "deepseek"])
    def test_verify_all_providers(self, runner: CliRunner, provider: str) -> None:
        mock_output = _mock_verified_output()

        with (
            patch("vericode.models.get_provider", return_value=AsyncMock()),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(
                main,
                [
                    "verify",
                    "sort a list",
                    "--provider",
                    provider,
                ],
            )
            assert result.exit_code == 0

    def test_verify_custom_max_iterations(self, runner: CliRunner) -> None:
        mock_output = _mock_verified_output()

        with (
            patch("vericode.models.get_provider", return_value=AsyncMock()),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(
                main,
                [
                    "verify",
                    "sort a list",
                    "--max-iterations",
                    "10",
                ],
            )
            assert result.exit_code == 0

    def test_verify_verbose(self, runner: CliRunner) -> None:
        mock_output = _mock_verified_output()

        with (
            patch("vericode.models.get_provider", return_value=AsyncMock()),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(
                main,
                ["-v", "verify", "sort a list"],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI display helpers
# ---------------------------------------------------------------------------


class TestDisplayHelpers:
    """Test _display_result for various VerificationOutput shapes."""

    def test_display_with_code_no_proof(self, runner: CliRunner) -> None:
        """If code is present but proof is empty, no crash."""
        mock_output = VerificationOutput(
            code="def f(): pass",
            proof="",
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
            patch("vericode.models.get_provider", return_value=AsyncMock()),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(main, ["verify", "do something"])
            assert result.exit_code == 0
            assert "Verification successful" in result.output

    def test_display_with_no_code_no_proof(self, runner: CliRunner) -> None:
        """If both code and proof are empty but verified, still succeeds."""
        mock_output = VerificationOutput(
            code="",
            proof="",
            verified=True,
            iterations=1,
            certificate=None,
            backend="lean4",
            language="python",
        )

        with (
            patch("vericode.models.get_provider", return_value=AsyncMock()),
            patch(
                "vericode.verifier.verify",
                new_callable=AsyncMock,
                return_value=mock_output,
            ),
        ):
            result = runner.invoke(main, ["verify", "do something"])
            assert result.exit_code == 0
