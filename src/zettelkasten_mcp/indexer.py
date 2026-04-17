"""Frontmatter parsing, markdown stripping, vault traversal, and Ollama embedding.

This module holds pure transformations. It does not talk to ChromaDB; wiring
lives in :mod:`zettelkasten_mcp.server`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import frontmatter
import ollama
from markdown_it import MarkdownIt
from pydantic import ValidationError

from zettelkasten_mcp.config import Settings
from zettelkasten_mcp.models import Note, NoteType

_MD = MarkdownIt("commonmark")


class InvalidNote(Exception):
    """Raised when a file cannot be parsed into a valid :class:`Note`."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"{path}: {reason}")


def compute_hash(raw: str) -> str:
    """Return a stable SHA-256 hex digest of raw file contents."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def strip_markdown(text: str) -> str:
    """Strip markdown formatting, preserving plain text and code content.

    Used to produce clean input for the embedding model. Wikilinks and inline
    code are kept as their raw text.
    """
    parts: list[str] = []
    for token in _MD.parse(text):
        if token.type == "inline" and token.children:
            for child in token.children:
                if child.type in ("text", "code_inline"):
                    parts.append(child.content)
        elif token.type in ("code_block", "fence"):
            parts.append(token.content)
    return "\n".join(p for p in parts if p).strip()


def _coerce_date(value: object, field: str, path: Path) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise InvalidNote(path, f"invalid {field}: {value!r}") from exc
    raise InvalidNote(path, f"missing or invalid {field}")


def parse_note(path: Path) -> Note:
    """Parse a single markdown file into a :class:`Note`.

    Raises :class:`InvalidNote` if frontmatter is missing or does not satisfy
    the schema.
    """
    raw = path.read_text(encoding="utf-8")
    post = frontmatter.loads(raw)
    meta = post.metadata or {}
    if not meta:
        raise InvalidNote(path, "missing frontmatter")

    required = ("id", "type", "tags", "created", "source")
    missing = [k for k in required if k not in meta]
    if missing:
        raise InvalidNote(path, f"missing required fields: {', '.join(missing)}")

    try:
        note_type = NoteType(meta["type"])
    except ValueError as exc:
        raise InvalidNote(path, f"invalid type: {meta['type']!r}") from exc

    created = _coerce_date(meta["created"], "created", path)
    updated = _coerce_date(meta["updated"], "updated", path) if meta.get("updated") else None

    try:
        return Note(
            id=str(meta["id"]),
            type=note_type,
            tags=list(meta["tags"]),
            created=created,
            source=str(meta["source"]),
            updated=updated,
            related=list(meta.get("related", []) or []),
            body=strip_markdown(post.content),
            path=path.resolve(),
            content_hash=compute_hash(raw),
        )
    except ValidationError as exc:
        raise InvalidNote(path, f"schema validation failed: {exc.errors()[0]['msg']}") from exc


def iter_vault_files(settings: Settings) -> Iterator[Path]:
    """Yield markdown files under ``settings.vault_path`` respecting index_dirs / skip_dirs.

    ``settings.index_dirs`` acts as an allow-list of vault-relative roots. Any
    path whose first segment is in ``settings.skip_dirs`` is dropped, which
    also covers nested exclusions (e.g. ``notes/artifacts`` if ``artifacts``
    is skipped).
    """
    vault = settings.vault_path
    skip = set(settings.skip_dirs)
    for rel_root in settings.index_dirs:
        root = vault / rel_root
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            rel_parts = path.relative_to(vault).parts
            if any(part in skip for part in rel_parts):
                continue
            yield path


def embed_text(text: str, settings: Settings) -> list[float]:
    """Generate an embedding for ``text`` via Ollama.

    Returns the raw float vector. Dimensionality depends on
    ``settings.embedding_model``.
    """
    client = ollama.Client(host=settings.ollama_url)
    response = client.embeddings(model=settings.embedding_model, prompt=text)
    return list(response["embedding"])
