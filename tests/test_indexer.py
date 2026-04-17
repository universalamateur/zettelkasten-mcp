"""Tests for :mod:`zettelkasten_mcp.indexer`.

Covers:

* ``compute_hash`` is stable and differs on any change.
* ``strip_markdown`` yields plain text for headings, paragraphs, inline
  formatting, and code blocks/fences (those are kept for embedding).
* ``parse_note`` succeeds on every note in the sample vault.
* ``parse_note`` raises :class:`InvalidNote` with a specific reason for each
  edge-case fixture.
* ``iter_vault_files`` respects ``index_dirs`` / ``skip_dirs``.
* ``embed_text`` uses the (patched) Ollama client.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from zettelkasten_mcp.config import Settings
from zettelkasten_mcp.indexer import (
    InvalidNote,
    compute_hash,
    embed_text,
    iter_vault_files,
    parse_note,
    strip_markdown,
)
from zettelkasten_mcp.models import NoteType


# --- compute_hash ----------------------------------------------------------


def test_compute_hash_is_stable() -> None:
    assert compute_hash("hello") == compute_hash("hello")


def test_compute_hash_differs_on_change() -> None:
    assert compute_hash("hello") != compute_hash("hello ")


# --- strip_markdown --------------------------------------------------------


def test_strip_markdown_removes_syntax() -> None:
    text = "# Heading\n\nThis is *emphasis* and **bold**. Plain text."
    out = strip_markdown(text)
    assert "Heading" in out
    assert "emphasis" in out
    assert "bold" in out
    assert "#" not in out
    assert "**" not in out


def test_strip_markdown_keeps_inline_code() -> None:
    out = strip_markdown("Call `parse_note(path)` here.")
    assert "parse_note(path)" in out


def test_strip_markdown_keeps_fenced_code() -> None:
    text = "Intro paragraph.\n\n```python\ndef f():\n    return 1\n```\n"
    out = strip_markdown(text)
    assert "def f():" in out
    assert "Intro paragraph." in out


# --- parse_note: sample vault ---------------------------------------------


def test_parse_all_sample_notes(sample_vault: Path) -> None:
    """Every real note in the sample vault parses cleanly."""
    for sub in ("notes", "literature", "indexes"):
        for md in (sample_vault / sub).rglob("*.md"):
            note = parse_note(md)
            assert note.id == md.stem
            assert note.tags, "tags must be non-empty per schema"
            assert note.content_hash, "content_hash must be populated"
            assert isinstance(note.type, str)  # enum is dumped to str


def test_parse_note_includes_content_hash(sample_vault: Path) -> None:
    path = sample_vault / "notes" / "atomic-notes.md"
    note = parse_note(path)
    assert note.content_hash == compute_hash(path.read_text(encoding="utf-8"))


def test_parse_note_body_is_stripped(sample_vault: Path) -> None:
    note = parse_note(sample_vault / "notes" / "atomic-notes.md")
    assert "---" not in note.body
    assert not note.body.lstrip().startswith("#")


# --- parse_note: edge cases -----------------------------------------------


def test_parse_note_no_frontmatter(edge_cases_dir: Path) -> None:
    with pytest.raises(InvalidNote) as err:
        parse_note(edge_cases_dir / "no-frontmatter.md")
    assert "missing frontmatter" in err.value.reason


def test_parse_note_missing_required(edge_cases_dir: Path) -> None:
    with pytest.raises(InvalidNote) as err:
        parse_note(edge_cases_dir / "missing-required.md")
    assert "missing required fields" in err.value.reason
    assert "tags" in err.value.reason


def test_parse_note_invalid_type(edge_cases_dir: Path) -> None:
    with pytest.raises(InvalidNote) as err:
        parse_note(edge_cases_dir / "invalid-type.md")
    assert err.value.reason.startswith("invalid type")


def test_parse_note_bad_date(edge_cases_dir: Path) -> None:
    with pytest.raises(InvalidNote) as err:
        parse_note(edge_cases_dir / "bad-date.md")
    assert err.value.reason.startswith("invalid created")


def test_parse_note_empty_tags(edge_cases_dir: Path) -> None:
    with pytest.raises(InvalidNote) as err:
        parse_note(edge_cases_dir / "empty-tags.md")
    # Pydantic surfaces this as a schema validation error on min_length.
    assert "schema validation failed" in err.value.reason


# --- iter_vault_files -----------------------------------------------------


def test_iter_vault_files_default_dirs(settings: Settings) -> None:
    files = list(iter_vault_files(settings))
    rels = sorted(str(p.relative_to(settings.vault_path)) for p in files)
    # 4 permanent + 2 literature + 1 index = 7
    assert len(rels) == 7, rels
    assert not any(r.startswith("journals/") for r in rels)
    assert not any(r.startswith("projects/") for r in rels)


def test_iter_vault_files_includes_projects_when_opted_in(
    sample_vault: Path, tmp_path: Path
) -> None:
    s = Settings(
        vault_path=sample_vault,
        chroma_path=tmp_path / "chroma",
        index_dirs=["notes", "literature", "indexes", "projects"],  # type: ignore[arg-type]
    )  # type: ignore[call-arg]
    files = list(iter_vault_files(s))
    assert any("projects/" in str(p) for p in files)


def test_iter_vault_files_skip_dirs(sample_vault: Path, tmp_path: Path) -> None:
    """Adding ``notes`` to skip_dirs drops the entire ``notes`` subtree."""
    s = Settings(
        vault_path=sample_vault,
        chroma_path=tmp_path / "chroma",
        skip_dirs=["journals", "notes"],  # type: ignore[arg-type]
    )  # type: ignore[call-arg]
    files = list(iter_vault_files(s))
    assert not any("/notes/" in str(p) for p in files)
    assert any("literature/" in str(p) for p in files)


def test_iter_vault_files_missing_index_dir(sample_vault: Path, tmp_path: Path) -> None:
    """A non-existent entry in ``index_dirs`` is silently skipped."""
    s = Settings(
        vault_path=sample_vault,
        chroma_path=tmp_path / "chroma",
        index_dirs=["notes", "does-not-exist"],  # type: ignore[arg-type]
    )  # type: ignore[call-arg]
    files = list(iter_vault_files(s))
    assert len(files) == 4


# --- embed_text -----------------------------------------------------------


def test_embed_text_uses_patched_ollama(settings: Settings, patched_ollama) -> None:  # noqa: ARG001
    vec = embed_text("hello world", settings)
    assert len(vec) == 384
    assert all(isinstance(v, float) for v in vec)


def test_embed_text_is_deterministic(settings: Settings, patched_ollama) -> None:  # noqa: ARG001
    assert embed_text("same prompt", settings) == embed_text("same prompt", settings)


def test_parsed_note_type_is_valid_enum_value(sample_vault: Path) -> None:
    """Every parsed note's ``type`` is one of the enum values."""
    valid = {t.value for t in NoteType}
    for sub in ("notes", "literature", "indexes"):
        for md in (sample_vault / sub).rglob("*.md"):
            note = parse_note(md)
            assert note.type in valid
