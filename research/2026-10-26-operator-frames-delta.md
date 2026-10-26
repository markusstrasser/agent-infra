---
title: "Operator frames: one-month delta pass"
date: 2026-10-26
status: complete
---

# Operator frames: one-month delta pass (2026-10-26)

**Verdict:** nine new frames and four sharpened ones from the operator's prompts in the month after the 2026-09-27 frames pass, now in skills `references/operator-frames.md` (skills `0e36817`). Whether the catalog helps agents at all is still untested: the blind rating artifact (https://claude.ai/artifact/AxJYPt4Kg3uq97zWza41sM) has 0 of 20 ratings.

## Method

- Input: `scripts/operator_prompts_export.py --since 2026-09-27T05:30 --packets …` over all of `~/Projects`. That yielded 1,969 operator prompts in 20 projects (genomics 510, immigration-research 379, arena 264, personal 238, agent-infra 134, others below 110), packed into 9 packets of up to 200K characters.
- Prompt: a delta brief (`.scratch/operator-meta-2026-10-26/delta_prompt.md`) with both catalogs attached, asking only for thinking a catalog-reading agent would still miss: `new`, `sharpened`, `contradicted` or `meta`, each with a verbatim quote.
- Three readers on every packet. Opus 5.5 hit a safety-classifier stop on one packet (social-conformism and IQ material); DeepSeek covered it.
- 423 items; 412 quotes verified verbatim against the packets (7 misses from DeepSeek, 1 from Astra). The parent read all 216 `new`/`meta` items plus 82 hand-picked prompts, clustered them, and checked each cluster against the catalog with `rg`.

| Reader | Calls | Prompt tok | Out tok | Reasoning tok | Verified items | In final clusters |
|---|---|---|---|---|---|---|
| Opus 5.5 high (subscription) | 8 ok + 1 refused | 950K | 156K | 108K | 164 | 9/9 |
| GPT-6 Astra high (subscription) | 9 | ~780K* | 32K | 19K | 64 | 5/9 |
| DeepSeek V4.1 Flash ultra (LithosAI, ~$0.50) | 9 | 553K | 225K | 192K | 184 | 9/9 |

*The Astra row may include two calls from a concurrent session in the usage log.

DeepSeek matched Opus on cluster coverage at about a third of the wall time (40–70 s per packet versus 140–290 s) and for about $0.50. It also produced more near-duplicates. Astra was terse and missed four clusters. For the next delta pass, use DeepSeek plus one frontier reader, then have the parent cluster.

## What changed

New: count the scarce inputs a change crowds out · aggregates can scale nonlinearly · a null needs a mechanism · the meaning gap between experts and the public · write for a capable machine reader · when work stops converging, question the requirement · check the graveyard first · interfaces are state machines that must not lie · keep the target out of the worker's brief.

Sharpened: *What does the number measure?* (14 items), *Plan on the capability curve* (17), *He brings blind spots…* (10). Reversed in part: *Instructions are code*. He now wants less prescription for current models.

`operator-deck` lets three process-group frames through to default draws (convergence, graveyard, blind brief), because they are hole-pokes rather than process.

## Not added

These are domain-specific game-design stances (randomness as reward, per-spec ratings, meta-abilities) and items already covered: the dated ledger covers "when was it knowable", firsthand observation covers folk calibration, and *Rules compose* covers institutions. Process asks were left out on the operator's 2026-09-28 rule ("thinking prompts and poking holes"). The meta items about steering itself ("divergent thinking and obvious misses") are already how `/steer` works.
