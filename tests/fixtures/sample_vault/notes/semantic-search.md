---
id: semantic-search
type: permanent
tags: [semantic-search, rag, embeddings]
created: 2026-02-11
source: journal/2026-02-11
related: [ollama-embeddings, chromadb-basics]
---

# Semantic search

Semantic search ranks documents by *meaning* similarity instead of exact keyword overlap. Both the query and each document are mapped to points in a vector space by an embedding model; relevance is then the distance between points.

## The three moving parts

1. **Embedder** — turns text into a fixed-length vector. Must be the same model at index time and query time.
2. **Vector store** — holds vectors plus metadata, answers nearest-neighbour queries.
3. **Re-ranker** *(optional)* — reorders top-k candidates using a more expensive signal.

## Why it works for notes

A good zettelkasten has many notes that talk about the same idea in different words. Keyword search misses those connections; semantic search finds them. That is exactly the retrieval problem an LLM assistant needs solved.

## Caveats

- Distance is not confidence. A closest-match is not necessarily a relevant match.
- Embeddings drift across model versions; re-index on model change.
- Metadata filtering (tags, type, date) is still essential for precision.
