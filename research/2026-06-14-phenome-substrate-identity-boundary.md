# phenome vs substrate vs corpus — the identity boundary (2026-06-14)

**Trigger:** Markus flagged GOALS.md as "cruft / not up to date." For phenome the
defect isn't stale *facts* — it's a stale *identity boundary*. He asked to
"research the reason discussions around phenome and substrate and corpus and so
on vs personal." This memo reconstructs that history and states the resolution.

## The de-facto architecture today (verified 2026-06-14)

The general verification substrate **already factored out of phenome**:

| Repo | What it is | Status |
|---|---|---|
| `substrate/` | L2 shared packages: `corpus-core` (canonical source store + sole `annotate` gateway), `claimcore` (biomedical claims over an *injected* corpus), `genomics-read`, `clinical-profile` | Extracted 2026-06-10 from agent-infra `scripts/corpus/packages` + genome-toolkit `packages/`; uv workspace, editable-path consumed |
| `corpus/` | The **data**: scientific source store + belief-change ledger (annotations.jsonl moat). Local git, daily launchd commit | Live |
| `genome-toolkit/` | The open local plugin — forcing function for public distribution | Live |
| `phenome/` | The **vertical product**: personal phenotype capture, self-knowledge, genome/health interpretation, agent-emulation/preference layer, daily actionable output | Consumes substrate; does not own it |

L2 discipline (substrate/CLAUDE.md): "No vertical→vertical deps. Substrate
depends only on L1 tooling, never on a vertical product (phenome/genomics/intel)."
So phenome is explicitly a *consumer*, architecturally barred from being the
substrate.

## The discussion history (Markus's own messages)

- **2026-06-09** (`/execute 7eda85c1-verification-substrate-refactor`): the
  verification-substrate refactor lands. Same day: "these design principles are
  written down somewhere? Maybe a memo/doc?" → `docs/architecture.md §0` + ADR
  0002 written.
- **2026-06-10**: "Look at phenome and corpus and genome-toolkit … phenome is
  like 2-3 projects … Should we factor out some part of it … media vs health vs
  KG vs science?" → the factor-out question. "idk get the diff between
  genome-toolkit, claimcore and corpus-core."
- **2026-06-10**: substrate repo created (extraction commit).
- **2026-06-11**: "(it's not 'my corpus' … it's general science and medical
  etc…)" / "what corpus?" / "I thought the KG is the canonical epistemic/sci[ence
  store]" — Markus pushing the KG/corpus toward *general*, away from *personal*.
- **2026-06-12**: "Dumb question: Why is all this literature and other general kg
  stuff in phenome, not substrate or something?" — **the crux.** He notices
  general-science content still framed as phenome's.

## The settled thesis (ADR 0002 / architecture §0, 2026-06-09)

"The real axis is **verify/ground vs synthesize — NOT personal vs general.**
Generality is not the disqualifier; synthesis-as-product is." Grounded in
Markus's own 2021 essay on why literature-KG-as-a-business fails: build the half
that survives (a verifiable evidence substrate the LLM reasons against), never
the half that dies (a graph expected to think for you).

So "personal vs general" was the *wrong* axis. But that resolution lives in the
substrate's design rationale — and the substrate is now its own repo. phenome
inherited the *thesis* text but no longer *is* the thing the thesis describes.

## The defect in phenome/docs/GOALS.md

The doc (updated 2026-06-12) still claims phenome **is** the substrate:
- Line 14: "A self-knowledge engine **and verification substrate**, not a search tool."
- Line 18: "**Verification substrate (the core)**: A graded, sourced, drift-aware claim layer…"
- Carries ADR-level substrate directives (store-exact-derive-coarse, quantity
  model, refusal oracle as "the core read primitive") that now belong to
  claimcore/corpus-core in the `substrate` repo.

Meanwhile the **mission** line is purely personal: "Capture MY phenotype … turn
it into actionable self-knowledge … improve MY life." Both framings coexist in
one doc; the substrate half is the stale identity.

## Resolution (proposed — phenome goals are Markus's to set)

phenome = **the personal vertical**. Its goal:
1. Capture phenotype (digital footprint + genome + health + behavioral).
2. Turn it into **actionable self-knowledge** → the daily-briefing end state.
3. Be the **agent-emulation / preference layer**: agents query phenome to act as
   Markus would when he's not there to choose.
4. **Apply** verification discipline (consume claimcore's graded/refusal layer;
   treat its own derived insights as hypotheses) — but it **consumes** the
   substrate, it does not **own** it.

Strip from phenome/GOALS.md: the "phenome IS the verification substrate" claim
and the substrate-internal ADR directives (those live in `substrate` /
`corpus-core` / `claimcore` docs). Keep: personal mission, data hierarchy,
agent-emulation layer, daily-output end state, the "verify-not-synthesize"
*discipline* as a consumer stance.

Open fork for Markus: does phenome keep the **OSS-plugin / Synthoria donor**
distribution scope, or does that move entirely to genome-toolkit + substrate
(the L2 distribution path), leaving phenome purely personal?
