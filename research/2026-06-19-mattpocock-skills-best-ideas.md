---
title: mattpocock/skills@1.0.0 — full best-ideas extraction + integration verdict
date: 2026-06-19
status: complete
tags: [skills, external-eval, skill-authoring, code-design, planning]
---

# mattpocock/skills@1.0.0 — all best ideas + what to integrate

**Source:** cloned to `~/Projects/best/mattpocock-skills` (33 SKILL.md across
engineering/productivity/misc/personal/in-progress/deprecated; 136K stars; v1.0.1 2026-06-17).
**Method:** both sides read in full — their 33 skills + our equivalents (interview-prompt,
interface-thinking, debug, verify-before, decide, code-review, critique, skill-authoring, hooks/,
checkpoint). Two independent passes (comparison lens + in-progress/references lens) converged.

## Verdict (both passes agree): pattern-skim, take the ideas, DO NOT symlink/install

Installing is **net-negative**: `setup-matt-pocock-skills` dependency chains, an issue-tracker
assumption baked through many skills, TS/course tooling, 8 domain-N/A skills. The value is ~6
transferable *ideas* folded into 4 of our files. 136K stars is a teaching-audience signal, not a
quality proof — but the two "they-win" calls are earned on merit, not stars.

Class tally (21 named): DOMAIN-N/A 8 · OVERLAP-WE-WIN 6 · OVERLAP-THEY-WIN 2 · GAP-WORTH-TAKING 1 · GAP-SKIP 4.

## A. Net-new steals (ranked — what to take, where it folds, effort)

1. **`writing-great-skills` design-language → our skill-authoring guide.** *(highest leverage — we
   maintain ~45 skills.)* Ours owns mechanics (frontmatter, L1/L2/L3, per-step constraint types);
   theirs owns design-language we lack:
   - **predictability as the root virtue** of a skill.
   - **leading words** — recruit a pretrained concept as a one-token behavior anchor
     ("fast, deterministic, low-overhead" → *tight*).
   - **no-op elimination hunted sentence-by-sentence** — delete the whole sentence, don't trim it.
   - **failure taxonomy**: premature-completion / sediment / sprawl / no-op.
   - **context-load vs cognitive-load** cost model for what to put in a skill.
   Effort ~1hr, additive prose. *(Meta: this is exactly the discipline we practiced this session
   killing the plan-contract theater — convergent.)*

2. **`decision-mapping` fog-of-war model → `/decide` / planning.** *(in-progress upstream — take the
   pattern, not the file.)* A compact **git-tracked ticket map**, one per planning effort, **whole map
   loaded as context every session**; numbered tickets with `Blocked by:` edges + `Type:
   Research|Prototype|Discuss`; **each ticket sized to one ~100K-token session**; resolve the
   **frontier** one node at a time ("push back the fog of war"); **skip the map entirely if grilling
   surfaces no fog** (no-op elimination at the skill level). Best external multi-session-planning model
   seen; adjacent to our plan + lifecycle-graph work. Effort ~2hr to adapt.

3. **`diagnosing-bugs` "build the feedback loop FIRST" → our `/debug`.** Our debug is fan-out scout
   orchestration; we have **no single-agent diagnosis discipline**. Their thesis + hard gate: *name one
   red-capable command you have ALREADY RUN, paste it + its output, before any hypothesis*; a 10-way
   loop-construction ladder; **seam-honesty** ("no correct seam = that IS the finding; don't fake a
   shallow test"). Effort ~2hr as a /debug gate.

4. **`codebase-design` deep-module vocab → one-liners into `interface-thinking` + `code-review` +
   `/decide`.** *(take the 20%, skip the standalone skill — it's TS-app-flavored.)* Ousterhout/Feathers
   operationalized: the **deletion test**; **"one adapter = hypothetical seam, two = real"** (= our
   proven-common-≥2, generalized to abstractions/ports); **"the interface is the test surface; replace,
   don't layer"** (delete shallow-module tests once interface tests exist); **dependency-category →
   test-strategy table** (in-process / local-substitutable / remote-owned=ports&adapters /
   true-external=mock); **depth = leverage, not a line-count ratio** (a genuine improvement on the
   source). NOTE our `interface-thinking` is HCI/tool-design scope — *different* from code-module
   design, so this is additive, not a dup. Effort ~30-60min.

5. **`DESIGN-IT-TWICE` per-agent constraint template → `/brainstorm` + `/decide` Phase 1.** Spawn N
   divergent designers each with a *different* constraint (minimize-interface / maximize-flexibility /
   optimize-common-caller / ports-&-adapters); **show the user the problem framing so they think WHILE
   the agents work** (latency overlap); **"be opinionated, give a recommendation — not a menu."** Effort ~30min.

6. **`review` fail-fast + no-op → `code-review`.** Validate the ref resolves + diff is non-empty
   *before* spawning sub-agents ("fail here, not inside two parallel agents"); **skip anything tooling
   enforces**; separate hard-violations from judgment-calls. Effort ~20min.

Honorable: `handoff`'s "suggested-skills section" + "reference-don't-duplicate-artifacts" → two lines
for our checkpoint convention.

## B. Convergent validation (they independently arrived at our design — confirms, no action)

| Their artifact | Confirms our |
|---|---|
| `review`: two parallel axes, **"do not merge or rerank — separation stops one axis masking the other"** | partition-not-compete (`code-review` ≠ `critique`) |
| `DESIGN-IT-TWICE` parallel divergent designers | `/brainstorm` + `/decide` 5-mechanism diverge |
| `deprecated/`: point-skills consolidated into deeper composable ones (ubiquitous-language→domain-modeling; design-an-interface→codebase-design) | breaking-refactor consolidation |
| "two adapters means a real seam" | proven-common-≥2 extraction test |

## C. Refuted "they-win" suspicions (we win — don't re-eval)

- **`grilling`** — clean extraction (one model-invoked loop, 1-line callers) but the loop is thin; our
  `interview-prompt` info-gain filter (predict answers, score by variance × update-magnitude, drop
  answerable questions) is strictly more.
- **`review`** — tidy two-axis, but our cross-model critique + code-review (premise scout,
  confidence-distrust calibration, convergent/divergent bucketing, anchor-hallucination fixes) are a
  different league.
- **`handoff`** — ours is hook-driven/auto-generated; theirs is a manual `/tmp` doc.
- **`git-guardrails`** — a setup recipe for a static deny-list hook; our `pretool-destructive-git-ref.sh`
  + predelete / add-all / no-background-commit / multiagent / append-only / data guards + commit-time
  backstops far exceed it.

## D. Domain-N/A (TS-education / course / issue-tracker tooling — don't re-look)

`migrate-to-shoehorn`, `scaffold-exercises`, `setup-pre-commit` (Husky), `setup-matt-pocock-skills`,
`teach`, `triage`, `to-issues`, `ask-matt`, and the personal-writing skills (`edit-article`,
`obsidian-vault`, `writing-beats`/`-fragments`/`-shape`).

## Integration plan (each is a shared-skill edit → 3+ blast radius → human-gated per constitution)

Ranked by leverage: (1) writing-great-skills principles → skill-authoring [~1hr] · (2) codebase-design
one-liners → interface-thinking/code-review [~45min] · (3) diagnosing-bugs feedback-loop-first gate →
/debug [~2hr] · (4) decision-mapping fog-of-war → /decide [~2hr] · (5) DESIGN-IT-TWICE constraint
template → /brainstorm [~30min] · (6) review fail-fast → code-review [~20min].
