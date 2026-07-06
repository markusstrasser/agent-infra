# Metered-Spend Hard Block — Build Memo (2026-07-06)

**STATUS: SHIPPED** (2026-07-06).

Spec: `decisions/2026-06-25-metered-spend-funnel-enforcement.md` (approved A+B @ $25, override env, refuse-unpriced, single-sourced pricing). Promoted from decisions-pending this session with a `## Resolution` section.

## What shipped

### llmx (repo: ~/Projects/llmx) — DONE
- `llmx/spend_guard.py` (new): canonical guard. `is_metered_transport()` (`api`/`*-api`),
  `metered_spend_today(log_path)` (sums today's billed spend via `usage_report.PRICING`),
  `enforce_daily_cap(model, cap_usd=25, check_model_priced=True)`.
- `llmx/providers.py`: new `SpendCapError`/`EXIT_SPEND_CAP=7`; guard call wired into
  `providers.chat()` (the CLI dispatch path — the dominant 26777 metered rows) right after
  model resolution, before SDK dispatch.
- `llmx/api.py`: guard call in `LLM.chat` native-SDK branch (library callers).
- `llmx/research.py`: guard on the Perplexity agent-api path (cumulative cap only —
  `check_model_priced=False`, since it self-reports cost).
- Pricing single-sourced: `usage_report.PRICING` is canonical (already had `gemini-3.5-flash`).

**Choke-point note (deviation-worth-flagging):** the CLI dispatches through
`providers.chat`, NOT `api.LLM.chat`. Spec named `transport==api`; I guarded BOTH the
CLI path and the library path so no metered surface is missed. Metered predicate widened
to `transport == "api" or endswith("-api")` to also catch `agent-api` (research).

### agent-infra + skills — DONE
- `scripts/usage-check.py`: vendored PRICING (single-sourced) + `_is_metered` (counts
  `agent-api`) + drift-test `tests/test_usage_check_pricing_drift.py`.
- `scripts/spend-alarm.sh` + `ops/launchd/com.agent-infra.spend-alarm.plist` (option B):
  every 30 min, macOS notification at $25. Bootstrapped + running (`launchctl print`
  state=running, interval 1800s).
- `skills/hooks/pretool-cost-guard.sh`: caps aligned $500/$1000 → $10/$25.
- Decision promoted `decisions-pending/ → decisions/` + `## Resolution (2026-07-06)`.

## Shas per repo
- llmx: `6a10f68` (guard + wiring), `158626d` (tests)
- agent-infra: `05a56b5` (pricing single-source + drift-test), `db06fe3` (spend-alarm launchd + architecture.mmd), decision-promotion + this memo (final commit)
- skills: `c2845fb` (cost-guard cap reconcile)

## Test evidence
- `tests/test_spend_guard.py` — 12/12 pass (`python -m unittest tests.test_spend_guard`).
  Regression: `test_usage_accounting` + `test_dispatch_plan` 16/16 pass.
- End-to-end (fixture ledger via `LLMX_USAGE_LOG`, no real spend):
  - subscription dry-run `--subscription -m claude-opus-4-8` → `transport=claude-cli`, NOT blocked.
  - metered `llmx chat -m gpt-5.5` against a $30 over-cap fixture → `[llmx:ERROR] type=spend_cap
    exit=7`, refused before any API call.
  - `get_model_name` resolves `gpt-5.5`/`claude-opus-4-8` to exact PRICING keys (no false
    unpriced-refuse on legit calls).

## How to override
`LLMX_SPEND_OVERRIDE=1 llmx chat -m <model> ...` — deliberately set per run to bypass the metered-spend guard.
