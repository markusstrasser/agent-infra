---
title: Decide/Critique cheap automation + historical validation
date: 2026-06-14
tags: [decide, critique, eval, cost, agentlogs]
status: complete
---

# Decide/Critique — cheap gates + usage validation

## Historical usage (agentlogs, 60–90d)

| Signal | n | Interpretation |
|--------|---|----------------|
| Sessions invoking `/critique` or `/code-review` Skill | 132 | Review is common |
| Sessions with **both** Skills same session | **3** | Skill-level stacking is rare |
| Sessions with `critique close` + `model-review.py` | **45** | **Closeout stacking is the real pattern** — design pass re-hits diff via packet |
| Sessions with `model-review.py` + `code-review-scout` | 2 | Diff double-scout is rare |
| `/decide` sessions also running `model-review.py` | 7 / 10 | Decide→critique is the expensive spine (expected) |
| `model-review.py` bash invocations | 440 | Gemini leg used `gemini-3.5-flash` until 2026-06-14 demotion |
| `composer` in model-review args | 0 | Composer not wired via model-review CLI yet |

**Counterfactual:** Partition enforcement (diff once via code-review, design `standard` only)
would have affected **~45 close sessions/90d**, not the 3 dual-skill sessions. The harm
was workflow prose allowing `standard,composer` on the design layer while code-review already
ran Composer on the diff.

**Flash demotion counterfactual:** 440 model-review runs used deep_review→flash35; probe
disqualified flash on clean invention — unknown how many closeouts got invented findings,
but emergency demote is conservative harm reduction.

**Would a `/review` router have helped historically?** No evidence — agents already
routed diffs to code-review when prompted; failure was closeout **recipe** stacking, not
missing classifier.

## Cheap automation between `/decide` and `/critique model`

**What already exists (zero API):**
- Phase 0 inventory: `rg`, `git log`, `decisions/` grep
- Phase 3 probe-the-join: inline bash proving symbols exist
- `model-review.py --extract` + `coverage.json` (structured post-hoc, not pre-filter)

**What is safe to add (deterministic / ~$0.001):**

| Gate | When | Cost | Why safe |
|------|------|------|----------|
| **ADR lint** | After Phase 2, before Phase 4 | $0 | Requires `## Alternatives`, `## Counterevidence`, `## Revisit if` |
| **Decision dedup grep** | Phase 0 | $0 | `rg` decisions/ for same concept slug |
| **Probe script runner** | Phase 3 | $0 | Execute embedded ` ```bash ` probes from plan; fail on nonzero |
| **Packet size gate** | Before model-review | $0 | Reject packets >N tokens; SWE-PRBench: more context → worse |
| **Haiku assumption triage** | Phase 0→1 boundary | ~$0.001 | Prompt hook: "list 3 falsifiable assumptions" — advisory only |
| **critique_replay anchor grep** | On ADR claims | $0 | If ADR cites a file:line, grep must hit |

**What NOT to do early:**

| Anti-pattern | Why |
|--------------|-----|
| **Force JSON review output before cross-model** | Goodhart — models optimize schema compliance over adversarial search; Feuer factor collapse on rubric axes |
| **Haiku as sole critic** | Probe: haiku missed C2 anchor; cheap floor ≠ cosigner |
| **LLM "is this decision good?" gate** | Same-model; replaces expensive critique with cheap sycophancy |
| **Skip Phase 4 when ADR lint passes** | Lint checks form, not substance |

**Recommended decide skill addition:** `Phase 3.5 — deterministic gate` (no LLM):
1. Run plan-embedded probes
2. ADR lint
3. Packet/token budget check if context file exists
4. Only then `/critique model --axes standard` (not deep) on ADR

Escalate to `--axes deep` only if standard finds HIGH unresolved.

**JSON is fine post-critique:** `model-review.py` already emits `findings.json` +
`disposition.md` for machines; the review *prompt* stays prose-shaped for adversarial
pressure. Extraction pass is the right place for structure.
