# Frontend Polish Techniques — Micro-Interaction Details

**Source:** https://jakub.kr/writing/details-that-make-interfaces-feel-better (Jakub Krehel)
**Grade:** B — practitioner blog, concrete CSS recipes, no novel claims.

## When to consult

- Polishing a **settled** UI where the design decisions are made and the remaining gap is feel/craft.
- Reviewing a frontend that looks "fine but not good" — these are the invisible tells.
- Before shipping a public-facing surface (dashboard, report, landing).

## When NOT to consult

- Design isn't settled — polishing premature decisions just locks them in.
- Kernel/backend work, internal CLI tools, agent-dispatched scripts.

## Techniques

| Technique | CSS / API | Problem it solves |
|---|---|---|
| Balanced titles | `text-wrap: balance` | Ragged multi-line headings |
| Pretty paragraphs | `text-wrap: pretty` | Orphaned last words |
| Concentric radius | outer = inner + padding | Nested corners look wrong |
| Crisp text (macOS) | `-webkit-font-smoothing: antialiased` | Text renders thick/muddy |
| Tabular numbers | `font-variant-numeric: tabular-nums` | Digits jitter on update |
| Interruptible anims | CSS `transition` (not `@keyframes`) | Animations can't be retargeted mid-flight |
| Staggered entry | Per-chunk delays | Block-entry feels heavy |
| Subtle exit | Smaller movement than entry (e.g. `-12px`) | Exits over-announce themselves |
| Optical alignment | Margin tweaks past geometric center | Icons look "slightly off" |
| Shadows over borders | Layered `box-shadow` | Borders don't adapt across bg colors |
| Image outlines | 1px black/white @ 10% opacity | Images float on page without grounding |

## Candidate projects (as of 2026-04-21)

- **intel reports, phenome dashboards** — viable once identity chosen.
- **evo** — deferred (extraction mode, design unsettled).
- Any user-facing publish surface in selve/genomics.

## Related

- `research/design-md-format.md` — pin tokens/identity first, polish second.
- Prerequisite ordering: identity (DESIGN.md) → layout/structure → polish (this memo).

<!-- knowledge-index
generated: 2026-04-22T06:50:29Z
hash: 65952f365719

cross_refs: research/design-md-format.md

end-knowledge-index -->
