---
title: Search-Engine Verification Eval — Design Spec
date: 2026-05-31
status: revised post-research (pre-critique)
---

# Search-Engine Verification Eval — Design Spec

Multi-provider bake-off for the search APIs we route through. Final roster (all
keys verified live 2026-05-31): **Exa, Brave, Perplexity, Parallel, Linkup.**
Grafts the **statistical rigor** of the N=60 Gospel-reader study
(`publishing/research/2026-05-19-engine-reliability-metric.md`) onto the
**standardized-harness + class-balance** discipline of better external benchmarks,
hardened with the last-3-weeks eval-methodology literature
(`research/2026-05-31-eval-benchmark-methodology-delta.md`). Goal: a reusable
harness that yields a *routing decision* + a defensible cost-aware ranking, not a
vanity leaderboard.

## Domain: Business-Intelligence (human pick, 2026-05-31)

Tests engines on the workload Linkup optimizes for *and* an enterprise-search
axis. Crucially, BI makes **finding #5 (contamination)** easy to satisfy: claims
are sourced **fresh + post-cutoff** (recent filings, funding rounds, exec
changes, regulatory actions) so neither engine indexes nor judge memory have
memorized the answers.

**Strata (3 × 20 = 60), with truth-class balance as the primary axis:**
| stratum | example claim shape |
|---------|--------------------|
| company/financial | "Company X raised $Y Series B led by Z in <recent month>" |
| regulatory/compliance | "Regulator A issued enforcement action against B for C" |
| people/market-events | "Person P became CEO of Q"; "Product/market event R occurred" |

Within each stratum: ~7 TRUE / 7 PARTIAL / 6 FALSE → **overall 20 TRUE / 20
PARTIAL / 20 FALSE**, baseline 33.3% (vs the old 83.3%). Per-stratum N=20 is
screening-grade.

## Why this exists

Search-API rankings are non-transitive: they flip by metric × query-type × judge
× harness. Vendor self-evals (Linkup, Tavily) publish rankings their own samples
can't statistically support. We want one eval whose axis matches how we actually
use search — claim verification feeding an agent's conclusion — run at enough
class balance that CIs can separate engines, and cost-normalized so "best" means
"best per dollar," not "best ignoring price."

## Core mechanism (revised per research findings)

Engines return different shapes: Exa/Perplexity/Linkup/Parallel synthesize an
answer; Brave returns snippets. Grading an engine's *own* verdict would favor
synthesis engines. So:

1. **Retrieve** — each engine answers the claim (answer if it has one, else
   top-K snippets). Identical query string per engine. Log latency + $ cost.
2. **Judge (single best judge, NOT a panel)** — *Finding #1 (Apple, Nine Judges
   Two Effective Votes):* a multi-model judge panel carries ~2 effective votes
   and the best single judge beats the full panel. So one fixed strong judge
   (Gemini 3.5 Flash; GPT-5.5 as a **disagreement flag only**, not a vote) reads
   `(claim, engine_output)`:
   - **engine-blind** — never told which engine produced the evidence.
   - **stakes-neutral** — *Finding #3 (Context Over Content):* one
     consequence-framing sentence shifts verdicts ~10pp. No contest framing, no
     "is this a good search engine" language.
   - **entailment rubric, not relevance** — *Finding #2 (ForceBench, Relevant ≠
     Warranted):* generic "is it supported?" scores 47%. The TRUE/PARTIAL/FALSE
     call checks entailment *at the claim's stated strength* across five axes:
     **relation, scope, modality, temporal, numeric**. PARTIAL = right entity/
     direction but wrong on ≥1 axis (e.g. right round, wrong amount).
   - emits verdict ∈ {TRUE, PARTIAL, FALSE, UNCERTAIN, FETCH_FAILED}.
3. **Grade vs human gold** — *Finding #1 cont.:* the judge is a measuring
   instrument, not the oracle. All 60 gold labels are **hand-set by a human
   against primary sources before any engine runs** (N=60 is small enough to
   label every item). Judge never sets gold → zero circularity.

This mirrors real use (engine retrieves → our LLM concludes), giving every engine
the identical downstream reasoner so we isolate *retrieval quality* from
*synthesis polish*.

## Pre-registration + headline metrics (Finding #4)

N=60 is a **screening** eval, not confirmatory — at ~20/stratum most engine pairs
won't separate, and McNemar lives or dies on discordant pairs. So:
- **Pre-register** before the run (via `verify-before` preregister mode): the
  gold set, the judge + prompt, the metrics, and the decision rule (e.g. "adopt
  Linkup into routing iff it beats Exa on cost-per-correct-verdict with
  non-overlapping Wilson CIs on ≥1 stratum").
- **Lead the report with:** ranks + CI overlap + **cost-per-correct-verdict**
  (Finding #4) — not raw accuracy. An engine that's 2pp better at 10× cost loses.
- Report TRUE/PARTIAL/FALSE **separately** (Finding #5) — PARTIAL is the
  unreliable stratum and averaging hides it.

## Statistics (rigor core — `stats.py`, stdlib-only, VALIDATED ✅)

Wilson 95% CI · McNemar exact (two-sided binomial) · Cohen's κ (inter-engine +
inter-rater). Self-test reproduces the memo's perp-vs-exa p=0.022, so numbers
stay comparable to the prior study. PPI (MIT, prediction-powered inference) noted
as an optional CI-tightener but judged overkill at N=60.

## Provider adapters (`adapters.py`, urllib/stdlib, registry pattern)

| Engine | Endpoint / tier | Key | Output shape |
|--------|-----------------|-----|--------------|
| Exa | `/answer` | ✅ EXA_API_KEY | answer + citations |
| Brave | `/res/v1/web/search` | ✅ BRAVE_API_KEY | snippets (no synthesis) |
| Perplexity | `/chat/completions` sonar-pro | ✅ PERPLEXITY_API_KEY | answer + citations |
| Parallel | search API (lite/core) | ✅ PARALLEL_API_KEY (env + ~/.claude.json) | cited answer |
| Linkup | `/v1/search` depth=standard, sourcedAnswer | ✅ LINKUP_API_KEY (verified 200) | answer + sources |

Adapter contract: `query(claim) -> {answer:str|None, sources:list[str], raw, latency_s, cost_usd, error}`.
Errors → verdict X, never crash the run. Cost logged per call for the headline metric.

## Phasing (validate-at-1/10 before the big run)

- **P1 ✅:** spec + `stats.py` validated offline.
- **P-research ✅:** methodology delta memo folded in.
- **P-critique (next):** `/critique model` on this spec → revise.
- **P2:** adapters (5) + blind judge + grader + run.py; smoke on a 6-claim pilot.
- **P3:** human authors + signs off balanced BI gold set (60, fresh/post-cutoff);
  pre-register; run all 5 engines.
- **P4:** full analysis — per-stratum precision, cost-per-correct-verdict ranking,
  McNemar/κ, routing recommendation.

Gate before P3 spend: critique folded in + gold set human-signed-off on shape.
