# Architecture

Six narrow modules. Each has one job. Layers only depend downward.

```
cli.py ──────────────────────┐
                             ▼
                         server.py ◀── MCP stdio transport
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
          indexer.py     store.py       models.py
              │              │              ▲
              ▼              ▼              │
         ollama / fs   chromadb      (Pydantic types)
                             │
                             ▼
                         config.py (Settings)
```

## Module responsibilities

### `config.py`

Pydantic `Settings` — single source of runtime config. Loads from
environment variables (prefix `ZETTELKASTEN_`) with optional `.env`. Validators
expand `~` on path fields and split CSV strings into lists for the
`index_dirs` / `skip_dirs` fields. Exposes `get_settings()` which is the
only entry point.

### `models.py`

Pure data classes. No I/O, no config reads.

* `NoteType` — `permanent | literature | project | index`
* `Note` — parsed markdown file with frontmatter, body, path, content_hash
* `SearchResult` — one row returned by `search`
* `IngestReport` — counts + errors from `ingest`
* `CoverageGap`, `StatusReport` — health output from `status`

### `indexer.py`

Pure transformations. No network side effects except `embed_text`:

* `compute_hash(raw)` — SHA-256 of raw file contents. Drives incremental
  ingest.
* `strip_markdown(text)` — markdown-it-py token stream; keeps text, inline
  code, and code fences; drops heading/emphasis/link syntax. Output is what
  the embedding model sees.
* `parse_note(path)` — read file → split frontmatter → validate required
  fields → coerce types → build `Note`. Raises `InvalidNote(path, reason)`
  on any failure with a specific, stable reason string.
* `iter_vault_files(settings)` — walks `settings.index_dirs` under
  `settings.vault_path`, drops any path whose relative segments hit
  `settings.skip_dirs`. Missing `index_dirs` entries are silently skipped.
* `embed_text(text, settings)` — one Ollama HTTP call per invocation.

### `store.py`

Thin facade over a persistent ChromaDB collection. Tags are stored as a
pipe-delimited blob (`|a|b|c|`) in metadata because Chroma only accepts
scalar metadata values.

* `upsert(note, embedding)` — idempotent by `note.id`.
* `get_hash(note_id)` — read the stored `content_hash` for incremental
  ingest decisions. `None` if the id is absent.
* `delete(note_id)` — remove one id.
* `query(embedding, type_, tags, since, limit)` — vector search. `type`
  and `since` translate to server-side Chroma metadata filters; `tags`
  filtering is client-side (set subset check) after overfetching `limit*5`
  candidates.
* `stats()` — returns `(total, by_type, by_tag)` by scanning all metadata.
* `indexed_ids()` — id set, used for orphan detection.

The constructor accepts an explicit `client` kwarg; tests inject
`chromadb.EphemeralClient()` here.

### `server.py`

Wires everything together. Module-level `_settings` / `_store` are lazy
singletons so MCP tool invocations don't re-open Chroma on every call.

`run_ingest(settings, store, full)` is the reusable pipeline — both the
`ingest` MCP tool and the `zettelkasten-mcp ingest` CLI call it:

1. For each file from `iter_vault_files`:
   - `parse_note(path)` → on `InvalidNote`, count `skipped` and record the
     reason in `errors`.
   - Compare `note.content_hash` against `store.get_hash(note.id)`. Equal
     and `not full` → skip.
   - `embed_text(note.body, settings)` → `store.upsert(note, embedding)`.
   - Classify as `indexed` (new id) or `updated` (hash changed).
2. `store.indexed_ids() - seen_ids` → orphan deletion.
3. Write `last_ingest.json` under `settings.chroma_path`.

MCP tools:

* `search` — wraps `embed_text` + `store.query`.
* `ingest` — wraps `run_ingest`.
* `status` — combines `store.stats()` with a walk of the vault to surface
  coverage gaps.
* `health_check` — returns version string; no side effects.

### `cli.py`

Typer subcommands: `version`, `serve`, `ingest`, `status`. Imports server
module lazily per-command so `--help` stays fast. `--vault PATH` overrides
`ZETTELKASTEN_VAULT_PATH` for the current invocation.

## Cross-cutting decisions

### Incremental ingest via content hash

Git is not a dependency. `compute_hash(raw_file_bytes)` produces a stable
SHA-256 that changes on any byte-level edit. That's sufficient signal for
"does this need to be re-embedded?" and keeps the tool usable on non-git
vaults.

### Tags in a pipe-delimited blob

Chroma metadata must be scalar. A list of strings can't be persisted natively.
Storing `|tag-a|tag-b|` and doing client-side subset checks keeps
implementation simple and is fast enough — a Zettelkasten is thousands of
notes, not millions, so overfetching `limit*5` and filtering in Python is
negligible.

### Module-level caches reset between tests

`server._settings` / `_store` are cached for production performance. The test
suite autouses a fixture that resets them before and after every test so
settings changes via `monkeypatch.setenv` actually take effect.

### No hidden I/O

* `config.py` reads env / `.env`. That is its job.
* `indexer.embed_text` is the only function that calls Ollama.
* `store.py` is the only module that touches Chroma.
* Everything else is pure.

This keeps each module independently testable and makes failure attribution
trivial — a broken embedding path can only live in `indexer.embed_text`; a
broken persistence call can only live in `store.py`.
