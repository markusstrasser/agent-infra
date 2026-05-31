---
title: Search-Engine Verification Eval — Design Spec
date: 2026-05-31
status: draft (pre-critique, pre-research-synthesis)
---

# Search-Engine Verification Eval — Design Spec

Multi-provider bake-off for the search APIs we route through (Exa, Brave,
Perplexity, + candidate adds Tavily, Linkup). Grafts the **statistical rigor**
of the existing N=60 Gospel-reader study (`publishing/research/2026-05-19-engine-reliability-metric.md`)
onto the **standardized-harness + class-balance** discipline of the better
external benchmarks (michaeldinzinger/search_evals). Goal: a reusable harness
that produces a *decision* ("route claim-type X to engine Y"), not a vanity ranking.

## Why this exists

Every external search-API benchmark is non-transitive: rankings flip by
metric × query-type × judge × harness (Perplexity wins SimpleQA-style answer
accuracy; Exa wins our N=60 verification precision). Vendor self-evals
(Linkup, Tavily) publish rankings their own samples can't statistically
support. We want one eval whose **axis matches how we actually use search**
(claim verification feeding an agent's conclusion), run at enough N and class
balance that the CIs can separate engines.

## The two design grafts

| From | We take | We fix their weakness |
|------|---------|----------------------|
| Our N=60 study | Wilson CIs, McNemar pairwise, Cohen's κ (inter-engine + inter-rater), per-claim ledger, source-graded gold | N too small; 83% TRUE-skewed → baseline swamps CIs; bespoke/unreplicable |
| michaeldinzinger/search_evals | Standardized provider-adapter harness (drop-in engines), public-suite discipline, blind judge | Measures generic QA, not our verification axis |

## Core mechanism: blind judge neutralizes synthesis-vs-retrieval asymmetry

Engines return different shapes: Exa/Perplexity/Linkup synthesize an answer;
Brave/Tavily(raw) return snippets. Grading the *engine's own verdict* would
unfairly favor synthesis engines. Instead:

1. **Retrieve** — each engine answers the claim (answer if it has one, else
   top-K snippets). Same query string per engine.
2. **Judge** — a *single fixed, cross-model* judge (NOT one of the engines —
   default Gemini 3.5 Flash; verify against GPT-5.5) reads `(claim,
   engine_output)` **blind to engine identity** and emits a verdict ∈
   {TRUE, PARTIAL, FALSE, UNCERTAIN, FETCH_FAILED}.
3. **Grade** — verdict vs **pre-established gold label** (human + primary
   source, set *before* any engine runs; judge never sets gold → no circularity).

This mirrors real use (engine retrieves → our LLM concludes) and gives every
engine the identical downstream reasoner, isolating *retrieval quality* from
*synthesis polish*.

## Class balance (the fix that makes N=60 mean something)

Existing set: 50 TRUE / 9 PARTIAL / 1 FALSE → random-TRUE baseline 83.3%,
which sits inside every engine's CI (can't reject "always-TRUE = Exa").

New set: **20 TRUE / 20 PARTIAL / 20 FALSE** → baseline drops to 33.3%, CI
half-width shrinks, McNemar gets discordant pairs to work with. This is the
single change that converts "routing hints" into "rankings with power."
(Memo's own prescription, §2 statistical caveats.)

## Grading scale (from the N=60 study, retained)

Verdict mapped to T/P/F/U/X. Two scores reported:
- **strict**: verdict == gold exactly.
- **conservative**: under-claim allowed (U or P on a TRUE gold = acceptable;
  models hedging is not penalized as hard as contradicting).

## Statistics (rigor core — `stats.py`, stdlib-only, validated offline)

- **Wilson 95% CI** on strict precision per engine.
- **McNemar exact** (two-sided binomial on discordant pairs) for each engine pair.
- **Cohen's κ** pairwise between engines (are they independent or correlated views?).
- **Inter-rater κ** on a re-graded subset (judge stability).
- Report per-stratum precision (which engine for which claim type) — the memo's
  finding that "qualitative per-stratum routing > strict ranking" holds.

## Provider adapters (`adapters.py`, urllib/stdlib, registry pattern)

| Engine | Endpoint | Key present? | Output shape |
|--------|----------|--------------|--------------|
| Exa | `/answer` (verify_claim path) | ✅ EXA_API_KEY | answer + citations |
| Brave | `/res/v1/web/search` | ✅ BRAVE_API_KEY | snippets (no synthesis) |
| Perplexity | `/chat/completions` sonar-pro | ✅ PERPLEXITY_API_KEY | answer + citations |
| Tavily | `/search` include_answer | ❌ **needs TAVILY_API_KEY** (free 1k/mo) | optional answer + results |
| Linkup | `/v1/search` sourcedAnswer | ❌ **needs LINKUP_API_KEY** (free $5/mo) | sourced answer |

Adapter contract: `query(claim:str) -> {answer:str|None, sources:list[str], raw:dict, latency_s:float, error:str|None}`.
Errors (timeout, 5xx, empty) → verdict X, never crash the run.

## Open decisions (for the human)

1. **Claim domain** — what do we test on? Determines validity.
   - (a) Rebalance the existing **sacred-music/art-history** set (cheapest; tests philology/enumeration).
   - (b) **Scientific/research verification** (genomics, ML claims) — matches agent-infra's *actual* search workload. ← principled default for "which engine for us."
   - (c) **Business-intelligence/multi-entity** — matches Linkup's pitch; fairest test of *their* claim.
   - (d) Mixed (20 per domain across 3 domains, N=60+).
2. **Provider scope / keys** — provision Tavily + Linkup free keys (user action), or validate on Exa/Brave/Perplexity first?

## Phasing (validate-at-1/10 before the big run)

- **P1 (this commit):** spec + `stats.py` validated offline. ← done
- **P2 (post research + critique):** adapters + blind judge + grader + run.py;
  smoke on Exa with a 6-claim pilot.
- **P3:** author balanced gold set (60, chosen domain); run 3 live engines.
- **P4:** add Tavily/Linkup once keyed; full run; per-stratum + ranking analysis.

Gate before P3's spend: research synthesis (newest eval methodology) folded in,
`/critique model` on this spec, gold set human-signed-off on shape.
