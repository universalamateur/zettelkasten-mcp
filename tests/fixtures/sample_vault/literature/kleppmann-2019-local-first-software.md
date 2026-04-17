---
id: kleppmann-2019-local-first-software
type: literature
tags: [local-first, foss, privacy]
created: 2026-02-02
source: "https://www.inkandswitch.com/local-first/"
related: [ollama-embeddings, chromadb-basics]
---

# Kleppmann et al. (2019), Local-First Software

The Ink & Switch essay that coined the term *local-first*.

## Seven ideals

1. No spinners: the work happens on your machine.
2. Your work is not trapped on one device.
3. The network is optional.
4. Seamless collaboration is possible but not required.
5. The Long Now: your data outlives the vendor.
6. Security and privacy by default.
7. You retain ultimate ownership and control.

## How it maps to this project

- The vault is the user's filesystem.
- Embeddings are generated locally via Ollama.
- The vector store is an embedded ChromaDB directory the user owns.
- There is no account, no cloud, no network except to Ollama over loopback.

## Open questions

- Multi-machine sync is left to the user (git, Syncthing, iCloud). Are there cases where the index itself should be synced rather than regenerated?
- Does the "Long Now" ideal argue for a more portable on-disk format than whatever ChromaDB happens to use?
