---
id: bad-date
type: permanent
tags: [edge-case]
created: yesterday
source: edge-case
---

# Bad date format

`created: yesterday` is not ISO-8601. The indexer should raise `InvalidNote`
whose reason starts with `"invalid created"`.
