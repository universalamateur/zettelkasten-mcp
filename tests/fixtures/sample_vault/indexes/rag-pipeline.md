---
id: rag-pipeline
type: index
tags: [rag, semantic-search, mcp]
created: 2026-03-01
source: project/zettelkasten-mcp
related: [semantic-search, ollama-embeddings, chromadb-basics, atomic-notes]
---

# RAG pipeline — index

Entry point for everything related to the local RAG pipeline in this vault.

## Concepts

- [[atomic-notes]] — why one idea per note makes retrieval work
- [[semantic-search]] — the mechanics of embedding-based retrieval
- [[ollama-embeddings]] — local embedding model choice
- [[chromadb-basics]] — embedded vector storage

## Literature

- [[ahrens-2017-how-to-take-smart-notes]] — note-taking theory
- [[kleppmann-2019-local-first-software]] — local-first ideals

## Open threads

- When to re-embed: the [[chromadb-basics]] note flags the rebuild requirement on model swap; no decision yet on how to automate it.
- Tag vocabulary enforcement: notes currently pass even with unknown tags (see `AGENTS.md` "When to stop and ask").
