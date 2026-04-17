# Security policy

## Threat model in one paragraph

zettelkasten-mcp runs entirely on the user's machine. It reads markdown files
from a vault directory, sends their text to a local Ollama instance for
embedding, and writes vectors into a local ChromaDB directory. No data leaves
the host (unless the user has configured `ZETTELKASTEN_OLLAMA_URL` to point at
a remote Ollama — their choice, their risk). There is no authentication
layer because the MCP client is the only caller and runs in the same trust
boundary.

## Reporting a vulnerability

Email <u-amateur@proton.me> with a subject line starting `[security]`. Do
not file public GitLab issues for security problems until we've had a chance
to ship a fix.

We'll acknowledge within 7 days and aim for a fix or mitigation within 30
days depending on severity.

## Scope — what we consider a vulnerability

* **Path traversal** — any way to make the indexer read, write, or delete
  files outside `ZETTELKASTEN_VAULT_PATH` or `ZETTELKASTEN_CHROMA_PATH`.
* **Arbitrary code execution** — via frontmatter, markdown content, or any
  input the indexer processes.
* **Data exfiltration** — a path by which vault contents could leak beyond
  the local Ollama endpoint the user configured.
* **Supply-chain issues** — compromised dependencies, malicious releases, or
  build-time tampering.

## Out of scope

* Risks the user opted into by pointing `ZETTELKASTEN_OLLAMA_URL` at a remote
  host.
* Compromise of the user's own machine (if the host is owned, the vault is
  already exposed).
* Denial of service from feeding an enormous vault into the ingest — this
  is a resource-exhaustion property of the chosen stack (Chroma + Ollama),
  not a vulnerability.
* Issues in upstream packages (Ollama, ChromaDB, fastmcp) that are not
  reachable through zettelkasten-mcp's public surface.

## What we commit to

* **No network calls** outside `ZETTELKASTEN_OLLAMA_URL`. Period. If a future
  change introduces one, it must be behind an opt-in flag documented in
  `AGENTS.md`.
* **No secrets in logs.** The project doesn't handle credentials and has
  nothing to log, but we'll reject PRs that introduce any.
* **Pinned majors for dependencies.** `pyproject.toml` uses caret ranges so
  dependency updates require an intentional bump.
