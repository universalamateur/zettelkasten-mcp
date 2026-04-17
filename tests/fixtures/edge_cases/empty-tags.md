---
id: empty-tags
type: permanent
tags: []
created: 2026-04-17
source: edge-case
---

# Empty `tags` list

Tags list is empty, violating the `min_length=1` rule on `Note`. The indexer
should raise `InvalidNote` with a schema validation reason.
