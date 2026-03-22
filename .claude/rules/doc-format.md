---
paths:
  - "research/**"
  - "decisions/**"
---

# Document Format Requirements

All knowledge-eligible files (research memos, decisions, entity files) must have YAML frontmatter.
The PostToolUse hook warns if frontmatter is missing. The balance check flags it as an error.

## Meta Research Memos (`research/*.md`)

```yaml
---
title: Descriptive title
date: YYYY-MM-DD
---
```

Additional optional fields: `tags`, `status` (active/complete/superseded).

## Meta Decisions (`decisions/*.md`)

Use the template at `decisions/.template.md`. Required: `concept`, `decision_date`, `status`.

## Knowledge Index Block

The `<!-- knowledge-index ... end-knowledge-index -->` block is **machine-generated**.
Never hand-edit it. The PostToolUse hook regenerates it on every Write/Edit.
If it's missing, the hook adds it automatically.
