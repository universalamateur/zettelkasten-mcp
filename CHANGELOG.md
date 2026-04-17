# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `config.Settings` — Pydantic BaseSettings with `ZETTELKASTEN_` env prefix, `.env` support, CSV parsing for list fields, `~` expansion for path fields.
- `models` — `NoteType` enum, `Note`, `SearchResult`, `IngestReport`, `CoverageGap`, `StatusReport`.
- `indexer` — `compute_hash`, `strip_markdown` (markdown-it-py token stream), `parse_note` with typed `InvalidNote` reasons, `iter_vault_files`, `embed_text`.
- `store.ChromaStore` — upsert/get_hash/delete/query/stats/indexed_ids; injectable Chroma client; tags stored as pipe-delim blob; client-side tag filtering with `limit*5` overfetch; type and since filters server-side.
- `server` — FastMCP tools (`search`, `ingest`, `status`, `health_check`); reusable `run_ingest` pipeline with incremental ingest via `content_hash`, orphan deletion, and `last_ingest.json` marker.
- `cli` — Typer subcommands (`version`, `serve`, `ingest`, `status`) with `--vault` option.
- Test suite with in-memory Chroma (`EphemeralClient`) and patched Ollama — runs offline, no model downloads required.
- Synthetic sample vault (`tests/fixtures/sample_vault/`) reusable as a real-vault seed — 4 permanent + 2 literature + 1 index + 1 project (opt-in) + skipped journal.
- Edge-case fixtures (`tests/fixtures/edge_cases/`) covering every `InvalidNote` branch.
- Public docs: `AGENTS.md`, `CONTRIBUTING.md`, `SECURITY.md`, `docs/API.md`, `docs/RAG-SETUP.md`, `docs/ARCHITECTURE.md`, `docs/MCP-CLIENTS.md`; expanded `README.md`.
- Initial repository scaffold: pyproject.toml, src layout, empty modules, tests skeleton.
