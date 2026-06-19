# Steering vectors — session mine (2026-06-19)

**Status:** actionable synthesis from incremental steer-mining pass.
**Sources:** `artifacts/observe/2026-06-19-steer-signals.jsonl` (29 sessions, $5.35, 495 signals) merged with `~/.claude/steer-mining/probe-2026-06-17.jsonl` (819 signals) for clustering.
**Method:** `mine_steers.py --prompt-mode multi` (steer + confirmation + agent_miss) → keyword buckets + `emb pairs` on agent_miss texts (threshold 0.80).

## Mine stats (today's pass)

| Metric | Value |
|--------|-------|
| Sessions scanned | 29 (24 Jun + 5 May residual) |
| Signals | 495 (209 steer, 218 agent_miss, 68 confirmation) |
| Steer types | redirect 85, constraint 45, correction 29, disconfirmation 23, scope 21, taste 6 |
| Ledger | `~/.claude/steer-mining/scanned_ledger.jsonl` (+29 rows) |

## Recurring preference vectors (what Markus pushes toward)

Ranked by multi-label keyword hits across **1,314** merged signals:

| Vector theme | Hits | Nature | Harness response |
|--------------|------|--------|------------------|
| **Verify / measure first** | 255 | Taste + discipline | Keep — aligns with verifier-conditioned autonomy; confirmations praise "verify before claim" |
| **Gate / hook friction** | 199 | Meta-harness | Partially addressed 2026-06-17 (transform-not-block); residue = false fires + incomplete codex fleet |
| **Model / effort routing** | 168 | Taste | model-guide skill + llmx routing; Cursor = Composer 2.5 only (phenome steer) |
| **Commit boundary** | 120 | Rule tension | Global auto-commit vs explicit-request — clarify boundary, don't add hook |
| **RSI / loop ops** | 120 | Operator tax | HUMAN.md escalation, loop-stop policy, RSI-close calibration |
| **Prior context / rediscovery** | 89 | Loop miss | **Shipped** (`userprompt-prior-context.py` + Cursor rule); residuals = `existing_infra` not git-log |
| **Scope too narrow** | 88 | Planning | "Think the full loops" — planning-lifecycle contract (2026-06-18 ADR) |
| **Act now / over-ask** | 64 | Autonomy | Top blindspot `over_caution` cluster; ready-means-execute on authorized scope |
| **Codex parity** | 45 | Infra debt | Global `~/.codex/hooks.json` fleet (63 hooks) still outside parity-sync shim |
| **Architecture over-build** | 36 | Taste | "Less architecture" / no unnamed shims — constitution principle 14 |

### Confirmation signal (positive preferences)

Top confirmation themes: **execute over ask**, **complete scoped work without deferral**, **accept verified fixes**, **prefer infrastructure fixes over demoting loops**. Silence does not count — these are explicit approvals only.

## Top recurring agent_miss clusters (`emb pairs`)

| Cluster | n | Representative miss | Proposed fix |
|---------|---|---------------------|--------------|
| **continuation-misread** | 4+ | "No response requested" on "Continue from where you left off" | **HOOK** — UserPromptSubmit or Stop: continuation directive ≠ no-op (identified 2026-06-17, still firing) |
| **over-ask after scope** | 2+ | "Say the word" / "Want me to…?" after user authorized full fix | **RULE** or Stop advisory — scope-authorized work executes without re-permission |
| **codex fleet gap** | 2+ | Parity sync fixed project mirrors; 63 global `~/.codex/hooks.json` hooks unshimmed | **ARCH** — extend `codex_parity_sync.py` to global fleet or central compat shim |
| **HUMAN.md false open count** | 2+ | `agi3-status` matched `[open]` in template example, not live escalations | **SCRIPT** — template-aware grep / anchor on real headers only |
| **commit without request** | 3 | Research memo committed mid-session without explicit ask | **RULE** clarification — not new hook (auto-commit tension) |
| **concurrent git index race** | 2 | First commit silently failed (concurrent-session collision) | **ARCH** — worktree/isolation (decision 2026-06-13 isolate-by-default) |

## GOALS steward-proposals (do NOT auto-edit GOALS.md)

1. **Verify-then-act is dual, not contradictory.** Corpus shows heavy verify-first steering *and* act-now steering — but on different registers: verify claims, execute authorized scope. GOALS already has verifier-conditioned regimes; surface this split explicitly in session-analyst rubric.
2. **Operator tax includes codex-parity maintenance.** Rising friction vector as codex CLI evolves (0.137→0.141). Standing consumer, not one-shot.
3. **Loop policy is principal-owned.** Steers reject agent-imposed loop-stop rules without operator opt-in (`HUMAN.md`, RSI-close thresholds).

## Supersedes / do not re-build

| Drift/observe finding | Ground truth |
|-----------------------|--------------|
| "Build prior-context v2" | Shipped 2026-06-17 (`userprompt-prior-context.py`, `.cursor/rules/prior-context.mdc`, triage) |
| "Wire agentlogs pruning" | Shipped — `reclaim rotate` nightly via `com.agent-infra.reclaim-rotate` |
| Gate-induced friction (top-2 clusters) | Shipped 2026-06-17 — dispatch-gate auto-inject, provenance pre-write, precompact peer guard |

## Artifacts

```
artifacts/observe/2026-06-19-steer-signals.jsonl   # today's raw signals
artifacts/observe/2026-06-19-steer-mine.log        # miner stderr (budget, session counts)
~/.claude/steer-mining/scanned_ledger.jsonl      # idempotency ledger
research/2026-06-17-embed-once-validated-recurring-mistakes.md  # prior cluster baseline
```

## Next maintain actions

1. **Ship continuation-misread hook** — highest new global candidate, 2+ sessions, checkable predicate.
2. **Audit codex global hooks fleet** — quantify live failure rate in phenome/genomics via agentlogs.
3. **Fix HUMAN.md template grep** — small script fix in hutter/agi3-status path.
4. **Re-check prior-context pre-reg ~2026-06-28** — blindspot cluster should shrink; triage residuals are `existing_infra`, not hook miss.
