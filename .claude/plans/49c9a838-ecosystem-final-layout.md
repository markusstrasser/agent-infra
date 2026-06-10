# Ecosystem — Final Layout

**Session:** 49c9a838 · **Date:** 2026-06-10 · **Status:** target layout (operator-directed)

Synthesis of the whole thread. Domain stays the primary cut; core/shell is a within-repo
discipline; horizontals are workspace-linked, not published; agent-infra becomes pure meta
(packages move out).

## The four layers

```
L0  META / KNOWLEDGE / HARNESS   (how agents work — NO code packages)
    agent-meta   (← renamed agent-infra) — research, decisions, rules, improvement-log,
                 hooks, agentlogs.db, dashboards, doctor, cross-project knowledge MCP
    skills/      — shared skills + hooks source
    evals/       — eval harness (MACVB home)

L1  TRANSPORT / TOOLING          (IO + LLM + search — horizontal services/libs, own repos)
    llmx (LLM transport) · emb (embed/search lib, 5 consumers) · research-mcp · biomedical-mcp
    parsers (export → JSONL) — PROMOTED to L1: phenome parses your-own sources, ext parses media
            sources → 2nd consumer satisfies the ≥2-repo gate

L2  SUBSTRATE                    (sources + claims — ONE workspace, editable-linked)
    substrate/   (NEW home — extracts the packages from agent-infra AND genome-toolkit)
      packages/corpus-core      (sources — moved FROM agent-infra)
      packages/claimcore        (biomedical claims — moved FROM genome-toolkit)
      packages/genomics-read    (typed genomic reads — moved FROM genome-toolkit)
      packages/clinical-profile (moved FROM genome-toolkit)
    corpus/      — the DATA store (sha_* dirs); separate from corpus-core the code

    The own-vs-consumed cut (2026-06-10): phenome = YOUR OWN record (health + life: genome/labs/
    medical/self-reports/psych/phenotype + your comms/calendar/contacts/code/writing). ext =
    EXTERNAL content you consume/curate (podcasts/blogs/articles + pinterest/IG/video/twitter-feed).
    Consumed media → ext, NOT phenome. Tradeoff: loses unified cross-domain search (rarely needed).
    This NARROWS phenome from the selve-era "unified 27-source manifold" → "your own health+life
    record." Your OWN social output (tweets you wrote) stays in phenome/writing — only inbound leaves.

L3  VERTICAL PRODUCTS            (each owns its shell; consumes L0–L2; core/ + shell/ inside)
    phenome (PRIVATE)  YOUR-OWN health + life record (genome/labs/medical/psych/self + comms/cal/contacts)
    ext                EXTERNAL media/content archive + search (podcasts/blogs + twitter/IG/pinterest/video)
                       ← consumed-media stuff lands here; already holds ext/pinterest + the scrapers
    genomics           WGS pipeline
    intel              investing (+ portfolio, moved from phenome)
    genome-toolkit     OPEN local plugin — "analyze your own genome" (apps/toolkit + toolkit_mcp).
                       ← THE live product path. A thin marketplace plugin that SHIPS the substrate
                       (claimcore + genomics-read + clinical-profile, corpus-core transitively) to
                       end users → substrate needs a real distribution path (git-source/published),
                       deadline = first public plugin ship.
    _synthoria-donor   PARKED (2026-06-10) — managed/remote donor service shelved + moved OUT of
                       phenome (← phenome/donor + mcp/donor + tests). Rationale: hosting protects
                       code/bulk-export but NOT the interpretive KG (leaks through query-response —
                       an extraction oracle), tool schemas are visible, and much of the KG is
                       public-source-derived (ClinVar/GenCC/CPIC). Hosting buys friction, not IP
                       protection; the moat is the data flywheel + brand/compliance/regulatory
                       standing, not secrecy. Revive only if the SERVICE (not secrecy) rationale
                       returns. `_` prefix = dormant (matches `_ancestry`).
    imagegen (new)     person-into-scene image gen (← phenome/imageengine)
    [trading RETIRED]  148 LOC skeleton, empty positions/ — delete. Salvage ibkr_client.py into
                       intel ONLY if automated execution is ever wanted (portfolio is reads-only).
    parsers            PROMOTED to L1 (see above) — no longer phenome-only once ext consumes it.
    parsers            phenome-only today → stays vertical (near/in phenome) until a 2nd consumer
```

