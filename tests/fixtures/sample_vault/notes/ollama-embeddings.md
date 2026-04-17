---
id: ollama-embeddings
type: permanent
tags: [ollama, embeddings, local-first, foss]
created: 2026-02-18
source: journal/2026-02-18
related: [semantic-search, chromadb-basics]
---

# Ollama for local embeddings

[Ollama](https://ollama.com/) runs open-weight models locally with a small HTTP API. For a personal RAG pipeline it is the simplest way to get embeddings without sending text to a cloud vendor.

## Why it fits

- **Local by default.** Text never leaves the machine.
- **Small footprint.** `nomic-embed-text` is ~274 MB and produces 768-dim vectors.
- **Same API surface everywhere.** macOS, Linux, Docker all expose `http://localhost:11434`.

## Minimal setup

```bash
brew install ollama            # or the Linux installer
ollama pull nomic-embed-text
curl http://localhost:11434/api/embeddings \
  -d '{"model":"nomic-embed-text","prompt":"hello"}'
```

## Constraints

- Swapping to a different embedding model changes the vector dimension; your Chroma collection must be rebuilt.
- The Python client (`ollama` on PyPI) is synchronous; async consumers need a threadpool.
