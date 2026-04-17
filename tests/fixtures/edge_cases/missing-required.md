---
id: missing-required
type: permanent
created: 2026-04-17
source: edge-case
---

# Missing required `tags`

Frontmatter is present but the required `tags` field is absent. The indexer
should raise `InvalidNote` whose reason mentions the missing field.
