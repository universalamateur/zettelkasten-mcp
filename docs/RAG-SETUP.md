# Local RAG setup

End-to-end walkthrough to get a working local RAG pipeline with
zettelkasten-mcp. No paid APIs, no data leaves your machine.

## 1. Install Ollama

Ollama is the local embedding runtime.

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

Start the daemon (macOS: the Homebrew cask launches it automatically; Linux
runs it as a systemd service). Verify:

```bash
curl http://localhost:11434/api/tags
```

## 2. Pull an embedding model

Default is [`nomic-embed-text`](https://ollama.com/library/nomic-embed-text)
— 768-dim, Apache-2.0 licensed, ~275 MB.

```bash
ollama pull nomic-embed-text
```

Any Ollama embedding model works; override with `ZETTELKASTEN_EMBEDDING_MODEL`.

> **Warning:** changing the embedding model after ingest invalidates the
> existing Chroma collection (vector dim mismatch or semantic drift). Run
> `zettelkasten-mcp ingest --full` after any model change. Deleting the Chroma
> directory is also safe.

## 3. Install zettelkasten-mcp

Pick one:

```bash
pipx install zettelkasten-mcp                 # recommended — isolated
pip install zettelkasten-mcp                  # into current venv
poetry add zettelkasten-mcp                   # Poetry project
```

Check:

```bash
zettelkasten-mcp version
```

## 4. Configure

Minimum — point it at your vault:

```bash
export ZETTELKASTEN_VAULT_PATH="$HOME/vault"
```

All variables (see [`.env.example`](../.env.example)):

| Variable | Default |
|---|---|
| `ZETTELKASTEN_VAULT_PATH` | _(required)_ |
| `ZETTELKASTEN_CHROMA_PATH` | `~/.local/share/zettelkasten-rag` |
| `ZETTELKASTEN_OLLAMA_URL` | `http://localhost:11434` |
| `ZETTELKASTEN_EMBEDDING_MODEL` | `nomic-embed-text` |
| `ZETTELKASTEN_INDEX_DIRS` | `notes,literature,indexes` |
| `ZETTELKASTEN_SKIP_DIRS` | `journals,Customer,.git,artifacts` |

A `.env` file in the current directory or the vault root is auto-loaded.

## 5. First ingest

```bash
zettelkasten-mcp ingest --full
```

Expected output:

```json
{
  "errors": [],
  "indexed": 7,
  "skipped": 0,
  "updated": 0
}
```

(Counts depend on your vault.)

Check health:

```bash
zettelkasten-mcp status
```

Non-zero `coverage_gaps` point at files that failed frontmatter validation —
fix them and re-run ingest. Detail on every gap reason is in
[`docs/API.md`](API.md#status).

## 6. Incremental ingest

Subsequent runs are near-instant — only changed files are re-embedded:

```bash
zettelkasten-mcp ingest
```

## 7. Wire it into an MCP client

See [`docs/MCP-CLIENTS.md`](MCP-CLIENTS.md) for Claude Desktop, Claude Code,
Cursor, and generic stdio configuration.

## Troubleshooting

**`Error: [Errno 61] Connection refused`**
Ollama isn't running. `brew services start ollama` (macOS) or
`systemctl --user start ollama`.

**`errors: ["<path>: missing frontmatter"]`**
The file at `<path>` has no YAML frontmatter block. Either add one or exclude
the directory via `ZETTELKASTEN_SKIP_DIRS`.

**`errors: ["<path>: invalid type: 'fleeting'"]`**
`type` must be one of `permanent | literature | project | index`. This is
enforced by `.rag/schema.yaml` and `NoteType` — see [`AGENTS.md`](../AGENTS.md).

**Huge memory use on ingest**
ChromaDB is in-process. Very large vaults (>50k notes) may need explicit
memory configuration — not yet tested at that scale.

**Results look irrelevant**
Try a different embedding model. `nomic-embed-text` is a good default, but
domain-specific models (e.g. `mxbai-embed-large`) may rank differently. After
switching models, run `zettelkasten-mcp ingest --full`.
