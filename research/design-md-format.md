# DESIGN.md — Visual Identity Spec for Coding Agents

**Source:** https://github.com/google-labs-code/design.md (Google Labs, alpha)
**Grade:** B — vendor-official spec, new format, adoption unproven.

## What it is

A file format that pins a project's visual identity so coding agents stop re-rolling it each session. Two layers:

- **YAML front matter** — normative design tokens (`colors`, `typography`, `rounded`, `spacing`, `components`).
- **Markdown prose** — rationale: what each token *means* and when to apply it.

Tokens carry exact values; prose carries intent. Agent editing UI reads both.

## Tooling

```bash
npx @google/design.md lint DESIGN.md   # schema check, broken refs, WCAG contrast — JSON output
npx @google/design.md diff A.md B.md   # token + prose regression detection
```

Both emit structured JSON — usable in CI or hook.

## Token Schema (alpha)

```yaml
version: alpha
name: <string>
colors: { <name>: <Color> }
typography: { <name>: { fontFamily, fontSize, ... } }
rounded: { sm|md|lg: <Dimension> }
spacing: { sm|md|lg: <Dimension|number> }
components: { <name>: { <token>: <ref|literal> } }
```

## When to adopt

- Project has a **load-bearing visual identity** (dashboard, report surface, published frontend).
- Agents repeatedly make UI decisions you'd otherwise have to re-specify.
- Identity is **stable enough** that pinning it won't churn.

## When NOT to adopt

- Design isn't settled — pinning premature choices just makes agents converge on a decision you haven't made. Every iteration becomes a spec update.
- UI is incidental (kernel-first projects, internal tools).
- No agent-generated UI work happening.

## Candidate projects (as of 2026-04-21)

- **phenome dashboards / intel reports** — viable if visual identity matters there.
- **evo** — assessed and **deferred**: in extraction mode, design not settled. Revisit when UI stabilizes or agents start fighting visual decisions.
- **new frontends** — adopt from day one once identity is chosen.

## Related

- `research/agent-economics-decision-frameworks.md` — maintenance-cost gating (adding a spec = ongoing surface).
- Constitution principle 11: recurring patterns become architecture. If agents re-specify colors 10+ times in one project, that's the signal.

<!-- knowledge-index
generated: 2026-04-22T06:49:29Z
hash: c4225f4efbb7

cross_refs: research/agent-economics-decision-frameworks.md

end-knowledge-index -->
