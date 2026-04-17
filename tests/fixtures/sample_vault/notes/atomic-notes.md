---
id: atomic-notes
type: permanent
tags: [zettelkasten, atomic-notes, note-taking]
created: 2026-01-05
source: journal/2026-01-05
updated: 2026-03-02
related: [semantic-search, chromadb-basics]
---

# Atomic notes

An **atomic note** contains exactly one idea that stands on its own. It should be readable out of context, linkable from many places, and short enough that its meaning does not depend on where it lives in the folder tree.

## Why atomic

- Searching for a concept returns the concept, not a 2,000-word essay that *mentions* it.
- Linking becomes cheap because link targets are small and stable.
- Agents retrieving fragments for RAG do better when fragments are self-contained.

## When a note is not atomic

- It needs three paragraphs of setup before the payload.
- It contains a section titled "also…" or "various".
- Two different people would file it under two different top-level topics.

When in doubt: split. Two small notes with a link between them are better than one long note with a heading.
