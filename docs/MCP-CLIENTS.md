# MCP client configuration

zettelkasten-mcp speaks MCP over stdio. Any MCP-compliant client can launch
it as a subprocess. Below are working configurations for the common ones.

> All examples assume you've already run `zettelkasten-mcp ingest --full` at
> least once. See [`RAG-SETUP.md`](RAG-SETUP.md) for the pipeline setup.

## Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "zettelkasten": {
      "command": "zettelkasten-mcp",
      "args": ["serve"],
      "env": {
        "ZETTELKASTEN_VAULT_PATH": "/Users/you/vault"
      }
    }
  }
}
```

Restart Claude Desktop. The tools (`search`, `ingest`, `status`,
`health_check`) appear in the slash-menu under the zettelkasten server.

## Claude Code

Add to `~/.claude/mcp.json` or the project-local `.mcp.json`:

```json
{
  "mcpServers": {
    "zettelkasten": {
      "command": "zettelkasten-mcp",
      "args": ["serve"],
      "env": {
        "ZETTELKASTEN_VAULT_PATH": "/Users/you/vault"
      }
    }
  }
}
```

Reload with `/mcp reload` or restart the session.

## Cursor

Cursor reads `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "zettelkasten": {
      "command": "zettelkasten-mcp",
      "args": ["serve"],
      "env": {
        "ZETTELKASTEN_VAULT_PATH": "/Users/you/vault"
      }
    }
  }
}
```

## Generic stdio client

Any MCP client that supports stdio can launch:

```bash
zettelkasten-mcp serve
```

with `ZETTELKASTEN_VAULT_PATH` set in the environment. The server talks JSON-RPC
over stdin/stdout per the MCP spec.

## Passing a different vault per invocation

The CLI respects `--vault` on all subcommands:

```bash
zettelkasten-mcp serve --vault /path/to/other-vault
```

Internally this sets `ZETTELKASTEN_VAULT_PATH` before starting the server.

## Running multiple vaults

Each vault needs its own Chroma directory, otherwise collections collide:

```json
{
  "mcpServers": {
    "vault-work": {
      "command": "zettelkasten-mcp",
      "args": ["serve"],
      "env": {
        "ZETTELKASTEN_VAULT_PATH": "/Users/you/work-vault",
        "ZETTELKASTEN_CHROMA_PATH": "/Users/you/.zettelkasten/work-chroma"
      }
    },
    "vault-personal": {
      "command": "zettelkasten-mcp",
      "args": ["serve"],
      "env": {
        "ZETTELKASTEN_VAULT_PATH": "/Users/you/personal-vault",
        "ZETTELKASTEN_CHROMA_PATH": "/Users/you/.zettelkasten/personal-chroma"
      }
    }
  }
}
```

## Verifying the connection

Call `health_check` from the client — it returns
`"OK (zettelkasten-mcp v0.1.0)"` without touching Ollama or Chroma, which
makes it a safe probe.
