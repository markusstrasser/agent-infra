---
title: Parallel FindAll Entity Search — Live Probe + Head-to-Head vs Exa
date: 2026-06-08
status: active
tags: [parallel, entity-search, findall, exa, intel, discovery, routing, probe]
---

# Parallel FindAll Entity Search — Live Probe + Head-to-Head

## Question

Is Parallel's **FindAll Entity Search** (`POST /v1beta/findall/entity-search`, public beta)
useful for us? Distinct surface from the Parallel **Search API** / **Task API** assessed in
`search-tool-thinning-perplexity-exa-parallel-2026-06-06.md` — this is the fast, synchronous
people/company *lookup* (objective sentence → ranked `{name, url, description}` set).

## Verdict

**Marginal. Don't wire into infra now; keep as a known manual primitive for one narrow job.**

- **People endpoint: do NOT use.** Exa `people_search_exa` beats it decisively on the same query.
- **Companies endpoint: genuinely differentiated** (fast, structured, Tracxn-backed criteria→startup-set)
  but **~60–70% precision** and **aggregator URLs, not company domains**. It is a *candidate generator*,
  not a verified set — matching Parallel's own positioning ("starting set → hand off to FindAll/Task").
- **No recurring demand in its natural home.** Its strength is *private/pre-IPO startup* set-building;
  intel's investable core is *public tickers* (SEC/13D-G/congressional/short-vol via DuckDB) + Exa theme
  bursts (`harvest_opinions.py`). Entity Search fills no painful gap there. Zero private-startup-discovery
  incident history → hypothetical need → don't build (Pre-Build Check #1).

## Probes (inline, re-runnable)

Key present in `~/.zshenv` as `PARALLEL_API_KEY`. SDK not installed; used raw curl.

### Companies — `objective: "US SMR startups founded after 2018"`, match_limit=15

`HTTP 200, 1.86s, n=15`. Descriptions carry Tracxn taxonomy
(`Founded Year | Location Country | Primary Sector | Primary Subsector | Short Description`).

- **Hits (real SMR/advanced-fission startups):** Last Energy, Deep Fission, Valar Atomics, NuCube,
  Hadron Energy, Apollo Atomics, Antares Industries, Serva Energy, Aureon Energy. (~9/15)
- **Misses (precision failures):** Marathon Fusion / Kronos Fusion / US Fusion Power (fusion ≠ SMR
  fission), **Mersenne Law LLP** (a law firm — LinkedIn name match), **Protect Nuclear NOW** (advocacy
  org, not a startup). (~6/15)
- URLs are `linkedin.com/company/*` and `platform.tracxn.com/...?utm_source=parallel` aggregator pages,
  **not** company homepages.

### People — `objective: "founders/CEOs of US SMR startups"`, match_limit=12

`HTTP 200, 3.37s, n=12`. **Acronym collision**: the concept "small modular reactor" collapsed to the
string "SMR". Returned **SMR Research** (financial research firm), **SMR Performance Consulting** (sports
medicine / self-myofascial release), **SMR Distribution**, **SMR Future LLC**. ~4/12 genuine SMR founders.

### Exa head-to-head — `people_search_exa("founders and CEOs of US SMR nuclear startups")`, n=12

**~11/12 genuine** advanced-nuclear founders, semantically correct (no string-match noise), with rich
inline enrichment (funding, headcount, founding year, HQ):
Jacob DeWitte (Oklo), Liz Muller (Deep Fission), Cristian Rabiti (NuCube), Wesley Deason (Emerald
Nuclear), Richard Taylor (ONE Nuclear), David Dabney (StarCore), Jonathan Webb (The Nuclear Company),
Nicholas Leone (Vulcaris), Anand Gangadharan (nVision), David Kropaczek (Veracity), Bill Stokes (First
American Nuclear), Brian Matthews (AMPERA). Exa wins the people axis outright.

> Note: Exa `company_research_exa` takes a single `companyName` (enrichment), NOT criteria→set. So Exa has
> no *direct* equivalent of Entity Search's **companies discovery** mode short of
> `web_search_advanced_exa` + `outputSchema`. That criteria→structured-startup-set is the one primitive
> Entity Search adds that we don't already have in a single cheap synchronous call.

## Where it would fit (if demand recurs)

The only clean slot: **fast private-company landscape mapping around a public thesis** (e.g. "private SMR
players adjacent to public OKLO/NNE"). If that recurs ≥2–3×, the right build is a thin
`intel/tools/entity_set.py`: Entity Search (broad candidate set) → existing intel verification/dedup →
dossier. Consistent with the 2026-06-06 routing rule ("escalate to Parallel for entity collation /
exhaustive set building") — Entity Search is the cheap synchronous front-door to that job. Until then:
manual curl, no wrapper.

## Caveats

- Pricing: doc says "priced per request… much cheaper than FindAll" but the exact entity-search rate is
  not on the page (adjacent Search API is $0.005/req). Not load-bearing here — precision/fit decided this,
  not cost.
- Public beta; request/response shape may change (30-day notice promised).
- Scope: professional-context only; not for employment/credit/housing decisions (vendor compliance note).
