"""FastMCP server exposing search, ingest, and status tools."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from zettelkasten_mcp import __version__
from zettelkasten_mcp.config import Settings, get_settings
from zettelkasten_mcp.indexer import InvalidNote, embed_text, iter_vault_files, parse_note
from zettelkasten_mcp.models import CoverageGap, IngestReport, SearchResult, StatusReport
from zettelkasten_mcp.store import ChromaStore

mcp: FastMCP = FastMCP("zettelkasten-mcp")

_LAST_INGEST_FILE = "last_ingest.json"


# ---------------------------------------------------------------------------
# lazy, process-local settings and store so tools can be called independently
# ---------------------------------------------------------------------------


_settings: Settings | None = None
_store: ChromaStore | None = None


def _get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings


def _get_store() -> ChromaStore:
    global _store
    if _store is None:
        _store = ChromaStore(_get_settings())
    return _store


def _last_ingest_path(settings: Settings) -> Path:
    return settings.chroma_path / _LAST_INGEST_FILE


def _read_last_ingest(settings: Settings) -> datetime | None:
    path = _last_ingest_path(settings)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return datetime.fromisoformat(payload["timestamp"])
    except (KeyError, ValueError, OSError):
        return None


def _write_last_ingest(settings: Settings, moment: datetime) -> None:
    path = _last_ingest_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"timestamp": moment.isoformat()}), encoding="utf-8")


# ---------------------------------------------------------------------------
# core ingest pipeline (library function, also reused by the CLI)
# ---------------------------------------------------------------------------


def run_ingest(settings: Settings, store: ChromaStore, *, full: bool = False) -> IngestReport:
    """Walk the vault, (re)index changed notes, remove orphans, return a report.

    ``full=True`` ignores stored hashes and re-embeds every file. Orphaned IDs
    (in Chroma but no longer on disk) are always deleted.
    """
    report = IngestReport()
    seen_ids: set[str] = set()

    for path in iter_vault_files(settings):
        try:
            note = parse_note(path)
        except InvalidNote as exc:
            report.skipped += 1
            report.errors.append(str(exc))
            continue
        except OSError as exc:
            report.errors.append(f"{path}: {exc}")
            continue

        seen_ids.add(note.id)
        existing_hash = None if full else store.get_hash(note.id)
        if existing_hash == note.content_hash:
            continue

        try:
            embedding = embed_text(note.body, settings)
            store.upsert(note, embedding)
        except Exception as exc:  # noqa: BLE001 - surface any embed/store failure in report
            report.errors.append(f"{path}: {exc.__class__.__name__}: {exc}")
            continue

        if existing_hash is None:
            report.indexed += 1
        else:
            report.updated += 1

    # Remove orphans: IDs in the store that were not seen this pass.
    orphans = store.indexed_ids() - seen_ids
    for orphan_id in orphans:
        store.delete(orphan_id)

    _write_last_ingest(settings, datetime.now())
    return report


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool
def search(
    query: str,
    tags: list[str] | None = None,
    type: str | None = None,
    since: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Semantic search over the indexed vault.

    Args:
        query: Natural-language query text.
        tags: Require all listed tags on returned notes.
        type: Filter by note type (permanent, literature, project, index).
        since: ISO date (YYYY-MM-DD); only notes updated on/after this date.
        limit: Maximum results to return (default 10).

    Returns:
        Ranked list of matches with id, type, tags, score, snippet, path.
    """
    settings = _get_settings()
    store = _get_store()

    since_date: date | None = None
    if since:
        try:
            since_date = date.fromisoformat(since)
        except ValueError as exc:
            raise ToolError(f"invalid since date: {since!r}") from exc

    try:
        embedding = embed_text(query, settings)
    except Exception as exc:  # noqa: BLE001
        raise ToolError(f"embedding failed: {exc}") from exc

    results: list[SearchResult] = store.query(
        embedding,
        type_=type,
        tags=tags,
        since=since_date,
        limit=limit,
    )
    return [r.model_dump() for r in results]


@mcp.tool
def ingest(path: str | None = None, full: bool = False) -> dict:
    """Run an incremental ingest, or a full reindex when ``full`` is true.

    Args:
        path: Reserved for future use (single-file / directory ingest).
        full: If true, rebuild the entire index.

    Returns:
        IngestReport with indexed / updated / skipped counts and any errors.
    """
    if path is not None:
        raise ToolError("path-scoped ingest is not implemented yet; use full=true for now")
    report = run_ingest(_get_settings(), _get_store(), full=full)
    return report.model_dump()


@mcp.tool
def status() -> dict:
    """Report index health, counts by type/tag, and coverage gaps.

    Returns:
        StatusReport with total_indexed, last_ingest, by_type, by_tag, coverage_gaps.
    """
    settings = _get_settings()
    store = _get_store()

    total, by_type, by_tag = store.stats()
    indexed_ids = store.indexed_ids()

    gaps: list[CoverageGap] = []
    for note_path in iter_vault_files(settings):
        try:
            note = parse_note(note_path)
        except InvalidNote as exc:
            gaps.append(CoverageGap(path=str(note_path), reason=f"parse-error: {exc.reason}"))
            continue
        except OSError as exc:
            gaps.append(CoverageGap(path=str(note_path), reason=f"read-error: {exc}"))
            continue
        if note.id not in indexed_ids:
            gaps.append(CoverageGap(path=str(note_path), reason="unindexed"))

    report = StatusReport(
        total_indexed=total,
        last_ingest=_read_last_ingest(settings),
        by_type=by_type,
        by_tag=by_tag,
        coverage_gaps=gaps,
    )
    return report.model_dump(mode="json")


@mcp.tool
def health_check() -> str:
    """Return a simple liveness string with the server version."""
    return f"OK (zettelkasten-mcp v{__version__})"


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Start the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
