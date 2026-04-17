"""Typer CLI with subcommands: serve, ingest, status."""

import typer

app = typer.Typer(
    name="zettelkasten-mcp",
    help="MCP server for semantic search over markdown vaults with YAML frontmatter.",
    no_args_is_help=True,
)


@app.command()
def serve() -> None:
    """Start the MCP server over stdio."""
    # TODO(step 6): delegate to server.main()
    raise NotImplementedError("serve not yet implemented")


@app.command()
def ingest(
    path: str = typer.Option(None, "--path", help="Vault path override."),
    full: bool = typer.Option(False, "--full", help="Rebuild the entire index."),
) -> None:
    """Run an incremental ingest, or a full reindex with --full."""
    # TODO(step 6): wire indexer + store
    raise NotImplementedError("ingest not yet implemented")


@app.command()
def status() -> None:
    """Print index health and coverage gaps."""
    # TODO(step 6): call store.stats()
    raise NotImplementedError("status not yet implemented")


if __name__ == "__main__":
    app()
