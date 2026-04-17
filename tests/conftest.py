"""Shared pytest fixtures for the zettelkasten-mcp test suite.

Fixtures here avoid any network or on-disk side effects:

* ``sample_vault`` points at the synthetic vault checked into
  ``tests/fixtures/sample_vault``.
* ``edge_cases_dir`` points at files designed to exercise every failure branch
  in :func:`zettelkasten_mcp.indexer.parse_note`.
* ``settings`` yields a :class:`Settings` configured against the sample vault
  with a fresh per-test Chroma path under ``tmp_path``.
* ``chroma_client`` yields an in-memory Chroma instance that is thrown away
  after each test.
* ``patched_ollama`` monkey-patches :class:`ollama.Client` so every embedding
  call returns a deterministic 384-dim pseudo-random vector — no network
  traffic, no models required.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import chromadb
import pytest

from zettelkasten_mcp.config import Settings

FIXTURES = Path(__file__).parent / "fixtures"
EMBED_DIM = 384


@pytest.fixture
def sample_vault() -> Path:
    """Absolute path to the synthetic sample vault."""
    return FIXTURES / "sample_vault"


@pytest.fixture
def edge_cases_dir() -> Path:
    """Directory of frontmatter edge-case files."""
    return FIXTURES / "edge_cases"


@pytest.fixture
def settings(sample_vault: Path, tmp_path: Path) -> Settings:
    """Settings bound to the sample vault with a disposable Chroma path."""
    return Settings(
        vault_path=sample_vault,
        chroma_path=tmp_path / "chroma",
    )  # type: ignore[call-arg]


@pytest.fixture
def chroma_client() -> Iterator[chromadb.api.ClientAPI]:
    """Ephemeral (in-memory) ChromaDB client; discarded after each test."""
    client = chromadb.EphemeralClient()
    yield client


def _deterministic_embedding(text: str) -> list[float]:
    """Derive a stable pseudo-random vector from a SHA-256 of ``text``.

    Same text → same vector. Different text → different vector. No external
    dependencies. The vector is NOT a meaningful embedding; it only supports
    roundtrip tests of upsert/query/stats.
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [(digest[i % len(digest)] - 128) / 128.0 for i in range(EMBED_DIM)]


class _FakeOllamaClient:
    """Drop-in stand-in for ``ollama.Client`` used by :mod:`indexer`."""

    def __init__(self, host: str | None = None, **_: Any) -> None:
        self.host = host

    def embeddings(self, *, model: str, prompt: str) -> dict[str, list[float]]:
        return {"embedding": _deterministic_embedding(prompt)}


@pytest.fixture
def patched_ollama(monkeypatch: pytest.MonkeyPatch) -> type[_FakeOllamaClient]:
    """Replace ``ollama.Client`` inside :mod:`indexer` with the fake."""
    from zettelkasten_mcp import indexer

    monkeypatch.setattr(indexer.ollama, "Client", _FakeOllamaClient)
    return _FakeOllamaClient


@pytest.fixture
def deterministic_embedding() -> Callable[[str], list[float]]:
    """Expose the embedding helper for tests that bypass the indexer."""
    return _deterministic_embedding


@pytest.fixture(autouse=True)
def _reset_server_module_state() -> Iterator[None]:
    """Clear the module-level settings/store cache in :mod:`server`.

    The server caches ``_settings`` and ``_store`` on first use so that MCP
    tool invocations don't re-open Chroma every call. Inside the test suite
    that cache leaks state across tests, so we reset it around every test.
    """
    from zettelkasten_mcp import server

    server._settings = None
    server._store = None
    yield
    server._settings = None
    server._store = None
