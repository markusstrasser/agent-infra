---
title: Search-Engine Verification Eval — Design Spec
date: 2026-05-31
status: revised post-critique (Gemini 3.5 Flash + GPT-5.5, .model-review/2026-05-31-search-eval-design-e535b3/)
---

# Search-Engine Verification Eval — Design Spec

Multi-provider bake-off for the search APIs we route through. Roster (keys
verified live 2026-05-31): **Exa, Brave, Perplexity, Parallel, Linkup.** Grafts
the N=60 Gospel-reader study's rigor onto a standardized harness, hardened by
(a) last-3-weeks eval-methodology research
(`research/2026-05-31-eval-benchmark-methodology-delta.md`) and (b) cross-model
adversarial critique (25 findings, disposition in `.model-review/`). Goal: a
**conditional routing policy** + cost-aware comparison, not a vanity leaderboard.

## Domain: Business-Intelligence (human pick) — OPEN: BI-only vs +scientific

BI lets us source **fresh, post-cutoff** claims (recent filings, funding,
exec/regulatory actions), satisfying contamination-resistance. **Unresolved
(escalated to human):** critique #9 warns BI-only may not generalize to our
*actual* production search (genomics/intel/phenome = static, citation-dense
scientific retrieval). Two options pending human call:
- **(A) BI-only** — cleanest test of Linkup's pitch, N=60 all BI.
- **(B) BI + scientific split** — 30 BI-fresh + 30 scientific-static, separate
  routing recs; matches production but halves per-domain N.

## Stratification (revised — adds claim-age to break the freshness confound)

Critique #7/#18: recent-only BI claims confound **index freshness** with
**retrieval quality** (an engine may win because it crawls faster, not retrieves
better). Fix: claim-age is a controlled axis.

- **Truth class (primary balance):** 20 TRUE / 20 PARTIAL / 20 FALSE → baseline 33.3%.
- **Claim-age strata:** 0–7 days / 8–30 days / 31–180 days (~20 each), crossed
  with truth class. Lets us separate "fresh-specialist" from "general-quality"
  engines instead of conflating them.
- **BI sub-type** (company/financial · regulatory · people/market-events) as a
  descriptive label, not a powered cell.

## Core mechanism: TWO LANES + quote-grounded judging (the big fix)

