"""Tests for :mod:`zettelkasten_mcp.cli`.

Uses ``typer.testing.CliRunner`` to drive the Typer app without a subprocess.

Covers:

* ``version`` prints the installed version and exits cleanly.
* ``--help`` lists every registered subcommand.
* ``ingest --vault PATH`` runs the ingest pipeline against ``PATH`` and emits
  a JSON :class:`IngestReport`.
* ``status --vault PATH`` emits a JSON :class:`StatusReport` with the expected
  totals against the sample vault.
* The ``--vault`` option sets ``ZETTELKASTEN_VAULT_PATH`` for the duration of
  the subcommand.

The ``patched_ollama`` fixture is used wherever the pipeline would otherwise
hit the network; Chroma state is kept in an ephemeral temp directory via
``tmp_path``.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from zettelkasten_mcp import __version__
from zettelkasten_mcp.cli import app

runner = CliRunner()


def _copy_vault(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst)
    return dst


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help_lists_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("version", "serve", "ingest", "status"):
        assert cmd in result.stdout


@pytest.mark.usefixtures("patched_ollama")
def test_ingest_with_vault_option(
    sample_vault: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault_copy = _copy_vault(sample_vault, tmp_path / "vault")
    monkeypatch.setenv("ZETTELKASTEN_CHROMA_PATH", str(tmp_path / "chroma"))

    result = runner.invoke(app, ["ingest", "--vault", str(vault_copy), "--full"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["indexed"] == 7
    assert payload["errors"] == []


@pytest.mark.usefixtures("patched_ollama")
def test_status_reports_expected_totals(
    sample_vault: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault_copy = _copy_vault(sample_vault, tmp_path / "vault")
    monkeypatch.setenv("ZETTELKASTEN_CHROMA_PATH", str(tmp_path / "chroma"))

    # Seed the index before asking for status.
    ingest_result = runner.invoke(app, ["ingest", "--vault", str(vault_copy), "--full"])
    assert ingest_result.exit_code == 0, ingest_result.stdout

    status_result = runner.invoke(app, ["status", "--vault", str(vault_copy)])
    assert status_result.exit_code == 0, status_result.stdout

    payload = json.loads(status_result.stdout)
    assert payload["total_indexed"] == 7
    assert payload["by_type"] == {"permanent": 4, "literature": 2, "index": 1}
    assert payload["coverage_gaps"] == []


def test_ingest_without_vault_uses_env(
    sample_vault: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, patched_ollama  # noqa: ARG001
) -> None:
    """Without ``--vault``, the CLI falls back to ``ZETTELKASTEN_VAULT_PATH``."""
    vault_copy = _copy_vault(sample_vault, tmp_path / "vault")
    monkeypatch.setenv("ZETTELKASTEN_VAULT_PATH", str(vault_copy))
    monkeypatch.setenv("ZETTELKASTEN_CHROMA_PATH", str(tmp_path / "chroma"))

    result = runner.invoke(app, ["ingest", "--full"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["indexed"] == 7
