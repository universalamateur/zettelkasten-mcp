# zettelkasten-mcp — Agent Guidelines

> Public SSOT for how both human contributors and AI agents should behave in this repository.
> Internal agent-only state lives in `.local/` and is never committed.

## What this project is

`zettelkasten-mcp` is an unofficial, FOSS [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes a folder of markdown files with YAML frontmatter as a semantic search resource.

Design boundaries:

- **Local-first, 100% FOSS.** Embeddings via [Ollama](https://ollama.com/), vector storage via embedded [ChromaDB](https://www.trychroma.com/). No cloud, no API keys, no telemetry.
- **Vault-agnostic.** Works with any `.md` files that carry YAML frontmatter. Obsidian, plain folders, Zettelkasten, personal-wiki style — all fine.
- **Read-mostly server.** The server indexes and searches. It does not create, edit, or move notes. Authoring stays in the user's editor.

## Repository layout

```text
zettelkasten-mcp/
├── src/zettelkasten_mcp/
│   ├── __init__.py          # version
│   ├── __main__.py          # python -m zettelkasten_mcp → cli.app
│   ├── cli.py               # Typer CLI: serve, ingest, status, version
│   ├── server.py            # FastMCP server; run_ingest pipeline
│   ├── config.py            # Pydantic Settings (ZETTELKASTEN_* env)
│   ├── models.py            # Note, SearchResult, IngestReport, StatusReport
│   ├── indexer.py           # parse_note, strip_markdown, iter_vault_files, embed_text
│   └── store.py             # ChromaStore facade over a persistent collection
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   │   └── sample_vault/    # Synthetic reusable vault for unit + integration tests
│   └── test_*.py
├── docs/                    # Contributor-facing documentation
├── AGENTS.md                # THIS FILE — public agent rules
├── README.md                # User-facing setup + usage
├── CONTRIBUTING.md          # How to contribute
├── SECURITY.md              # Vulnerability disclosure policy
├── CHANGELOG.md             # Keep-a-Changelog format
├── LICENSE                  # MIT
├── pyproject.toml           # Poetry + PEP 621
```

## Language and tooling

| Tool | Configuration |
|---|---|
| Python | `>=3.12` |
| Package manager | Poetry |
| Formatter | Black (line length 120) |
| Import sort | isort (Black profile) |
| Lint | flake8 (`.flake8`: max-line-length 120, extend-ignore E203) |
| Static types | mypy (non-strict by default) |
| Tests | pytest + pytest-asyncio + pytest-cov |
| Docstrings | Google style on public functions and classes |

Run quality checks locally:

```bash
poetry run black --check src tests
poetry run isort --check-only src tests
poetry run flake8 src tests
poetry run mypy src
poetry run pytest
```

## Design principles

1. **Understandability.** Clear naming, obvious structure, minimal indirection. A new contributor should find the relevant code within 30 seconds.
2. **Maintainability.** Prefer explicit over implicit, standard over custom, boring over brilliant.
3. **Simplicity.** Three similar lines beat a premature abstraction. Delete before you add. The MCP contract is only three tools — do not grow it without a concrete user story.
4. **Vault-agnostic by default.** Any hard-coded assumption about the Falko zettelkasten is a bug.
5. **No telemetry, no network calls beyond Ollama.** Embeddings stay local.

## Design patterns

### Validation

All structured data goes through Pydantic models in `models.py`. Tools accept primitives, translate to models, and return `model.model_dump()`.

### Error handling

- Parser failures: raise `indexer.InvalidNote(path, reason)` with a specific reason string. The ingest pipeline captures them in `IngestReport.errors`.
- Tool-facing failures: raise `fastmcp.exceptions.ToolError(msg)`; FastMCP surfaces this to the MCP client cleanly.
- Never use bare `except:`. Catch `Exception` only at the run-ingest boundary, where failure of one file must not abort the whole pass.

### Metadata storage

ChromaDB metadata must be scalar. Tags are stored as a pipe-delimited blob (`"|tag-a|tag-b|"`). Filtering:

- **Server-side (Chroma):** `type`, `updated_iso` (`$gte` for `since`).
- **Client-side (post-query):** tag membership (require all listed tags). Overfetch `n_results * 5` to keep returned size stable.

### Incremental ingest

A note is re-embedded only if `content_hash` (SHA-256 of raw file contents) changes. Orphans (IDs in Chroma no longer on disk) are deleted at the end of every pass.

## MCP tools (the public contract)

| Tool | Signature | Behavior |
|---|---|---|
| `search` | `search(query, tags?, type?, since?, limit=10)` | Semantic search with metadata filters |
| `ingest` | `ingest(path?, full=false)` | Incremental ingest; `full=true` rebuilds |
| `status` | `status()` | Index health, counts, coverage gaps |
| `health_check` | `health_check()` | Liveness string with version |

Adding a tool requires: a new Pydantic model for any structured response, a docstring in the Typer command (if CLI-exposed), a test that covers both success and error paths, and an entry in the tool table in `README.md`.

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `ZETTELKASTEN_VAULT_PATH` | Yes | — | Root of the markdown vault |
| `ZETTELKASTEN_CHROMA_PATH` | No | `~/.local/share/zettelkasten-rag` | ChromaDB persistence directory |
| `ZETTELKASTEN_OLLAMA_URL` | No | `http://localhost:11434` | Ollama HTTP endpoint |
| `ZETTELKASTEN_EMBEDDING_MODEL` | No | `nomic-embed-text` | Ollama model name |
| `ZETTELKASTEN_INDEX_DIRS` | No | `notes,literature,indexes` | Vault-relative dirs to index |
| `ZETTELKASTEN_SKIP_DIRS` | No | `journals,Customer,.git,artifacts` | Dirs to skip |

`.env` files in the vault root or CWD are loaded automatically.

## Frontmatter contract

Every indexed note needs valid YAML frontmatter:

```yaml
---
id: kebab-case-id
type: permanent | literature | project | index
tags: [at-least-one]
created: YYYY-MM-DD
source: journal/YYYY-MM-DD | project/NNN | https://...
updated: YYYY-MM-DD    # optional
related: [other-ids]   # optional
---
```

Files missing any required field are **skipped** during ingest and reported as `parse-error` in `status().coverage_gaps`. The server never edits notes to fix them.

## Version management

`__version__` in `src/zettelkasten_mcp/__init__.py` is the single source of truth. A release bumps:

1. `src/zettelkasten_mcp/__init__.py` `__version__`
2. `pyproject.toml` `[project] version` and `[tool.poetry] version`
3. `CHANGELOG.md` — new heading, move `[Unreleased]` items under it
4. Run `poetry lock` to refresh `poetry.lock`

CI enforces that all three match.

## Git operations policy

**Commits and pushes:**
- AI agents MAY commit and push on explicit user instruction.
- Agents MUST NOT force-push, rewrite history, or push tags without explicit confirmation.
- `CLAUDE.md`, `GEMINI.md`, and any file containing the pattern `claude.md` (any case) MUST NEVER be staged. Run `git diff --cached --name-only | grep -iE 'claude\.md|gemini\.md'` before every commit.
- Release tags (`vX.Y.Z`) are created by maintainers only.

**Branching:**
- `main` is the default branch.
- Feature work goes in branches named `feat/<slug>`, `fix/<slug>`, or `docs/<slug>`.
- Merge via MR, not direct push, once the project has more than one contributor.

## Contribution flow

1. Fork / branch.
2. Change code + tests + docs in the same MR.
3. Run `poetry run pytest` and the full quality check bundle.
4. Open an MR with a description that explains the *why*, not just the *what*.
5. CI must be green.

See `CONTRIBUTING.md` for the detailed guide.

## When to stop and ask

Pause and request maintainer input when:

1. A change would add a new runtime dependency.
2. A change would break the three-tool MCP contract (rename, remove, re-signature).
3. A change would lower test coverage.
4. The frontmatter schema would need to grow.
5. Performance at zettelkasten scale (~thousands of notes) is unclear.
6. Something feels like it needs >50 lines of new code or a new module.

## Non-goals

- **Not an editor.** We do not write notes.
- **Not a crawler.** We do not follow external URLs; only local markdown.
- **Not a chat interface.** We surface search results; the LLM composes the reply.
- **Not a sync service.** Multi-machine users run their own local indices.
