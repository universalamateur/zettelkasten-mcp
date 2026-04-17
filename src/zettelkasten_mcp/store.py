"""ChromaDB wrapper: upsert notes with embeddings, query, and report stats.

Chroma metadata values must be scalars, so tags are stored as a pipe-delimited
blob (``|tag-a|tag-b|``). Metadata filters available server-side:

* ``type`` — exact match
* ``updated_iso`` — ``$gte`` for the ``since`` filter

Tag filtering (require all) is applied client-side after the initial vector
query, which keeps metadata lean and is cheap at Zettelkasten scales.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from zettelkasten_mcp.config import Settings
from zettelkasten_mcp.models import Note, SearchResult

_COLLECTION = "vault"
_SNIPPET_LEN = 400


def _tags_to_blob(tags: list[str]) -> str:
    return "|" + "|".join(tags) + "|" if tags else "||"


def _blob_to_tags(blob: str) -> list[str]:
    return [t for t in blob.split("|") if t]


class ChromaStore:
    """Thin facade over a ChromaDB persistent collection."""

    def __init__(self, settings: Settings, *, client: ClientAPI | None = None) -> None:
        self._client: ClientAPI = client or chromadb.PersistentClient(path=str(settings.chroma_path))
        self._collection: Collection = self._client.get_or_create_collection(name=_COLLECTION)

    # --- write path ---------------------------------------------------------

    def upsert(self, note: Note, embedding: list[float]) -> None:
        """Insert or replace a note's vector and metadata."""
        self._collection.upsert(
            ids=[note.id],
            embeddings=[embedding],
            documents=[note.body[:_SNIPPET_LEN]],
            metadatas=[self._metadata(note)],
        )

    def delete(self, note_id: str) -> None:
        """Remove a note from the index."""
        self._collection.delete(ids=[note_id])

    def get_hash(self, note_id: str) -> str | None:
        """Return the stored ``content_hash`` for a note, or ``None`` if absent."""
        result = self._collection.get(ids=[note_id], include=["metadatas"])
        metas = result.get("metadatas") or []
        if not metas:
            return None
        return metas[0].get("content_hash")  # type: ignore[return-value]

    # --- read path ----------------------------------------------------------

    def query(
        self,
        embedding: list[float],
        *,
        type_: str | None = None,
        tags: list[str] | None = None,
        since: date | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Semantic search with optional metadata filters."""
        where = self._build_where(type_=type_, since=since)

        # Overfetch so client-side tag filtering can still return ``limit`` items.
        fetch_n = limit * 5 if tags else limit
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=fetch_n,
            where=where or None,
            include=["metadatas", "documents", "distances"],
        )

        ids = (result.get("ids") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]

        hits: list[SearchResult] = []
        for note_id, meta, doc, dist in zip(ids, metas, docs, dists, strict=False):
            note_tags = _blob_to_tags(meta.get("tags_blob", ""))
            if tags and not set(tags).issubset(note_tags):
                continue
            hits.append(
                SearchResult(
                    id=note_id,
                    type=str(meta.get("type", "")),
                    tags=note_tags,
                    score=float(dist),
                    snippet=doc or "",
                    path=str(meta.get("path", "")),
                )
            )
            if len(hits) >= limit:
                break
        return hits

    def stats(self) -> tuple[int, dict[str, int], dict[str, int]]:
        """Return ``(total, by_type, by_tag)`` for a :class:`StatusReport`."""
        result = self._collection.get(include=["metadatas"])
        metas: list[dict[str, Any]] = result.get("metadatas") or []
        by_type: dict[str, int] = {}
        by_tag: dict[str, int] = {}
        for meta in metas:
            note_type = str(meta.get("type", "unknown"))
            by_type[note_type] = by_type.get(note_type, 0) + 1
            for tag in _blob_to_tags(meta.get("tags_blob", "")):
                by_tag[tag] = by_tag.get(tag, 0) + 1
        return len(metas), by_type, by_tag

    def indexed_ids(self) -> set[str]:
        """Return the set of currently indexed note IDs."""
        result = self._collection.get(include=[])
        return set(result.get("ids") or [])

    # --- helpers ------------------------------------------------------------

    @staticmethod
    def _metadata(note: Note) -> dict[str, Any]:
        return {
            "type": note.type if isinstance(note.type, str) else note.type.value,
            "tags_blob": _tags_to_blob(note.tags),
            "created_iso": note.created.isoformat(),
            "updated_iso": (note.updated or note.created).isoformat(),
            "source": note.source,
            "path": str(note.path),
            "content_hash": note.content_hash,
        }

    @staticmethod
    def _build_where(*, type_: str | None, since: date | None) -> dict[str, Any]:
        clauses: list[dict[str, Any]] = []
        if type_:
            clauses.append({"type": type_})
        if since:
            clauses.append({"updated_iso": {"$gte": since.isoformat()}})
        if not clauses:
            return {}
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}
