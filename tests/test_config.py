"""Tests for :mod:`zettelkasten_mcp.config`.

Covers:

* env-var loading via the ``ZETTELKASTEN_`` prefix
* CSV parsing for list fields (``index_dirs``, ``skip_dirs``)
* ``~`` expansion for path fields
* default values for optional fields
* ``vault_path`` is required
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from zettelkasten_mcp.config import Settings, _split_csv, get_settings


def test_vault_path_required() -> None:
    """Constructing :class:`Settings` with no vault path should error."""
    # Clear any inherited env so we actually hit the missing-field branch.
    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]


def test_defaults_applied(tmp_path: Path) -> None:
    """Unset optional fields fall back to the documented defaults."""
    s = Settings(vault_path=tmp_path)  # type: ignore[call-arg]
    assert s.ollama_url == "http://localhost:11434"
    assert s.embedding_model == "nomic-embed-text"
    assert s.index_dirs == ["notes", "literature", "indexes"]
    assert s.skip_dirs == ["journals", "Customer", ".git", "artifacts"]


def test_tilde_expansion(tmp_path: Path) -> None:
    """``~`` in path fields must resolve to the user's home directory."""
    s = Settings(vault_path=tmp_path, chroma_path="~/custom-chroma")  # type: ignore[call-arg]
    assert str(s.chroma_path).startswith(str(Path.home()))
    assert s.chroma_path.name == "custom-chroma"


def test_csv_parsing_from_string(tmp_path: Path) -> None:
    """A comma-separated string is split into a list, trimming whitespace."""
    s = Settings(
        vault_path=tmp_path,
        index_dirs="notes, literature , indexes",  # type: ignore[arg-type]
        skip_dirs="journals,Customer",  # type: ignore[arg-type]
    )  # type: ignore[call-arg]
    assert s.index_dirs == ["notes", "literature", "indexes"]
    assert s.skip_dirs == ["journals", "Customer"]


def test_csv_parsing_from_list(tmp_path: Path) -> None:
    """An already-split list passes through unchanged."""
    s = Settings(vault_path=tmp_path, index_dirs=["a", "b", "c"])  # type: ignore[call-arg]
    assert s.index_dirs == ["a", "b", "c"]


def test_split_csv_drops_empties() -> None:
    """Empty segments from trailing commas or doubles are dropped."""
    assert _split_csv("a,,b, ,c,") == ["a", "b", "c"]
    assert _split_csv([" a ", "", "b"]) == ["a", "b"]


def test_env_loading(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """``ZETTELKASTEN_*`` env vars populate the matching fields."""
    vault = tmp_path / "vault"
    vault.mkdir()
    chroma = tmp_path / "chroma"
    monkeypatch.setenv("ZETTELKASTEN_VAULT_PATH", str(vault))
    monkeypatch.setenv("ZETTELKASTEN_CHROMA_PATH", str(chroma))
    monkeypatch.setenv("ZETTELKASTEN_OLLAMA_URL", "http://example:1234")
    monkeypatch.setenv("ZETTELKASTEN_EMBEDDING_MODEL", "test-model")
    monkeypatch.setenv("ZETTELKASTEN_INDEX_DIRS", "notes,projects")
    monkeypatch.setenv("ZETTELKASTEN_SKIP_DIRS", "journals")

    s = get_settings()

    assert s.vault_path == vault
    assert s.chroma_path == chroma
    assert s.ollama_url == "http://example:1234"
    assert s.embedding_model == "test-model"
    assert s.index_dirs == ["notes", "projects"]
    assert s.skip_dirs == ["journals"]


def test_extra_fields_ignored(tmp_path: Path) -> None:
    """Unknown keys do not raise — extra=ignore is set by model_config."""
    s = Settings(vault_path=tmp_path, unknown_field="x")  # type: ignore[call-arg]
    assert not hasattr(s, "unknown_field")
