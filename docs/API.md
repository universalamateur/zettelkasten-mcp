# API reference — MCP tools

zettelkasten-mcp exposes four tools over stdio via FastMCP. All tools return
plain JSON-serialisable payloads (dicts / lists of dicts). Errors surface as
`ToolError` with a human-readable reason.

---

## `search`

Semantic search over the indexed vault with optional metadata filters.

**Signature**

```python
search(
    query: str,
    tags: list[str] | None = None,
    type: str | None = None,
    since: str | None = None,
    limit: int = 10,
) -> list[dict]
```

**Arguments**

| Name | Type | Purpose |
|---|---|---|
| `query` | `str` | Natural-language query. Embedded via Ollama, compared to stored note vectors by cosine distance. |
| `tags` | `list[str] \| None` | Require every listed tag on returned notes. Applied client-side after vector retrieval. |
| `type` | `str \| None` | Filter by note type (`permanent`, `literature`, `project`, `index`). Server-side filter. |
| `since` | `str \| None` | ISO-8601 date (`YYYY-MM-DD`). Only notes with `updated >= since` are returned. Server-side filter. |
| `limit` | `int` | Maximum rows to return. Default 10. |

**Returns** — list of dicts, each with:

| Field | Type | Meaning |
|---|---|---|
| `id` | `str` | Note id (kebab-case, matches filename without `.md`) |
| `type` | `str` | Note type |
| `tags` | `list[str]` | All tags on the note |
| `score` | `float` | ChromaDB distance — **lower is closer** |
| `snippet` | `str` | First 400 characters of the markdown-stripped body |
| `path` | `str` | Absolute path to the source file |

**Errors** — `ToolError` on malformed `since` date, Ollama unreachable, or embedding failure.

---

## `ingest`

Run the ingest pipeline. Incremental by default (only re-embeds files whose
`content_hash` changed since last ingest); `full=True` re-embeds everything.

**Signature**

```python
ingest(path: str | None = None, full: bool = False) -> dict
```

**Arguments**

| Name | Type | Purpose |
|---|---|---|
| `path` | `str \| None` | Reserved. Scoping ingest to a subtree is not yet implemented. Supplying a value raises `ToolError`. |
| `full` | `bool` | If true, rebuild the entire index from scratch. |

**Returns** — `IngestReport` dict:

```json
{"indexed": 7, "updated": 0, "skipped": 0, "errors": []}
```

* `indexed` — notes newly added to the vector store.
* `updated` — notes whose hash changed and were re-embedded.
* `skipped` — notes that failed frontmatter validation (counted in `errors`).
* `errors` — list of `"path: reason"` strings.

Orphan note ids (present in the store but no longer on disk) are deleted on
every run; orphan deletions are not separately counted.

After every successful run, `last_ingest.json` is written under
`ZETTELKASTEN_CHROMA_PATH` with an ISO-8601 timestamp.

---

## `status`

Report index health, counts by type and tag, and coverage gaps.

**Signature**

```python
status() -> dict
```

**Returns** — `StatusReport` dict:

```json
{
  "total_indexed": 7,
  "last_ingest": "2026-04-17T12:34:56",
  "by_type": {"permanent": 4, "literature": 2, "index": 1},
  "by_tag": {"zettelkasten": 3, "rag": 2, "ollama": 1, ...},
  "coverage_gaps": [
    {"path": "/vault/notes/broken.md", "reason": "parse-error: invalid type: 'fleeting'"}
  ]
}
```

**Coverage gap reasons**

| Reason prefix | Meaning |
|---|---|
| `parse-error: <reason>` | `parse_note` raised `InvalidNote`; `<reason>` is the specific validation failure |
| `read-error: <os-error>` | File existed during walk but could not be read |
| `unindexed` | File parsed successfully but is absent from the vector store (e.g. ingest has not run yet, or embedding previously failed) |

`last_ingest` is `null` if no successful ingest has ever completed.

---

## `health_check`

Liveness probe.

**Signature**

```python
health_check() -> str
```

**Returns** — `"OK (zettelkasten-mcp v<version>)"`.

Always safe to call; does not touch Ollama or Chroma.
