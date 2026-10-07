# GPT-6 Astra and Fable 5.1 migration

**Verdict:** The coding-agent configuration selects Astra and Fable 5.1 across
the inspected repositories. This follow-up migrates remaining general agent
launchers and repairs request, accounting and registry defects. Configuration,
mocked execution and parser checks establish compatibility; they do not establish
live provider access, workload quality or scientific qualification.

## Scope and authority

The user explicitly requested `$openai-docs migrate this project to GPT-6 Astra`
and named genomics, arc-agi, personal and other relevant repositories. This follows
the [completed prompt/skill cleanup](2026-09-05-astra-context-pruning.md) prompted
by both supplied articles. Scientific policies, evaluation treatments, existing
cost tiers and Claude subscription-only authorization remain applicable.

Sources fetched on 2026-09-05:

- [OpenAI migration guidance](https://developers.openai.com/api/docs/guides/latest-model)
  and [Astra model contract](https://developers.openai.com/api/docs/models/gpt-6-astra).
- [OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching),
  checked with the installed SDK's usage-field definitions.
- [Fable 5.1 overview](https://platform.claude.com/docs/en/models/fable-5-1/overview)
  and [Claude plan rules](https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan).
- Installed CLI help, exact model/effort fields, call-site traces and synthetic
  request/ledger fixtures. No credentials or private data were needed.

## Repository disposition

Global Codex selects `gpt-6-astra` with `max`; global Claude selects
`claude-fable-5-1[1m]` with saved effort `medium`. Explicit launcher/task arguments
still take precedence. Installed Codex is 0.147.0 and Claude Code is 2.1.261.
The final safe scan parsed 29 existing Codex/Claude configuration files across
14 immediate project roots and found no local model, effort, profile or direct
model-environment override. The scan covered `.codex/config.toml` and
`.claude/settings{,.local}.json`, not arbitrary task-level model selections.

| Surface | Applied migration or verified disposition |
|---|---|
| agent-infra | Codex dispatcher/scout defaults select Astra. Research agent preload resolves to the current shared research skill. Cost readers import the llmx calculation. |
| shared skills / llmx | Astra defaults and alias handling; unsupported request parameters removed; effort preserved, with none/minimal mapped to low. Fable 5.1 subscription route registered. Current guidance distinguishes subscription allowance from API prices and preserves earlier claims in a linked history. |
| genomics | Editor configuration inherits globals. Explicit GPT-6 selections retain the existing subscription/context-size boundary. Scientific verifier policy and donor outputs are unchanged. |
| arc-agi | Portfolio worker uses current Codex flags and Opus 5; general paper-discovery helpers select Astra. Current Opus/Fable probe definitions use 5/5.1, with historical probe receipts preserved. |
| personal | Editor configuration inherits globals; no local coding-model override or launcher blocker found. Health-analysis model batteries remain separate application contracts. |
| intel | Editor configuration inherits globals. Alias helper consumes the canonical llmx registry and checks literal model names. Domain agents and financial-analysis models retain their existing roles. |
| anim-workbench | Outer-loop digest uses Astra low; architecture uses Astra medium. Existing Opus/Gemini/Composer and evaluation lanes retain their roles. |
| research-mcp | Coding-agent configuration inherits globals. The MCP application remains a Google-backed service; changing its model field to an OpenAI/Claude ID would require a provider migration. |

## Request and accounting corrections

In a synthetic ledger, four 300K-input/10K-output Astra requests were estimated at
$14 and passed the old $25 cap calculation. Standard long-context pricing gives
$27. This was an accounting regression probe, not an observed purchase. The shared calculation
now prices each request before aggregation, including cache reads/writes and
reasoning already contained in output totals. When Astra cache-write counts are
unreported, the guard and request-level reports use the cache-write rate as a
conservative estimate and label that assumption. Native streams persist returned usage and
failure/interruption status. Unreported token totals remain unknown costs; the
guard and reports flag incomplete accounting while still enforcing a known
subtotal above the cap. Doctor and the existing spend-alarm consumer surface
that degraded state. A subscription stream that lacks CLI support fails
before SDK construction, preventing silent API billing.

Agent-infra now declares its existing sibling llmx checkout as an editable Python
dependency. Its monthly/session ledger readers use the same public cost helpers;
the vendored rate table and its drift test are replaced by output-level fixtures.
Whole-session shadow estimates remain labeled approximate because aggregation
loses request boundaries and cache categories. The option record is
`.claude/plans/01a07099-astra-readiness.md`.

## Remaining boundaries

- The optional OpenRouter default remains blocked by the existing unpriced-model
  guard. Its [Astra endpoint registry](https://openrouter.ai/api/v1/models/openai/gpt-6-astra-20260903/endpoints)
  exposes different rates for Flex, standard, US and Fast routes. An unconstrained
  provider route cannot safely inherit the native OpenAI price tuple; enabling it
  needs a provider-routing/accounting contract. No such caller migration is made.
- Fable is included within Max's Fable allowance, up to 50% of shared weekly
  usage. That does not authorize credits beyond the allowance or metered API
  fallback. Headless dry-runs establish routing only; no Fable/Astra runtime
  canary or scientific run was performed. The single independent review used
  the existing Cursor subscription route, with no API-key or provider fallback.
- Named scientific/evaluation pins, Intel financial-analysis tools, personal's
  health critique battery, research-mcp synthesis/OCR and Cursor grinders were
  not relabeled as migrated applications. Each has a separate role or provider
  contract. No new automations or production outputs were created.

## Independent review disposition

One Cursor Composer 2.5 review covered a frozen packet of 37 changed paths and
three context files. The native request completed successfully in 168 seconds;
all requested paths were accounted for and source hashes still matched after
review. Coverage enumeration is reviewer-reported, not proof of reasoning quality.
The packet SHA-256 is `1fe615f0b313847a5478fc53b8be6f162d1c2682985b52f391dc54e16e41d15e`.
Local receipts: `/tmp/astra2-review-report.md`, `/tmp/astra2-review-manifest.json`
and the unmodified response `/tmp/astra2-review-raw.json`.

The parent checked both MEDIUM candidates:

1. **Genomics Astra API advisory cost: no reachable migration regression.**
   `bundle_adjudicate._dispatch_model_call` validates policy before calling
   `_model_call`; the latter has no other production caller. The current policy
   admits Sol, Gemini and Opus, and rejects Astra. The prior fallback already
   selected the API for unrecognized OpenAI models; this patch enables the
   existing subscription route for small explicit GPT-6 prompts. The admission
   regression test now proves refusal before execution for Astra on both sides
   of the context threshold. Scientific admission and its local advisory-cost
   calculator remain a separate qualification task; adding a flat Astra price
   tuple would not correctly implement its cache/tier contract.
2. **Ordinary rollups versus the conservative cap: fixed.** Request-level
   reports now use the same conservative cache assumption as the guard and
   explain it in text and structured output. Whole-session shadow estimates
   remain explicitly approximate because they lack per-request boundaries.

## Validation and commits

Completed validation:

- llmx: the full suite passed with 159 tests and 84 subtests; one optional live
  test was skipped. After the final report-consistency change, 40 affected
  accounting/guard tests and 16 subtests passed. Agent-infra's 16 report/harness
  tests also passed, including the same missing-cache-write ledger across
  every request report and the cap. No unaffected full suite was repeated.
- `just harness-eval`: passed, including 214 hook smoke checks, drift, 29
  prior-context tests, 13 orientation/inventory tests, seven observe-gate tests,
  nine transcript tests, approval coverage and stale-pointer checks.
- ARC: 41 focused tests passed across worker dispatch, paper-discovery defaults
  and mocked transport-health probes. Current Codex CLI accepted the replacement
  flags; the removed `--full-auto` spelling failed its parser as expected.
- Genomics: 13 transport/admission tests passed, followed by all 28 quorum tests
  in the native commit gate. Its remaining precommit gates also passed. The hook
  included two generated configuration fingerprint updates tied to this script;
  their diffs contained no scientific data or policy change.
- Intel: 30 mocked registry tests and read-only installed-registry checks for
  Astra and Fable 5.1 passed. Anim: eight mocked launcher calls across API/Codex
  branches, Claude key-stripping, shell syntax and JSON checks passed.
- Shared model-guide and llmx-guide passed the repository's native skill
  validator with zero errors or warnings. Archived guidance sections were
  checked byte-for-byte. Subscription dry-runs selected the exact Astra and
  Fable 5.1 CLI routes without a fallback.

Applied commits (all on main):

| Repository | Commit | Change |
|---|---|---|
| agent-infra | `b1dfd79` | Astra dispatcher/scout defaults (existing peer change, verified) |
| agent-infra | `50d870b` | Current research skill preload |
| agent-infra | `e53679a` | Shared llmx cost authority, reports and degraded-accounting consumers |
| llmx | `c236ae0` | Astra registry/defaults and base rates (existing peer change, verified) |
| llmx | `45202c2` | Canonical model registry export and CLI-availability reporting |
| llmx | `c277468` | Astra request/usage contracts, conservative cost reports and regressions |
| skills | `1384503`, `58f15ac` | Current Fable access/role guidance with preserved history |
| arc-agi | `39e8f8ca` | Coding/discovery launcher migration and tests |
| genomics | `cf8b1110a` | GPT-6 transport compatibility with unchanged policy admission |
| intel | `54e55ccd` | Canonical registry consumer and literal-name checks |
| anim-workbench | `4fa666e` | Astra review lanes and matching instructions |

All changed code/guidance paths were clean after these commits. Five temporary
worktrees belonging to this task were removed only after their changed sources
were backed up and compared with the integrated commits, including the later
review fixes. Other worktrees and peer edits were preserved. The only llmx
status difference was removal of its untracked temporary-worktree directory;
the five preexisting plan deletions were untouched. Local backup/proof artifacts
are under `/tmp/astra2-completed-worktrees/`.
