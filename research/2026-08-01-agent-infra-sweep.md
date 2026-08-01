---
title: Agent-infra frontier sweep — 2026-08-01 (3d delta)
date: 2026-08-01
---

# Agent-infra sweep — 2026-08-01

Delta since `2026-07-29-agent-infra-sweep.md`. Freshness DUE clear.

## Consumed this window

1. **llmx GPT-5.6 cut** — usage-check vendored PRICING re-synced; drift-test green.
2. **test_health nodeid capture** — overnight 12-fail @531s left no names; sentinel now records `failed_nodeids` in jsonl.
3. **agentlogs sticky event_id** — already shipped 2026-07-29; still green.

## Observe 2026-08-01 (Tier-0)

- Correction rate 0.68% / mixed autonomy_reading (thin — do not over-steer)
- Triangulated HIGH: over_caution + rediscovery (same residual classes as 07-29)
- Genomics failures (BIOCONDA image, Modal numpy/flash_attn) → operator memo only this package

## Open local (low urgency)

- Vendored pricing remains a knowing exception to invariant #9 (separate env) — drift-test is the enforcer
- zsh-env:parse-error ×3/7d below promote threshold; cross-harness shell checks healthy

## Surveillance status

- trending-scout + this sweep written today → freshness DUE cleared

