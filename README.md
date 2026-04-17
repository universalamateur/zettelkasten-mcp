# zettelkasten-mcp

> **Status:** Pre-alpha scaffold. Not yet functional. See [CHANGELOG.md](CHANGELOG.md).

MCP server for semantic search over markdown vaults with YAML frontmatter. Local RAG pipeline using [Ollama](https://ollama.com/) for embeddings and [ChromaDB](https://www.trychroma.com/) for vector storage. 100% FOSS, local-first, works offline.

## What this is

A [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes a markdown vault (Obsidian, Zettelkasten, plain folder of `.md` files) as a semantic search resource for any MCP client (Claude Code, Claude Desktop, Cursor, etc.).

Designed for markdown files with YAML frontmatter, but usable with any `.md` content.

## MCP Tools

| Tool | Purpose |
|---|---|
| `search(query, tags?, type?, since?, limit=10)` | Semantic search with metadata filters |
| `ingest(path?, full=false)` | Incremental or full reindex |
| `status()` | Index health + coverage gaps |

## CLI

```bash
zettelkasten-mcp serve          # Start MCP server (stdio)
zettelkasten-mcp ingest         # Incremental ingest
zettelkasten-mcp ingest --full  # Full reindex
zettelkasten-mcp status         # Print index stats
```

## Configuration

All variables prefix with `ZETTELKASTEN_`. See [`.env.example`](.env.example) for the full list.

## Roadmap

See the [implementation plan](https://gitlab.com/universalamateur1/zettelkasten-mcp/-/issues). Next steps:

1. [x] Scaffold repo
2. [ ] `config.py` + `models.py`
3. [ ] `indexer.py` (frontmatter parse, markdown strip, Ollama embedding)
4. [ ] `store.py` (ChromaDB wrapper)
5. [ ] `server.py` (FastMCP with 3 tools)
6. [ ] `cli.py` (Typer)
7. [ ] Tests with mocked Ollama + in-memory ChromaDB
8. [ ] Full README with RAG pipeline setup guide
9. [ ] CI/CD pipeline
10. [ ] Dockerfile + smithery.yaml
11. [ ] v0.1.0 release

## License

MIT. See [LICENSE](LICENSE).
