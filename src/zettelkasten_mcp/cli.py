"""Typer CLI with subcommands: serve, ingest, status."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from zettelkasten_mcp import __version__
from zettelkasten_mcp.config import Settings, get_settings
from zettelkasten_mcp.store import ChromaStore

app = typer.Typer(
    name="zettelkasten-mcp",
    help="MCP server for semantic search over markdown vaults with YAML frontmatter.",
    no_args_is_help=True,
    add_completion=False,
)


def _print_json(payload: dict) -> None:
    typer.echo(json.dumps(payload, indent=2, sort_keys=True, default=str))


def _load_settings(vault: Optional[Path]) -> Settings:
    if vault is not None:
        import os

        os.environ["ZETTELKASTEN_VAULT_PATH"] = str(vault)
    return get_settings()


@app.command()
def version() -> None:
    """Print the installed zettelkasten-mcp version."""
    typer.echo(__version__)


@app.command()
def serve(
    vault: Optional[Path] = typer.Option(None, "--vault", help="Override ZETTELKASTEN_VAULT_PATH."),
) -> None:
    """Start the MCP server over stdio."""
    _load_settings(vault)
    from zettelkasten_mcp.server import main as serve_main

    serve_main()


@app.command()
def ingest(
    vault: Optional[Path] = typer.Option(None, "--vault", help="Override ZETTELKASTEN_VAULT_PATH."),
    full: bool = typer.Option(False, "--full", help="Rebuild the entire index from scratch."),
) -> None:
    """Run an ingest (incremental by default, full reindex with --full)."""
    settings = _load_settings(vault)
    # Local import so `zettelkasten-mcp --help` stays fast and does not need
    # Chroma / Ollama importable at CLI introspection time.
    from zettelkasten_mcp.server import run_ingest

    store = ChromaStore(settings)
    report = run_ingest(settings, store, full=full)
    _print_json(report.model_dump())


@app.command()
def status(
    vault: Optional[Path] = typer.Option(None, "--vault", help="Override ZETTELKASTEN_VAULT_PATH."),
) -> None:
    """Print index health and coverage gaps as JSON."""
    settings = _load_settings(vault)
    from zettelkasten_mcp.server import status as status_tool  # reuses tool body

    # ``status_tool`` is the @mcp.tool wrapper; FastMCP keeps the original
    # function attached via ``.fn`` so direct invocation works.
    callable_ = getattr(status_tool, "fn", status_tool)
    _print_json(callable_())
    # settings reference kept so type checkers see it is used intentionally.
    _ = settings


if __name__ == "__main__":
    app()
