# zettelkasten-mcp

![Project logo](./logo.png)

[Lead repository on GitLab](https://gitlab.com/universalamateur1/zettelkasten-mcp)

> **Status:** Alpha. Core ingest / search / status functionality implemented and tested. See [CHANGELOG.md](CHANGELOG.md).

MCP server for semantic search over markdown vaults with YAML frontmatter. Local RAG pipeline using [Ollama](https://ollama.com/) for embeddings and [ChromaDB](https://www.trychroma.com/) for vector storage. 100% FOSS, local-first, works offline.

## What this is

A [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes a markdown vault (Obsidian, Zettelkasten, plain folder of `.md` files) as a semantic search resource for any MCP client (Claude Code, Claude Desktop, Cursor, etc.).

Designed for markdown files with YAML frontmatter, but usable with any `.md` content.

## MCP Tools

| Tool | Purpose |
|---|---|
| `search(query, tags?, type?, since?, limit=10)` | Semantic search with metadata filters |
| `ingest(path?, full=false)` | Incremental or full reindex |
| `status()` | Index health, counts by type/tag, coverage gaps |
| `health_check()` | Liveness probe returning version string |

See [`docs/API.md`](docs/API.md) for full tool contracts.

## CLI

```bash
zettelkasten-mcp version                # Print installed version
zettelkasten-mcp serve                  # Start MCP server (stdio)
zettelkasten-mcp ingest                 # Incremental ingest
zettelkasten-mcp ingest --full          # Full reindex
zettelkasten-mcp status                 # Print index stats as JSON
zettelkasten-mcp ingest --vault PATH    # Override vault path for this run
```

## Quick start

```bash
# 1. Install Ollama and pull the embedding model
brew install ollama  # or see https://ollama.com/download
ollama pull nomic-embed-text

# 2. Install zettelkasten-mcp
pipx install zettelkasten-mcp          # or: poetry add zettelkasten-mcp

# 3. Point it at your vault
export ZETTELKASTEN_VAULT_PATH="$HOME/vault"
zettelkasten-mcp ingest --full
zettelkasten-mcp status
```

Full local-RAG setup walkthrough: [`docs/RAG-SETUP.md`](docs/RAG-SETUP.md).
MCP client wiring (Claude Desktop, Claude Code, Cursor): [`docs/MCP-CLIENTS.md`](docs/MCP-CLIENTS.md).

## Configuration

All variables prefix with `ZETTELKASTEN_`. See [`.env.example`](.env.example) for the full list.

| Variable | Default | Purpose |
|---|---|---|
| `ZETTELKASTEN_VAULT_PATH` | _(required)_ | Root of the markdown vault |
| `ZETTELKASTEN_CHROMA_PATH` | `~/.local/share/zettelkasten-rag` | Persisted vector DB location |
| `ZETTELKASTEN_OLLAMA_URL` | `http://localhost:11434` | Ollama HTTP endpoint |
| `ZETTELKASTEN_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model name |
| `ZETTELKASTEN_INDEX_DIRS` | `notes,literature,indexes` | Vault subdirs to index (CSV) |
| `ZETTELKASTEN_SKIP_DIRS` | `journals,Customer,.git,artifacts` | Subdirs to skip (CSV) |

## Frontmatter contract

Each indexed markdown file must carry YAML frontmatter matching this shape:

```yaml
---
id: kebab-case-id           # required; must match filename without .md
type: permanent              # required; one of: permanent | literature | project | index
tags: [zettelkasten, rag]    # required; non-empty list
created: 2026-04-17          # required; ISO-8601 date
source: internal             # required; journal path, project number, or URL
updated: 2026-04-17          # optional; used for ``since`` filter
related: [other-id]          # optional; list of related note ids
---
```

Full schema lives in [`tests/fixtures/sample_vault/.rag/schema.yaml`](tests/fixtures/sample_vault/.rag/schema.yaml); the sample vault itself (7 real notes + 5 edge cases) is a ready-to-use seed.

## Architecture

Five modules with narrow responsibilities — see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md):

* `config.py` — Pydantic `Settings` (env + `.env`)
* `models.py` — `Note`, `SearchResult`, `IngestReport`, `StatusReport`
* `indexer.py` — frontmatter parse, markdown strip, vault walk, Ollama embed
* `store.py` — ChromaDB upsert / query / stats
* `server.py` — FastMCP tools + `run_ingest` pipeline
* `cli.py` — Typer subcommands

## Development

```bash
poetry install
poetry run pytest
poetry run black src tests
poetry run mypy src
```

Contribution guide: [`CONTRIBUTING.md`](CONTRIBUTING.md). Security policy: [`SECURITY.md`](SECURITY.md). Agent / LLM contributors should read [`AGENTS.md`](AGENTS.md) first — it is the public SSOT for this project's rules.

## License

MIT. See [LICENSE](LICENSE).
