# Contributing to zettelkasten-mcp

Thanks for considering a contribution. This project is small and opinionated;
the guidelines below keep it that way.

Read [`AGENTS.md`](AGENTS.md) first — it is the public SSOT for rules that
apply to humans and LLM agents alike.

## Ground rules

1. **Understandability > maintainability > simplicity.** Every change must
   pass these three filters, in that order.
2. **No feature creep.** The scope is: semantic search over markdown vaults
   with YAML frontmatter. Anything else (editing, syncing, crawling, chat UI)
   belongs in a different project.
3. **Tests pass locally before you open an MR.** No exceptions.
4. **Style is enforced.** `black` (line-length 120), `isort`, `flake8`,
   `mypy`.

## Dev setup

```bash
git clone git@gitlab.com:universalamateur1/zettelkasten-mcp.git
cd zettelkasten-mcp
poetry install
poetry run pytest          # must pass on a fresh checkout
```

Ollama is **not** required to run the test suite — `ollama.Client` is
monkey-patched in `tests/conftest.py` to return deterministic pseudo-random
vectors. Tests run offline in seconds.

## Running pieces locally

```bash
export ZETTELKASTEN_VAULT_PATH=$(pwd)/tests/fixtures/sample_vault
export ZETTELKASTEN_CHROMA_PATH=/tmp/ztk-dev-chroma
ollama pull nomic-embed-text
poetry run zettelkasten-mcp ingest --full
poetry run zettelkasten-mcp status
```

Expected: `indexed: 7, errors: []`, status `total_indexed: 7`.

## What goes where

| Change type | File(s) |
|---|---|
| Frontmatter schema or tag vocab | `tests/fixtures/sample_vault/.rag/{schema,tags}.yaml` — and update `models.NoteType` / validators to match |
| New MCP tool | Add a `@mcp.tool` function in `server.py`; document it in `docs/API.md`; add tests in `tests/test_server.py` |
| New CLI command | Add a `@app.command()` in `cli.py`; add a test in `tests/test_cli.py` using `typer.testing.CliRunner` |
| Ingest logic | Modify `indexer.py` (pure transforms) or the `run_ingest` function in `server.py` (pipeline). Not both. |
| Vector-store behaviour | `store.py` only. Do not bypass `ChromaStore` from other modules. |

## Tests

* **Real tests only.** Placeholder `assert True` tests are not accepted.
* **No network or model downloads in CI.** Use the `patched_ollama` and
  `chroma_client` fixtures from `conftest.py`.
* **Edge cases go in `tests/fixtures/edge_cases/`.** One file per failure
  branch, with the expected `InvalidNote` reason in the file's body comment.
* **New MCP tool → new test in `tests/test_server.py`.** Test the happy path
  and at least one error path.

Run a single file:

```bash
poetry run pytest tests/test_indexer.py -v
```

## Version bumps

Three places must match (enforced by release checklist):

1. `src/zettelkasten_mcp/__init__.py` — `__version__`
2. `pyproject.toml` — `[project].version` and `[tool.poetry].version`
3. `CHANGELOG.md` — new section for the version

The `zettelkasten-mcp version` command reads `__init__.py`, so tests will
catch drift.

## Git policy

* Work on a feature branch from `main`. Never commit directly to `main`.
* Commit messages explain the *why*, not just the *what*.
* **Never stage `CLAUDE.md`, `GEMINI.md`, or lowercase `claude.md`.** These
  are gitignored and contain non-public references. Before every commit:

  ```bash
  git diff --cached --name-only | grep -iE 'claude\.md|gemini\.md' && echo "ABORT" || echo "safe"
  ```

* Sign commits if you can; it's not mandatory.

## Opening an MR

1. Fork or branch.
2. Implement + test.
3. Run `poetry run pytest && poetry run black --check src tests && poetry run mypy src`.
4. Push and open an MR against `main`.
5. Describe the *problem* the MR solves in the description. A screenshot of
   `zettelkasten-mcp status` output helps for user-visible changes.

## License

By contributing you agree your contribution is MIT-licensed, matching the
project.
