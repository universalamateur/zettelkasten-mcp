---
id: invalid-type
type: fleeting
tags: [edge-case]
created: 2026-04-17
source: edge-case
---

# Invalid `type` value

`type: fleeting` is not in the enum (`permanent | literature | project | index`).
The indexer should raise `InvalidNote` whose reason starts with `"invalid type"`.