> **Correction (2026-06-10, grounded):** the toolkit plugin and the donor service do NOT merge.
> `toolkit_mcp` is a thin transport over the substrate; the donor service is a thin (hosted, auth'd,
> compliance-gated) transport over the same substrate. They share ONLY L2, no product-core — opposite
> deployment/trust/publish models. So `genome-toolkit` (open local plugin) and `synthoria` (commercial
> donor) are SIBLING substrate-consumers, not one product. The substrate gets its OWN home; it is NOT
> "repurposed genome-toolkit."

**Dependency rule:** L3 → L2 → L1, everything uses L0. One-way. **No vertical depends on another
vertical** (phenome↔genomics only via artifacts/certificates). This is the property that makes the
ecosystem agent-interweave-able.

## The two renames

1. **`agent-infra` → `agent-meta`** (operator's call — also floated `agent-wiki`/`agent-info`).
   Recommend `agent-meta`: it's already internally titled "Meta," and it holds more than docs — the
   live harness (hooks, agentlogs, dashboards, MCP) + governance + research. "wiki/info" undersells
   the harness; "meta" captures knowledge + governance + harness. **Trigger for the rename: it stops
   hosting code packages** (corpus-core leaves).
2. **`genome-toolkit` KEEPS its name** — it's the open local plugin product. The SUBSTRATE
   extracts to a NEW home (recommend `substrate`; alts `cores`, `bio-substrate`[too narrow]).
   So this is one new repo (`substrate`) + genome-toolkit slimmed to just the plugin — NOT a rename
   of genome-toolkit.
3. **`synthoria`** = the commercial donor service. Add `-toolkit`/`-donor` suffixes only if you also
   want the open plugin Synthoria-branded (then: `synthoria-toolkit` + `synthoria-donor`); if the
   plugin stays neutral `genome-toolkit`, the donor is just `synthoria`.

## What actually moves (deltas from today)

| Move | From → To | Why |
|---|---|---|
| `corpus-core` | agent-infra/scripts/corpus/packages → **substrate/packages** | packages leave the meta repo; substrate gets one home |
| `claimcore`, `genomics-read`, `clinical-profile` | genome-toolkit/packages → **substrate/packages** | the substrate consolidates into one home |
| toolkit plugin (`apps/toolkit`) + `toolkit_mcp` | **stays in genome-toolkit** | it IS genome-toolkit's product — the open local plugin |
| `donor/` + `mcp/donor` + donor tests | phenome → **`_synthoria-donor`** (parked) | managed service shelved (hosting ≠ IP protection); move OUT to de-clutter phenome |
| `trading/` | **delete** (salvage `ibkr_client.py`→intel only if execution wanted) | 148 LOC skeleton, empty positions/, superseded by portfolio→intel |
| `imageengine/` | phenome → **imagegen** | image-gen is not the health manifold |
| `portfolio/` | phenome → **intel** | finance belongs in the investing repo |
| pinterest/insta scrapers | phenome/scripts → **ext** | acquisition belongs with the archive |
| (rename) | agent-infra → **agent-meta** | pure meta, no packages |

## What stays put (don't touch)

- **phenome** = personal-knowledge + medical/health + self-report + phenotype + claims-consumer.
  PRIVATE. The unified manifold; do not split health from search.
- **emb / research-mcp / biomedical-mcp / llmx** = horizontal tooling, own repos. Fine as-is.
- **parsers** = phenome-only; stays vertical until a 2nd consumer (the ≥2-repo promotion gate).
- **corpus** (data) stays the data store; **agentlogs/evals/skills** stay in the meta/governance layer.

## Sequencing (NOT a big bang — reviews flagged operator-tax)

1. **Low-risk vertical evictions first** (independent of the substrate move): imagegen out,
   portfolio→intel, scrapers→ext. (phenome-decomposition plan Phase 1.)
2. **Substrate consolidation** (the rename + corpus-core move): do as a workspace re-home, link by
   editable path — **do NOT publish independently** (operator-tax). Rewire consumer pyproject
   sources (phenome, genomics, intel, research-mcp) to the new `substrate/` paths. One consumer
   per commit; runtime-smoke each in a fresh env.
3. **Renames last** (agent-infra→agent-meta, genome-toolkit→substrate): mechanical, but touches
   every `.mcp.json`, path-dep, and cross-repo reference — do it as one focused pass with a grep
   sweep, after the moves settle.
4. **synthoria** extraction (plugin + donor) is business-gated (the one-product-vs-two question)
   and sequenced AFTER the substrate has stable paths so it doesn't inherit churn.

## Open naming choices (operator's call)

- `agent-infra` → `agent-meta` / `agent-wiki` / `agent-info`?
- the new substrate home → `substrate` / `cores`? (genome-toolkit keeps its name as the plugin)
- ~~synthoria branding~~ — moot for now; donor service DEFERRED, parked in phenome.
