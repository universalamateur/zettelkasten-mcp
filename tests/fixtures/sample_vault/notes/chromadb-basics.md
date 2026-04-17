---
id: chromadb-basics
type: permanent
tags: [chromadb, vector-store, local-first]
created: 2026-02-20
source: journal/2026-02-20
related: [semantic-search, ollama-embeddings]
---

# ChromaDB in embedded mode

[ChromaDB](https://www.trychroma.com/) is a vector database with an embedded Python mode that stores everything on local disk. No server process, no network hop — just a directory.

## Why embedded

- Zero operational overhead for a single-user vault.
- Data portability: the whole index is a folder you can zip, back up, or drop.
- Good enough performance for tens of thousands of notes.

## Metadata is scalar

Each item carries metadata, but Chroma only accepts scalar values (str, int, float, bool). Lists need to be serialised. The idiomatic dodge is a pipe-delimited blob:

```
tags_blob = "|rag|mcp|embeddings|"
```

Query with `$contains`? No — `$contains` is for the document text. For tag filtering do a slight overfetch (e.g. `n_results * 5`) then filter tags client-side. At zettelkasten scale that cost is invisible.

## Caveats

- Dimensionality is fixed per collection. Model change → rebuild.
- Concurrent writers are not supported; stick to one process per store.
