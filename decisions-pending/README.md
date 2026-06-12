# decisions-pending/ — the escalation surface

The cross-project analogue of hutter's `decisions-pending/`. The improvement
loop (`/improve maintain`, `/observe`, the Dreamer) writes **sign-off-ready**
proposals here; the human reads and says yes/no. The loop never greenlights
anything in this directory itself.

## What lands here (and ONLY this)

An item escalates only when it hits a real boundary the loop cannot cross
autonomously (constitution §"Autonomy Boundaries" + invariants.md):

- **taste / telos / business-outcome** — what to optimize for, not how
- **money / capital** — any spend or financial commitment
- **irreversible** — deletes architectural components, destroys state
- **shared blast radius** — hooks/skills affecting 3+ projects, or
  constitution/GOALS edits (≤1 constitution proposal/week)
- **discovery-tier direction** — a model-class / paradigm change, not a
  within-paradigm search move

Everything else the loop **decides and logs** (improvement-log.md). If you find
yourself escalating a reversible, single-project, judgment-free item, that's a
defect — decide it.

## Item format (make each a 30-second yes/no)

One file per decision: `YYYY-MM-DD-slug.md`. The loop does the work so the human
only judges:

```
# <one-line decision>

**Boundary:** taste | money | irreversible | shared | discovery
**Recommendation:** <the loop's pick, stated plainly>
**Dissent / risk:** <the strongest case against, or cross-lab critique>
**Open question for you:** <the single thing only you can answer>
**Reversible?** <yes/no — and the cost if wrong>
**Evidence:** <links: commits, memos, critique output>
```

If a proposal is consequential and non-trivial, the loop runs `/critique model`
(cross-lab, different model than the author) BEFORE writing it here — the file
carries the synthesis, not an un-pressure-tested opinion (constitution P12).

## Disposition

- **Approve** → move the item into execution (the loop or a `/execute` run picks
  it up); record the decision in `decisions/` if it forecloses alternatives.
- **Reject** → annotate why and delete, or move to `decisions/` as a
  `[-] rejected` record if worth remembering (prevents re-proposal).

## The reiteration defect

If an escalation turns out to be something you already decided elsewhere (a
"didn't we already settle this?" moment), that is the highest-signal defect:
the loop should have derived it. Log it `[obs]` and propose the checklist/hook
that would have caught it — this is the mechanism by which your manual
interventions shrink over time (the generative principle).