Critique convergence (both models, #2/#4/#5/#6/#13/#21): judging an engine's
**native output** measures synthesis/writing, not retrieval — Brave hands the
judge raw snippets while Linkup/Perplexity hand pre-digested prose. "Blindness"
is also nominal: output *format* reveals the engine. Fix:

1. **Retrieve** — each engine answers the claim. Capture BOTH its synthesized
   answer (if any) AND its raw source snippets. Log latency + $ cost.
   *(Adapter audit gate — verified: Brave=snippets, Linkup=`sources[].snippet`,
   Exa=`/answer` citations w/ text, Parallel=cited excerpts. **Perplexity
   chat API is at-risk** — may return answer + citation URLs without per-source
   snippet text; if so it runs native-lane-only, flagged in results.)*
2. **Normalize** — render every engine's raw evidence into ONE common schema
   (top-K `{url, snippet}`, answer text stripped) before the judge sees it, so
   format can't leak engine identity (#13).
3. **Judge — two lanes, single best judge:**
   - **Evidence-normalized lane** (primary, measures *retrieval*): judge sees
     only the standardized snippet packet. **Quote-grounded** (#6): judge must
     extract a verbatim supporting quote from the snippets; **no quote → verdict
     cannot exceed UNCERTAIN** (blocks rewarding confident-but-unsupported prose).
   - **Native lane** (secondary, measures *end-to-end utility*): judge sees what
     the engine actually returns. Report both; log divergences.
   - One fixed strong judge (Gemini 3.5 Flash), engine-blind, stakes-neutral,
     entailment-at-stated-strength rubric (relation/scope/modality/temporal/
     numeric). GPT-5.5 as **disagreement flag only**, not a vote (Apple panel
     finding). Verdict ∈ {TRUE, PARTIAL, FALSE, UNCERTAIN, FETCH_FAILED}.
4. **Grade vs human gold** — all 60 gold labels hand-set against primary sources
   *before* any engine runs. Judge is an instrument, not the oracle.

## Verdict scoring (was undefined — critique #11)

| judge verdict vs gold | strict | conservative |
|---|---|---|
| exact match | correct | correct |
| UNCERTAIN on a TRUE/FALSE gold | incorrect | half-credit (hedge, not error) |
| PARTIAL on TRUE gold (under-claim) | incorrect | correct |
| FETCH_FAILED | incorrect, **reported separately** as coverage | excluded from accuracy denom, reported as availability |
| TRUE/FALSE swap | incorrect | incorrect |

"Accuracy" (one verdict per claim), **not "precision"** (#24).

## Statistics (rigor core — `stats.py`, stdlib, VALIDATED ✅)

Engines run on the SAME claims → **paired** analysis, never marginal-CI overlap
(critique #1, GPT conf 1.0):
- **Primary readout — Bayesian P(θ_A > θ_B)** (Beta(1,1)-Binomial Monte Carlo,
  #16). At N=60, "probability Linkup beats Exa = 0.xx" is the decision-useful
  statement; binary p-values mostly return uninformative nulls.
- **Paired bootstrap CI** on accuracy difference (resample claim indices) — the
  correct comparison instrument.
- **McNemar exact** + **Holm-adjusted** p-values across the pre-registered pairs
  (conservative cross-check; raw + adjusted both reported).
- Wilson CI = **per-engine descriptive estimate only**, never a comparison test.
- Cohen's κ (inter-engine correlation + inter-rater judge stability).
- Per-stratum + per-truth-class breakdown (PARTIAL reported separately).

## Pre-registration & power (critique #8/#10/#14/#20)

N=60/5-engines = 10 pairwise comparisons = underpowered for a full ranking.
Therefore:
- **One pre-registered primary contrast: Exa (incumbent) vs Linkup (challenger).**
  Powered, Holm-protected. All other engines run but are **descriptive/
  exploratory** (cheap to run, give per-stratum color; no inferential claims).
- **Decision rule (pre-registered):** adopt Linkup into routing iff
  P(θ_Linkup > θ_Exa) ≥ 0.90 on the evidence-normalized lane AND its
  cost-per-correct-verdict ≤ Exa's, on ≥1 claim-age stratum.
- **Sequential expansion:** if the primary contrast is inconclusive
  (0.80 < P < 0.90 or overlapping bootstrap CI), expand gold set to N=120 rather
  than over-claim at 60. Pre-registered so it's not p-hacking.

## Output: routing policy + utility, not a flat winner (#15/#17)

Deliverable is a **conditional routing recommendation** ("age <7d → X, else Y;
scientific → Z"), scored by a utility that includes latency:
`U = accuracy − w_cost·log(cost_per_call) − w_lat·log(p95_latency)` with a
sensitivity sweep over (w_cost, w_lat). Cost-per-correct-verdict leads; latency
enters because operator wait time is real here.

## Judge-as-instrument audit (#3)

Human-audit a targeted subset of the ~600 individual judgments (2 lanes × 5
engines × 60): all discordant-vs-gold, all PARTIAL, all UNCERTAIN, + a random
TRUE/FALSE sample. Confirms the judge isn't style-biased before we trust the run.

## Provider adapters (`adapters.py`, urllib/stdlib)

Contract: `query(claim) -> {answer:str|None, sources:list[{url,snippet}], raw, latency_s, cost_usd, error}`.
Must expose raw snippet text for the normalized lane; engines that can't are
native-lane-only and flagged. Errors → FETCH_FAILED, never crash the run.

## Phasing

- **P1 ✅** spec + `stats.py` (now incl. Holm, paired bootstrap, Bayesian superiority) validated.
- **P-research ✅** · **P-critique ✅** (folded in).
- **P-decision (now):** human resolves BI-only vs BI+scientific split.
- **P2:** adapters (5, with raw-snippet audit) + two-lane blind judge + grader + run.py; 6-claim pilot smoke.
- **P3:** human authors + signs off balanced gold set; **pre-register** (decision rule + primary contrast); run.
- **P4:** judge audit → analysis (Bayesian superiority, per-stratum, utility) → routing policy. Expand to N=120 only if primary contrast inconclusive.

Gate before P3 spend: domain decision + gold set human-signed-off.
