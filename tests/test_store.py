"""Tests for :mod:`zettelkasten_mcp.store`.

All tests run against an in-memory Chroma instance injected via the
``chroma_client`` fixture — no disk or network side effects.

Covers:

* ``upsert`` + ``get_hash`` round-trip.
* ``upsert`` replaces an existing id (hash and body update).
* ``delete`` removes an id from the index.
* ``query`` applies ``type`` and ``since`` server-side and ``tags`` client-side.
* ``stats`` reports counts by type and by tag.
* ``indexed_ids`` returns the full id set.
* tag blob helpers are symmetric and handle the empty case.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from zettelkasten_mcp.config import Settings
from zettelkasten_mcp.models import Note, NoteType
from zettelkasten_mcp.store import ChromaStore, _blob_to_tags, _tags_to_blob


# --- helpers --------------------------------------------------------------


def _make_note(
    note_id: str,
    *,
    type_: NoteType = NoteType.PERMANENT,
    tags: list[str] | None = None,
    created: date = date(2026, 4, 17),
    updated: date | None = None,
    body: str = "sample body",
) -> Note:
    return Note(
        id=note_id,
        type=type_,
        tags=tags or ["test"],
        created=created,
        source="test",
        updated=updated,
        body=body,
        path=Path(f"/tmp/{note_id}.md"),
        content_hash=f"hash-{note_id}",
    )


def _build_store(settings: Settings, chroma_client) -> ChromaStore:  # type: ignore[no-untyped-def]
    return ChromaStore(settings, client=chroma_client)


# --- blob helpers ----------------------------------------------------------


def test_tag_blob_roundtrip() -> None:
    blob = _tags_to_blob(["zettelkasten", "rag", "ollama"])
    assert blob == "|zettelkasten|rag|ollama|"
    assert _blob_to_tags(blob) == ["zettelkasten", "rag", "ollama"]


def test_tag_blob_empty() -> None:
    assert _tags_to_blob([]) == "||"
    assert _blob_to_tags("||") == []


# --- upsert / get_hash / delete -------------------------------------------


def test_upsert_and_get_hash(settings: Settings, chroma_client, deterministic_embedding) -> None:  # type: ignore[no-untyped-def]
    store = _build_store(settings, chroma_client)
    note = _make_note("a")
    store.upsert(note, deterministic_embedding(note.body))
    assert store.get_hash("a") == "hash-a"


def test_get_hash_returns_none_for_missing(settings: Settings, chroma_client) -> None:  # type: ignore[no-untyped-def]
    store = _build_store(settings, chroma_client)
    assert store.get_hash("does-not-exist") is None


def test_upsert_replaces_existing(settings: Settings, chroma_client, deterministic_embedding) -> None:  # type: ignore[no-untyped-def]
    store = _build_store(settings, chroma_client)
    note = _make_note("a", body="first")
    store.upsert(note, deterministic_embedding(note.body))

    # Mutate hash + body and upsert again; id stays.
    updated = note.model_copy(update={"content_hash": "hash-v2", "body": "second"})
    store.upsert(updated, deterministic_embedding(updated.body))

    assert store.get_hash("a") == "hash-v2"
    assert store.indexed_ids() == {"a"}


def test_delete(settings: Settings, chroma_client, deterministic_embedding) -> None:  # type: ignore[no-untyped-def]
    store = _build_store(settings, chroma_client)
    note = _make_note("a")
    store.upsert(note, deterministic_embedding(note.body))
    assert store.indexed_ids() == {"a"}

    store.delete("a")
    assert store.indexed_ids() == set()
    assert store.get_hash("a") is None


# --- indexed_ids / stats --------------------------------------------------


def test_indexed_ids_and_stats(settings: Settings, chroma_client, deterministic_embedding) -> None:  # type: ignore[no-untyped-def]
    store = _build_store(settings, chroma_client)
    store.upsert(_make_note("n1", type_=NoteType.PERMANENT, tags=["a", "b"]), deterministic_embedding("n1"))
    store.upsert(_make_note("n2", type_=NoteType.PERMANENT, tags=["a"]), deterministic_embedding("n2"))
    store.upsert(_make_note("l1", type_=NoteType.LITERATURE, tags=["c"]), deterministic_embedding("l1"))

    assert store.indexed_ids() == {"n1", "n2", "l1"}

    total, by_type, by_tag = store.stats()
    assert total == 3
    assert by_type == {"permanent": 2, "literature": 1}
    assert by_tag == {"a": 2, "b": 1, "c": 1}


# --- query ---------------------------------------------------------------


def _seed_for_query(store: ChromaStore, embed) -> None:  # type: ignore[no-untyped-def]
    store.upsert(
        _make_note("n1", type_=NoteType.PERMANENT, tags=["rag", "ollama"], body="rag with ollama"),
        embed("rag with ollama"),
    )
    store.upsert(
        _make_note("n2", type_=NoteType.PERMANENT, tags=["zettelkasten"], body="atomic note idea"),
        embed("atomic note idea"),
    )
    store.upsert(
        _make_note(
            "l1",
            type_=NoteType.LITERATURE,
            tags=["rag", "paper"],
            body="retrieval augmented generation paper",
            updated=date(2026, 4, 17),
        ),
        embed("retrieval augmented generation paper"),
    )


def test_query_without_filters_returns_all(
    settings: Settings, chroma_client, deterministic_embedding
) -> None:  # type: ignore[no-untyped-def]
    store = _build_store(settings, chroma_client)
    _seed_for_query(store, deterministic_embedding)

    hits = store.query(deterministic_embedding("anything"), limit=10)
    assert {h.id for h in hits} == {"n1", "n2", "l1"}


def test_query_type_filter(settings: Settings, chroma_client, deterministic_embedding) -> None:  # type: ignore[no-untyped-def]
    store = _build_store(settings, chroma_client)
    _seed_for_query(store, deterministic_embedding)

    hits = store.query(deterministic_embedding("x"), type_="literature", limit=10)
    assert {h.id for h in hits} == {"l1"}
    assert all(h.type == "literature" for h in hits)


def test_query_tags_filter_requires_all(
    settings: Settings, chroma_client, deterministic_embedding
) -> None:  # type: ignore[no-untyped-def]
    store = _build_store(settings, chroma_client)
    _seed_for_query(store, deterministic_embedding)

    # Only notes tagged BOTH ``rag`` AND ``ollama``.
    hits = store.query(deterministic_embedding("x"), tags=["rag", "ollama"], limit=10)
    assert {h.id for h in hits} == {"n1"}


def test_query_since_filter(settings: Settings, chroma_client, deterministic_embedding) -> None:  # type: ignore[no-untyped-def]
    store = _build_store(settings, chroma_client)
    store.upsert(
        _make_note("old", created=date(2025, 1, 1)),
        deterministic_embedding("old"),
    )
    store.upsert(
        _make_note("new", created=date(2026, 4, 17)),
        deterministic_embedding("new"),
    )

    hits = store.query(deterministic_embedding("x"), since=date(2026, 1, 1), limit=10)
    assert {h.id for h in hits} == {"new"}


def test_query_limit_respected(settings: Settings, chroma_client, deterministic_embedding) -> None:  # type: ignore[no-untyped-def]
    store = _build_store(settings, chroma_client)
    _seed_for_query(store, deterministic_embedding)

    hits = store.query(deterministic_embedding("x"), limit=2)
    assert len(hits) == 2


def test_query_snippet_truncated(settings: Settings, chroma_client, deterministic_embedding) -> None:  # type: ignore[no-untyped-def]
    """Snippet must be at most _SNIPPET_LEN characters."""
    from zettelkasten_mcp.store import _SNIPPET_LEN

    store = _build_store(settings, chroma_client)
    long_body = "x" * (_SNIPPET_LEN * 2)
    store.upsert(_make_note("big", body=long_body), deterministic_embedding(long_body))

    hits = store.query(deterministic_embedding("x"), limit=1)
    assert len(hits[0].snippet) <= _SNIPPET_LEN
