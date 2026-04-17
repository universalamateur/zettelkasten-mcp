"""Tests for :mod:`zettelkasten_mcp.server`.

Focus is on :func:`run_ingest` — the reusable pipeline that backs both the
``ingest`` MCP tool and the ``zettelkasten-mcp ingest`` CLI command. Tests run
against an in-memory Chroma client and a patched Ollama client so no external
services are required.

Covers:

* First-run ingest across the default sample vault (expect 7 indexed).
* Incremental ingest: second run with unchanged files is a no-op.
* ``full=True`` re-embeds every file regardless of hash.
* Edits are detected via content_hash and counted as ``updated``.
* Orphan deletion: files removed from disk are dropped from the index.
* Invalid notes are reported in ``errors`` and counted as ``skipped``.
* ``last_ingest.json`` is written after every run.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from zettelkasten_mcp.config import Settings
from zettelkasten_mcp.server import run_ingest
from zettelkasten_mcp.store import ChromaStore


def _copy_vault(src: Path, dst: Path) -> Path:
    """Copy the sample vault to a writable temp location."""
    shutil.copytree(src, dst)
    return dst


def _store(settings: Settings, chroma_client) -> ChromaStore:  # type: ignore[no-untyped-def]
    return ChromaStore(settings, client=chroma_client)


def _writable_settings(sample_vault: Path, tmp_path: Path) -> Settings:
    vault_copy = _copy_vault(sample_vault, tmp_path / "vault")
    return Settings(vault_path=vault_copy, chroma_path=tmp_path / "chroma")  # type: ignore[call-arg]


@pytest.mark.usefixtures("patched_ollama")
def test_run_ingest_first_pass(sample_vault: Path, tmp_path: Path, chroma_client) -> None:  # type: ignore[no-untyped-def]
    s = _writable_settings(sample_vault, tmp_path)
    store = _store(s, chroma_client)

    report = run_ingest(s, store, full=False)

    assert report.indexed == 7, report
    assert report.updated == 0
    assert report.skipped == 0
    assert report.errors == []
    assert store.indexed_ids() == {
        "atomic-notes",
        "semantic-search",
        "ollama-embeddings",
        "chromadb-basics",
        "ahrens-2017-how-to-take-smart-notes",
        "kleppmann-2019-local-first-software",
        "rag-pipeline",
    }


@pytest.mark.usefixtures("patched_ollama")
def test_run_ingest_is_incremental(sample_vault: Path, tmp_path: Path, chroma_client) -> None:  # type: ignore[no-untyped-def]
    s = _writable_settings(sample_vault, tmp_path)
    store = _store(s, chroma_client)

    run_ingest(s, store, full=False)
    second = run_ingest(s, store, full=False)

    # Nothing changed on disk → nothing to do.
    assert second.indexed == 0
    assert second.updated == 0
    assert second.skipped == 0
    assert second.errors == []


@pytest.mark.usefixtures("patched_ollama")
def test_run_ingest_full_rebuilds_everything(
    sample_vault: Path, tmp_path: Path, chroma_client
) -> None:  # type: ignore[no-untyped-def]
    s = _writable_settings(sample_vault, tmp_path)
    store = _store(s, chroma_client)

    run_ingest(s, store, full=False)
    rebuild = run_ingest(s, store, full=True)

    # full=True ignores hashes — everything is re-embedded and counted as
    # ``updated`` (existing_hash is None from run_ingest's perspective, so it
    # falls through the ``existing_hash is None`` branch and counts as
    # indexed). We accept either interpretation because both semantically
    # reflect "touched every file".
    assert rebuild.indexed + rebuild.updated == 7
    assert rebuild.errors == []


@pytest.mark.usefixtures("patched_ollama")
def test_run_ingest_detects_edits(sample_vault: Path, tmp_path: Path, chroma_client) -> None:  # type: ignore[no-untyped-def]
    s = _writable_settings(sample_vault, tmp_path)
    store = _store(s, chroma_client)

    run_ingest(s, store, full=False)

    # Edit one file so its content_hash changes.
    target = s.vault_path / "notes" / "atomic-notes.md"
    target.write_text(target.read_text(encoding="utf-8") + "\n\nEdit.\n", encoding="utf-8")

    report = run_ingest(s, store, full=False)
    assert report.updated == 1
    assert report.indexed == 0
    assert report.errors == []


@pytest.mark.usefixtures("patched_ollama")
def test_run_ingest_removes_orphans(sample_vault: Path, tmp_path: Path, chroma_client) -> None:  # type: ignore[no-untyped-def]
    s = _writable_settings(sample_vault, tmp_path)
    store = _store(s, chroma_client)

    run_ingest(s, store, full=False)
    assert "atomic-notes" in store.indexed_ids()

    # Delete a file on disk and run again.
    (s.vault_path / "notes" / "atomic-notes.md").unlink()
    run_ingest(s, store, full=False)

    assert "atomic-notes" not in store.indexed_ids()
    assert len(store.indexed_ids()) == 6


@pytest.mark.usefixtures("patched_ollama")
def test_run_ingest_skips_invalid_notes(
    sample_vault: Path, tmp_path: Path, chroma_client
) -> None:  # type: ignore[no-untyped-def]
    s = _writable_settings(sample_vault, tmp_path)

    # Drop a bad-frontmatter file into ``notes/`` where it will be picked up.
    bad = s.vault_path / "notes" / "broken.md"
    bad.write_text("---\nid: broken\ntype: fleeting\n---\nbroken\n", encoding="utf-8")

    store = _store(s, chroma_client)
    report = run_ingest(s, store, full=False)

    assert report.skipped == 1
    assert any("broken.md" in err for err in report.errors)
    # Valid notes still indexed normally.
    assert report.indexed == 7


@pytest.mark.usefixtures("patched_ollama")
def test_run_ingest_writes_last_ingest(
    sample_vault: Path, tmp_path: Path, chroma_client
) -> None:  # type: ignore[no-untyped-def]
    s = _writable_settings(sample_vault, tmp_path)
    store = _store(s, chroma_client)

    run_ingest(s, store, full=False)

    marker = s.chroma_path / "last_ingest.json"
    assert marker.exists()
    payload = json.loads(marker.read_text(encoding="utf-8"))
    assert "timestamp" in payload
