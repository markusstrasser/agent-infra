# Orphaned-Generator Sweep — agent-infra/scripts (2026-06-08)

**Axis:** unnecessary (primary) + simpler (secondary). **Surface:** the 122 .py/.sh
generators in `agent-infra/scripts/`. **Disease targeted:** consumption-over-autonomy
(generation-without-consumption) — the project's #1 named failure mode.

## Method (empirical consumption test per generator)

Four consumption signals, computed mechanically, not from intuition:

1. **Wired** — referenced in `justfile`, `.claude/settings.json` (Claude hooks),
   `~/.codex/hooks.json` (Codex hooks), launchd plists, or `*-oneshot.sh`.
2. **Imported** — imported by another live script *or* by the MCP server
   `agent_infra_mcp.py` (root, outside `scripts/`).
3. **Referenced by a real consumer** — a skill, a non-inventory rule, a decision
   record, an active plan, or a memory file. (Filtered OUT: `codebase-map.md` and
   `overviews/compare/*` / `*-overview.md` — these are *auto-generated inventories
   that describe the script exists*, NOT consumers. ~all unwired scripts appear in
   codebase-map; treating that as consumption is the trap.)
4. **Invoked** — actual Bash `tool_calls` in agentlogs (507K calls, Aug 2025–Jun 02
   2026). **Caveat: raw count is misleading both ways** — most low counts are author
   `sed -i`/`git add`/`ast.parse`/`grep` *editing or fact-checking* the file, not
   *running* it; and hook-fired scripts show **0 Bash calls** despite being live.
   Counts were drilled into (distinct runs + sampled commands) before judging.

## Headline (session-level, honest)

Of 122 generators, **48 wired into recipes, 2 hook-wired (Claude+Codex), 1
MCP-imported, 4 pending an active plan.** The genuinely **orphaned-generator** set —
produces analysis/report output that NOTHING reads, on no cadence, with no consumer —
is **~17 scripts (~14% of the generator surface)**. A further ~10 are
*occasional-manual CLI tools* (not the disease) and ~6 are *one-shot migrations
already completed* (delete-eligible but harmless).

This is real but **not a crisis** — the surface is mostly wired. The disease is
present at the edges, concentrated in **abandoned measurement/analysis prototypes**
that were built, assessed, and never given a reader.

## KILL-LIST — orphaned generators, zero consumer (propose retire/delete)

Evidence format: `wired? | imported? | real-ref? | real-invocations`

| script | evidence | verdict |
|--------|----------|---------|
| `overview-usage.py` | no/no/no/1 | Dead. "Measure overview read rates" — nothing reads its output; the live `sessionend-overview-trigger.sh` calls `generate-overview.sh`, not this. |
| `overview-trigger-analysis.py` | no/no/no/2 | Dead. Analyzes `overview-trigger.log`; no consumer; not in the live hook. |
| `subagent-analysis.py` | no/no/no/1 (last 2026-03-04) | Dead. Reads `subagent-log.jsonl`, produces a distribution nobody reads. |
| `cross-project-drift.py` | no/no/no/3 | Dead. Drift report with no reader; `just`-less; last real run Apr. |
| `plan-staleness.py` | no/no/no/2 | Dead. Plan-staleness scan — `just plans`/`plan-status.py` (wired) cover plan surfacing; this duplicate has no consumer. |
| `improvement_cycle.py` | no/no/no/2 (last 2026-03-31) | Dead. Parent of the dormant finding-triage pipeline. |
| `fix-verify.py` | no/no/vetoed/6-but-all-edits | Dead. vetoed-decisions.md: "Dormant consumer… flagged for separate decommission." Invocations are `sed`/`git add` on the file. |
| `pattern-maintenance.py` | no/no/vetoed/4 | Dead. Same vetoed-decisions decommission flag. |
| `propose-work.py` | no/no/vetoed/25-but-not-runs | **Dormant** but **touched 2026-06-06 w/ tests** — see DEFER note; vetoed-flagged but actively edited 2 days ago. Move to DEFER, re-confirm with operator. |
| `claim-vulnerabilities.py` | no/no/research-only/10-edits | Dead. Epistemic prototype; only ref is a research memo; invocations are fact-checks. |
| `claims-reader.py` | no/no/research-only/22-edits | Dead. Same — epistemic-measurement prototype, no live reader. |
| `reasoning-audit.py` | no/no/decision-keep/12 | **Gray** — `2026-06-04-reasoning-quality-signal-not-built.md` explicitly *keeps* it "report-only," but the same decision flags "the real latent gap is *consumption*." Nothing reads its report on a cadence. See note below. |
| `tool-trajectory.py` | no/no/decision-keep/4 | Gray — same decision, same consumption gap. |
| `thesis-challenge.py` | no/no/decision-keep/8 | Gray — same. |
| `supervision-kpi.py` | no/no/research-only/14 (last 2026-03-26) | Dead. KPI report, no reader, cold 2.5mo. |
| `compaction-canary.py` | no/no/research-only/10 (last 2026-04-16) | Dead. Cold 2mo, no consumer. |
| `prompt-archaeology.py` | no/no/no/0 NEVER | Dead. One-shot Gemini "implied-beliefs" extractor; never run. |
| `repo-deps.py` | no/no/no/0 NEVER | Dead. "Show deps with PyPI summaries" — superseded by agents reading pyproject directly. |
| `repo-imports.py` | no/no/no/0 NEVER | Dead. Import-graph generator; never invoked. |
| `mcp-audit.py` | no/no/no/8 (last 2026-04-08) | Dead. Superseded by wired `mcp_contract_smoke.py` + `mcp-health` recipe. |
| `audit-research-memo.py` | no/no/map-only/6-edits | Dead. Memo-contract auditor; not in `research-verify` recipe path; no reader. |
| `extract-citation-ids.py` | no/no/map-only/8-edits | Likely dead — citation-ID extractor with no downstream; confirm vs research-mcp before delete. |

