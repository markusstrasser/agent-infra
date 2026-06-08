---
title: Talent-Flow Intelligence — Feasibility, Vendor Landscape, intel Fit
date: 2026-06-08
status: active
tags: [talent-flow, workforce-intelligence, alt-data, intel, exa, parallel, linkedin, compliance, buy-vs-build]
---

# Talent-Flow Intelligence — Feasibility + Buy-vs-Build

## Question

Track **talent movement within an industry** as a signal (e.g. OpenAI/DeepMind → Anthropic).
Build on people search, or buy? Where does it fit intel?

## Reframe

"People search" is the wrong primitive — it's snapshot lookup. The signal is **directed,
time-stamped transitions** between orgs. Two granularities:

1. **Individual high-signal move** (named person A → company B). Feasible NOW with Exa people
   search — the dated employment trajectory is embedded in each person record (probe below).
2. **Aggregate directional net-flow** (volume/seniority-weighted A→B over time). Needs a
   longitudinal panel; not reliably reconstructable from ad-hoc snapshot calls. This is what
   the workforce-data vendors exist for.

## Probe (2026-06-08, inline)

Query both engines: *"AI researchers who left OpenAI/DeepMind to join Anthropic"*, people mode.

- **Both return a dated multi-employer timeline inside the record.** Chris Olah →
  `Google Brain (2014–2018) → OpenAI (2018-09→2020-12) → Anthropic (2021-03→)`; Milad Nasr →
  `UMass → DeepMind (2022-05→2025-07) → OpenAI (2025-07→2026-02) → Anthropic (2026-02→)`. So for
  *individual* moves you parse history, not diff snapshots.
- **Exa = higher provenance** (real arxiv/scholar links; canonical people: Sam McCandlish, Tom
  Brown, Max Schwarzer, Adam Lerer). **Parallel = more structured ISO dates BUT shows
  LLM-enrichment smell** (templated "reduced costs 30%" bullets; a GSoC intern surfaced as a
  "move"). Don't trade on Parallel's people prose.

## Vendor landscape (verified 2026-06-08 via web search)

| Vendor | Coverage | Talent-flow native? | Price | Notes |
|---|---|---|---|---|
| **Live Data Technologies** | 80–160M, re-checked every 10–14d | Yes — `/search` on `jobs.started_at/ended_at`, public+private | **FREE in beta** (500 dl, $0.02 extra) | Has `company.ticker` → joins to intel universe. Best operator-scale fit. |
| **Coresignal** | 650–882M employee records | Yes ("track talent movement") | $49 trial → $800 → $1,500/mo; $0.005–0.196/record | Transparent self-serve, Elasticsearch DSL. |
| **Revelio Labs** | 1.1B+ profiles | Yes — explicit inflow/outflow/transition feeds, seniority/geo-segmented | Enterprise (contact sales) | Category gold standard; overkill now. |
| **Proxycurl** | — | — | **DEAD** | **LinkedIn sued Jan 2025 (N.D. Cal. 3:25-cv-00828), settled, shut down Jul 2025.** Founder → NinjaPear. Do not use. |

## Compliance (verified — load-bearing)

LinkedIn-derived data is legally hazardous to **build on / resell**, less so for **personal
research**. hiQ (9th Cir. 2022) only narrowed the CFAA question for public-page scraping; it did
NOT void LinkedIn's User Agreement §8.2 (anti-scrape/resale/broker), which **survives account
termination**. Per the Proxycurl founder's postmortem: "buying scraped data does not clean the
chain of custody." LinkedIn has acted against Apollo.io, Seamless.ai. → For Markus's personal
investing research: low risk. For any productized/resold use: do not build on LinkedIn data.

## intel fit

intel already catches **public-company exec departures** via SEC 8-K Item 5.02 (authoritative,
identity-resolved). Talent-flow is **additive** exactly where 8-K is blind:
- **Sub-executive brain-drain/gain** that never triggers a filing.
- **Private/pre-IPO momentum** — a startup pulling senior talent from incumbents pre-coverage.
Live Data's `company.ticker` joins flows to intel's ticker universe directly.

## Caveat

Noisy, **lagged** signal (LinkedIn self-reports trail real moves weeks–months); incomplete
profiles; "inflow = bullish" is a weak prior confounded by comp cycles/layoffs/visas. One input,
not a trigger. Partial-verifier regime → bounded autonomy, human reads the signal.

## Recommended next step (verify-before-build)

Don't wire anything yet. Cheapest high-information move: **Live Data free beta (500 free dl)** —
pull job-change data for ~5 intel-universe tickers + a couple of AI labs, check it's (a) timely
and (b) adds signal vs intel's existing 8-K/Form-4 detection. If it clears that bar, *then* a thin
ingester into intel's alert system. Until then, Exa people search covers individual-move lookups.

**Built (granularity #1):** `scripts/talent_flow_probe.py` — Exa structured-summary → dated
inbound transitions + flow matrix, stdlib-only, re-runnable. Demo (AI labs, since 2025-01)
surfaced **OpenAI → Thinking Machines Lab (4×)** plus xAI/DeepMind/FAIR/Mistral → TML — Murati's
lab pulling frontier talent, the canonical directional signal. SSI returned 0 (stealth profiles —
recall limit). Snapshot-derived, so it's individual moves, not net-flow volume.

Open decision (Markus's call): pursue the Live Data probe? And is this personal-research-only
(low compliance risk) or something you'd productize (changes the LinkedIn-data calculus)?

## Revision 2026-06-08 — Exa falsified for flow MEASUREMENT (granularity #2)

Ran the probe on semiconductors to test the AI-lab scarcity. Result **falsifies Exa as a
flow-measurement substrate** — and the cause is tool-fit, not data scarcity:

- **Chip incumbents** (NVIDIA/AMD/Intel/Qualcomm/Broadcom, N=50 each = 250 profiles): **7 moves
  total**, NVIDIA=2, Intel=0, Broadcom=0. **Every flow edge = count 1.**
- **Chip startups** (Cerebras/Groq/Tenstorrent/SambaNova/Etched, N=50 = 250): 18 moves, still
  **every edge = count 1** — no directional concentration anywhere.

The tell: **NVIDIA (~30K employees) yielded FEWER moves than a stealth startup.** If this were
data scarcity, incumbents would dominate. They didn't. Exa is a **relevance** engine — "joined
NVIDIA" returns the top-N most *findable* profiles, a semantically-skewed micro-sample, not the
workforce. Talent FLOW is intrinsically about volume/concentration, which a top-N relevance sample
**cannot** represent. More queries / bigger N / bigger companies do not fix this — it's structural.

**Conclusion:** Exa is good for granularity #1 (verify a named move happened) and useless for #2
(measure a flow). The cheap path is now *falsified*, which **justifies the Live Data beta probe**
— its `/search` is a panel query (`jobs.started_at` window + `jobs.company`), the right shape for
flow density. "Too scarce" was wrong: the data is abundant (Coresignal 882M / Live Data 80–160M /
Revelio 1.1B), just behind a panel API, not a search engine. "Scrape LinkedIn" stays vetoed
(Proxycurl). Next concrete step unchanged but now evidence-backed: Live Data free beta.
