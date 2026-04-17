# sample_vault — Synthetic Zettelkasten Fixture

Used by the test suite and also suitable as a minimal starter vault for end-to-end manual tests against a live Ollama + ChromaDB stack.

## Layout

```text
sample_vault/
├── .rag/
│   ├── schema.yaml
│   └── tags.yaml
├── notes/            # permanent notes (4 files)
├── literature/       # literature notes (2 files)
├── indexes/          # index notes (1 file)
├── projects/001-example-project/README.md  # project note (1 file)
└── journals/         # skipped by default
```

## Expected behaviour under default config

Default `index_dirs` is `notes,literature,indexes` — **`projects/` is NOT indexed by default**, matching the shipped `Settings` defaults. The journal is ignored because `journals` is in the default `skip_dirs`.

- `iter_vault_files` returns **7 files** (4 permanent + 2 literature + 1 index).
- `parse_note` succeeds on all 7; each one has valid frontmatter.
- `run_ingest(..., full=True)` reports `indexed: 7, updated: 0, skipped: 0, errors: []`.
- `status()` returns `total_indexed: 7`, `by_type: {permanent: 4, literature: 2, index: 1}`, `coverage_gaps: []`.

To include the project note, override the env var:

```bash
ZETTELKASTEN_INDEX_DIRS=notes,literature,indexes,projects
```

Note: with the current implementation, adding `projects` to `index_dirs` will recurse the whole subtree and pick up any `.md` file there, not just `README.md`. This is tracked as open question #3 in `.local/IMPLEMENTATION-STATUS.md`.

## Using as a real vault

```bash
export ZETTELKASTEN_VAULT_PATH=$(pwd)/tests/fixtures/sample_vault
export ZETTELKASTEN_CHROMA_PATH=/tmp/sample_vault_chroma
ollama pull nomic-embed-text
poetry run zettelkasten-mcp ingest --full
poetry run zettelkasten-mcp status
```