**The "Gray" trio (`reasoning-audit`, `tool-trajectory`, `thesis-challenge`):** kept
by an explicit 2026-06-04 decision as report-only detectors, but that decision *itself*
identified consumption as the latent gap and DEFERRED building a consumer. They are
the textbook case the sweep exists to surface: blessed-to-keep, but generating into the
void. **Recommendation: not kill — give them a consumer** (fold their output into the
`gov-report` / `/observe` cadence) OR demote to on-demand-only and drop the implicit
"these run as standing detectors" framing. Operator call.

## KEEP-LIST — has a named consumer (do NOT touch)

| script | consumer (verified) |
|--------|--------------------|
| `coverage-digest.sh` | `/observe` skill — `observe/SKILL.md` + `observe_artifacts.py` pipe it into `artifacts/observe/`. 104 distinct runs. |
| `reflect_capture.py` | live SessionEnd hook `skills/hooks/sessionend-reflect-capture.sh` in `~/.claude/settings.json`. 0 Bash calls = hook-fired (not a generator orphan). |
| `codex_hook_shim.py` | wired in `~/.codex/hooks.json`. 0 Bash calls = hook-fired. |
| `mcp_middleware.py` | imported by live `agent_infra_mcp.py:266` (`TelemetryMiddleware`). 0 Bash calls = library, not a CLI. |
| `code-review-scout.py` | genuinely invoked (`uv run … scout.py ~/Projects/intel`), 9 distinct runs through 2026-05-31. NOTE: its skill home `code-review/SKILL.md` is in `_archive/` — confirm the scout workflow still has an entry point or it becomes orphaned. |
| `postwrite-knowledge-index.py` | 36 invocations across 15 runs; referenced by knowledge-substrate decision. Confirm hook-wiring status (CLAUDE.md notes the knowledge-index hook was unwired 2026-05-29 — may have drifted to dead; re-verify). |
| `session-features.py` | 40 invocations, plan `14f5f9ac-session-detectors.md`, imports `session_detectors.py`. Active. |

## DEFER-LIST — active development or pending plan (NOT orphans yet)

| script | reason |
|--------|--------|
| `export_public_skills.py`, `migrate_skills.py`, `skill_graph.py`, `skill_description_budget.py` | All four belong to the **active plan** `2026-06-06-cross-project-skill-composition-plan.md` (2 days old). Pending-build, not orphan. If that plan dies, these die with it — tag accordingly. |
| `propose-work.py`, `autoresearch.py` | Both touched **2026-06-06 with new tests** (focused commits). Despite low real-invocation, under active dev. `propose-work` carries a *conflicting* signal (vetoed-decommission flag AND a 2-day-old feature commit) — **operator must resolve this contradiction**. |

## NOT-THE-DISEASE — occasional-manual CLI tools / completed one-shots

These appear "unwired" but are *ad-hoc utilities a human/agent runs on demand*, not
generators-without-consumers. Leave them; deleting buys nothing and removes a tool.

- Manual convenience: `reclaim.sh` (hygiene, 10 runs), `git-push-all.sh`,
  `daily-recon.sh`, `best-sync.py` (OSS sync — verify no launchd expected),
  `ts-replace.py`, `usage-check.py`, `token-baseline.py`.
- Corpus ingest (manual, last run **2026-06-01** — recent): `corpus_ingest_gwern.py`,
  `corpus_ingest_lesswrong.py`, `corpus_reference_search.py`.
- Completed one-shot migrations (delete-eligible, harmless): `selve-frontmatter-backfill.py`,
  `compress-research-index.py`.
- Repo-introspection on demand: `repo-outline.py`, `repo-summary.py`, `repo-changes.py`,
  `verify-audit.py`, `verify-subagent-claims.py`, `researcher-postmortem.py`,
  `dispatch-with-stub.py`, `parallel_mcp.py`, `parallel_search.py`.

## Ratchet (the structural fix, not a one-time cleanup)

The disease recurs because **nothing flags a generator that loses its consumer**. The
sweep was manual; the skill's own anti-pattern warns "why did a human have to notice."

**Proposed ratchet:** extend the existing `doctor.py` / a new `just orphan-check` to
compute signals (1)+(2)+(3)+(4) above and emit any `scripts/*.py|*.sh` with
wired=no ∧ imported=no ∧ real-ref=no ∧ invocations<3-in-90d. Filter the
known-occasional-manual allowlist. Report-only (do NOT auto-delete — the false-negative
rate here is high: 4 scripts in this very sweep flipped from "dead" to "keep" only after
drill-down). This gives orphaned-generator detection a standing consumer — applying the
fix to the meta layer itself.

## Honest factor

Not a 10x win. The generator surface is ~86% wired/consumed. The measured dead surface
is **~14% (17 confirmed-dead + a 3-script gray zone needing a consumer)**, concentrated
in abandoned measurement prototypes. The durable win is the **ratchet** — converting a
manual sweep that found 2 instances this session (and ~17 total) into a standing check,
so the answer to "why did a human have to notice" becomes "they don't."
