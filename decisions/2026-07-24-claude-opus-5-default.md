---
concept: model-routing
decision_date: 2026-07-24
status: active
---

# Decision: Claude Opus 5 replaces Opus 4.8 as primary Claude default

## Context

Anthropic released Claude Opus 5 on 2026-07-24 (`claude-opus-5`, $5/$25 — same price as 4.8), positioned as near-Fable intelligence at half Fable's price and the new product default on Claude Max. Our fleet still pinned `claude-opus-4-8` everywhere as the $0-subscription Claude workhorse after Fable went metered (2026-07-07).

## Decision

**Promote `claude-opus-5` to the primary Claude default** across llmx subscription allowlist, provider defaults, model-guide routing, critique/dispatch profiles, outer-loop RSI, and headless examples.

**Keep `claude-opus-4-8` on the allowlist** as the documented cyber-classifier fallback target — do not auto-upgrade explicit 4.8 pins.

**Fable 5 stays metered opt-in** ($10/$50) — only when a named edge justifies 2× price.

## Rationale

- Same price as 4.8 → no cost regression for default Claude work.
- Vendor claims SOTA / large lifts on Frontier-Bench, ARC-AGI 3, AutomationBench, OSWorld cost-efficiency — aligns with our hardest agentic coding and long-loop use.
- Most aligned recent Claude on Anthropic's behavioral audit → better fit for multi-day autonomous runs.
- Bio work: Fable blocks now route here; Opus remains the non-Mythos science default.

## Rejected

- **Keep 4.8 as default until AA remeasures** — rejected: same price, product default is 5, risk of deliberate lag on agentic coding is higher than risk of unremeasured calibration numbers (we already don't treat AA non-hallucination as a hard gate for coding).
- **Auto-upgrade all 4.8 pins including cyber fallback** — rejected: Anthropic documents 4.8 as the cyber fallback; silent upgrade would break that path.
- **Flip interactive settings.json Fable pin to Opus 5** — deferred: operator session model is a separate taste/entitlement call.

## Consequences

- All new headless Claude work: `-m claude-opus-5`.
- Prompting: strip over-verification scaffolding; prompt for concision; re-sweep effort.
- Calibration trust still cites Opus 4.8's 64% AA non-hallucination until remeasured.
- Memo: `research/2026-07-24-claude-opus-5-release.md`.

## Evidence

- Anthropic launch 2026-07-24 + models overview + prompting guide.
- llmx dry-run: `llmx chat --dry-run --subscription -m claude-opus-5 -e max` → transport=claude-cli, auth=subscription.
