---
title: Skill usage & value audit — 23d window, both channels, transcript-verified
date: 2026-07-06
status: active
tags: [skills, usage, agentlogs, audit, context-budget, rsi]
---

# Skill Usage & Value Audit — 2026-07-06

Operator question: "look at all our main skills and how they're used (agent logs) and how we could improve them / make them more valuable?"

Method: [DATA] agentlogs.db (window 2026-06-13→07-06, 23d, 22,998 sessions) for both usage channels; [DATA] transcript sampling of 14 invocations across 7 projects (value audit); [DATA] on-disk structure audit of the 10 largest SKILL.md files; [INFERENCE] verdicts and proposals. Three fable-low subagent reports feed this memo (session 5f576d8b); key evidence is folded inline.

## 1. Usage ground truth — two disjoint channels

**Channel A — model-invoked (Skill tool, 447 calls, all vendor=claude):**

```sql
SELECT json_extract(tc.args_json,'$.skill'), COUNT(*), COUNT(DISTINCT s.session_pk)
FROM tool_calls tc JOIN runs r ON tc.run_id=r.run_id JOIN sessions s ON r.session_pk=s.session_pk
WHERE tc.tool_name='Skill' GROUP BY 1 ORDER BY 2 DESC;
```

Top: decide 60 (39 sess, 11 projects), research 52 (34/14), critique 45 (35/13), rsi 41 (35/13), model-guide 40 (28/12), observe 23, code-review 22, brainstorm 19, modal 17, eval 16, execute 12, improve 11. Five skills = 53% of all calls.

**Channel B — user-typed slash commands (`<command-name>` in user events; never logged as Skill calls):**
/compact 382 (built-in), **/loop 195, /rsi 63, /improve 54**, /goal 18, /effort 18, **/debug 14**, /decide 6, /model-guide ~9, /modal 4, /execute 3, /code-review 3.

Consequences: (a) any usage analysis from `tool_calls` alone undercounts typed-first skills (debug, loop, improve, rsi) — /debug looked dead in Channel A but has 14 typed uses; (b) Codex/Cursor consume skills as docs — zero direct usage signal (same caveat as the 06-13 audit).

**Channel split by session role:** ~90% of Skill calls come from SUBAGENT sessions (decide 57/60, model-guide 39/40, critique 41/45, observe 23/23, improve 11/11 subagent-side). Main sessions reach skills via typed commands or not at all. Skills are de facto the fleet's shared procedure memory; main-session auto-invocation is the weak edge — consistent with the 06-15 finding (/research typed in ~163 sessions/60d, Skill-invoked 29%).

**The one measured routing fix worked:** /research description-ad rewrite + PreToolUse gate (improvement-log 2026-06-15) took research from 69 invocations/3mo to 52/23d, now #2 overall. Pattern validated: description leads with trigger words + "INVOKE BEFORE ad-hoc X" + a narrow PreToolUse nudge.

## 2. Live defects found (transcript/on-disk verified)

### 2.1 rsi mechanical spine DEAD since 2026-06-18 (P0 — rule #22 class)
[DATA, verified on-disk by value-audit agent]
- `~/.claude/close-queue/`: **132 close-intent.v1 files unprocessed** (2026-06-17→07-06, `processed:false`).
- `reflect_session_close.py --drain` → "0 digest(s)", intents stay unprocessed. Last real `reflect.close-digest.v1`: **2026-06-18**; everything after is thin `close-ack.v1`.
- Skill Step 1 does `tail -1 reflect-close-digest.jsonl` → always returns an ack, never a digest → Steps 2-3 (route by `real_issue_kinds`, `fm.py attach-evidence`) structurally cannot fire. 0/3 sampled sessions executed the designed arc.
- Downstream starvation: `loop_funnel.rsi_pending()` keys on `invoke_skill` (digest.v1-only) → act-drain gets no new RSI items.
- Value is currently salvaged by the model's generic close diligence (e.g. caught the stale "NVDA NOT HELD" DB error, session 81b0e889) — the skill text describes machinery that doesn't run.

Fix shape: repair the drain (root cause in reflect_session_close.py), fail-loud denominator line ("N intents read, M digests written, K skipped: <reason>"), Step-1 filter by `schema==digest.v1 AND session_id==current` (or split acks to a separate file), and reconcile the redundant manual attach-evidence step with the automated fm-evidence capture (1,674 rows, auto-fed).

### 2.2 critique triage can emit below-floor budgets → silent axis skip (recurring)
ad6ba340: triage wrote budget 480s < 600s axis timeout → all 4 axes skipped, "failed exit 2", one wasted rerun. Known-issue class from 2026-06-18 recurring. Fix: `review_gate triage` refuses budgets below the profile's axis timeout (config-time hard error).

### 2.3 research-ops: 4 of 6 dispatch-mode reference pointers broken
`references/{prompt-construction,verification-procedure,paper-reading-dispatch,agent-system-prompt}.md` cited but absent (live under `research/references/` — lineage split). 0 invocations/23d + `disable-model-invocation:true` → blast radius ≈0, but dead pointers. Fix: symlink/copy the 4, or fold dispatch mode back.

### 2.4 Dead duplicate: `observe/scripts/session_shape.py` (786B stub) beside live `session-shape.py` — delete stub.

### 2.5 Description-index "OVER" (8282/8000) is a broken METER, not a real overflow
[DATA, dead-triage agent] `skills_budget.py` (via `surface_gates.py`) sums raw `description:` lines alphabetically and ignores `disable-model-invocation: true` — but 899 chars belong to the 4 deliberately explicit-only skills (fa0ce09), so the **effective model-visible index ≈7383 (92%)**. Claude Code doesn't clip at 8000 at all (full 45-entry list loads; cf. `cc-loads-claude-md-in-full`); the ceiling is Codex-side, and Codex mounts measure **7990/44 — 10 chars of headroom** (genuinely tight). Cumulative-order check: the past-8000 tail (writing-style/x-api/youtube-transcript) was **actively used** in-window; every zero-usage skill sits inside the ceiling → clipping explains no dormancy. Fix the meter (report `effective_model_index`, keep raw as the conservative Codex number) + trim the 3 fattest descriptions for Codex headroom (interface-thinking 295, diagnose 292, debug 288; median ~170). The 06-13 lesson stands: description-trim, never deletion (hard-cuts were executed then same-day REVERTED, commit e39991a).

## 3. Value verdicts on the top-5 (14 transcript samples, 7 projects)

**Pure ceremony: 0/14** — when a skill loads, the model uses it. Structural findings:

| Skill | Verdict | Key evidence |
|---|---|---|
| decide | Load-bearing at **Phase 0**; advertised escalating cross-model adversarial arc ran **0/4** — grounding dissolves/reframes decisions first (correct scope-gate behavior, oversold centerpiece). 1 friction: Phase-0 inventory **by grep** asserted a false "transport absent" (user rescue; violates never-trust-regex) | e4f4b7be → NO-BUILD ADR 61d3d20; 024fca68 grep failure |
| critique | Healthy; **premise-scout is the MVP** (falsified proposals against live config — caught a retracted-panel target). Budget footgun §2.2 | ad6ba340: 34 claims → 21 CONFIRMED, 13 INCONCLUSIVE |
| rsi | **Broken spine** (§2.1); value salvaged ad hoc | 3/3 arc-broken-but-value-salvaged |
| improve | **Healthiest** — deterministic harvest with denominators, verified dead-infra finds (phantom `just blindspot`, dead launchd job), correct verifier-boundary routing | d40e1326, a09ef6a1 (commit 0c3b0a8) |
| model-guide | Load-bearing reference; **crisply changed the pick in 2/3** (killed an unneeded LLM dependency; pinned opus-low key-stripped + cross-lab alternation) | 8f88ab03, 96179e0b |

## 4. Context economics (structure audit, 10 largest skills)

`chars_loaded/23d = SKILL.md bytes × load events` (typed uses also load full body → lower bounds):

| skill | bytes | loads/23d | chars loaded | lean est. | savings/23d |
|---|--:|--:|--:|--:|--:|
| improve | 41,033 | 65 (11+54 typed) | 2.67M | ~25K | ~1.04M |
| critique | 41,185 | 45 | 1.85M | ~31K | ~0.45M |
| model-guide | 42,472 | 40 | 1.70M | ~27K | ~0.60M |
| research | 32,077 | 52 | 1.67M | ~25K | ~0.36M |
| eval | 64,147 | 16 | 1.03M | ~26K | ~0.61M |
| observe | 39,406 | 23 | 0.91M | ~32K | ~0.16M |
| modal | 36,843 | 17 | 0.63M | ~24K | ~0.22M |

≈10K tokens/invocation deferrable across the hot 5; ~2.5-3M chars/23d total. Every subagent spawned under a skill-loaded session pays the loaded body again. eval is the extreme: 64K, **no references/ dir**, ~110 lines of folded research memos + inline arXiv evidence ("2026-06 frontier adopts", "Confirmed by DeepSWE/LifeSciBench") — self-labeled reference-grade. Ranked moves (structure-audit agent, full detail in session artifacts): 1) eval → extract folded memos/evidence to references/ (~38K/load); 2) improve → defer harvest 2a-2i detail + extract 30-line Live-State bash heredoc to a script (Native-First); 3) model-guide → defer dormant-Fable section + validation checklists; 4) critique → retire FIXED Known-Issues entries + dedup anti-patterns table vs references/; 5) modal → move checkpoint code blocks to references/checkpointing.md + dedup Durable Gotchas.

Prior-art reconciliation: skill-consolidation (42→18, 2026-04) largely SHIPPED; 06-13 trim audit settled (reversed; description-trim is the lever); mattpocock context-load cost model noted 06-19 but never applied as a body-size pass — §4 operationalizes it.

## 5. Skill amnesia — compaction eats loaded skills mid-arc

[DATA] Sessions that invoked a skill and later compacted (vendor_kind='compact_summary' after the call): decide 16/39, rsi 17/35, critique 19/35, research 14/34, model-guide 14/28, modal 8/10, execute 8/10, **loop 6/7**. ~40-85% of skill-using sessions lose the loaded instructions to summarization; long-arc skills (decide, improve maintain, loop) are most exposed. No skill externalizes arc state today. Levers already in-house: PreCompact stdout = summarizer customInstructions (compact-is-headless-scriptable); state-externalization lens (Harness-1).

## 6. Feedback loops that exist but don't run

- **Known Issues / append-skill-memento.sh**: 3 skills have the section (~1 entry each); 0 invocations in 23d of tool calls. Skills don't learn from their own failures without a human-triggered audit.
- **skill_usage_watch** (launchd, 2h): queues /execute+/critique invocations for semantic skim — the only standing per-skill quality loop, 2 skills only.
- **Two telemetry stores**: `~/.claude/skill-triggers.jsonl` (3,581 rows, feeds the watch) ∥ agentlogs tool_calls. Overlapping counts of the same invariant; agentlogs is richer (joins, roles, projects).

## 7. Dead/dormant skill triage

[DATA+INFERENCE, dead-triage agent; trigger counts are LIKE-grep candidate upper bounds — grep locates, doesn't decide]

| skill(s) | verdict | evidence |
|---|---|---|
| execute, leverage, research-ops, interview-prompt | **BY-DESIGN explicit-only** | fa0ce09 (06-15) flipped `disable-model-invocation:true`; zero/cliff usage is the flip working, not decay |
| goals | INVISIBLE-BY-DESIGN | `friend-sync.sh:189` SKIP_DIRS excludes it; also name-collides with the /goal command (18 typed uses) — mount it or archive it |
| outer-loop | NOT-A-SKILL | SKILL.md deleted d36c9f5 (de-scoped to executable record) — drop from skill counts |
| **interface-thinking** | **MISSED-ROUTING, confirmed instance** | created 06-18; 0 fires, 0 doc wiring; the 2026-07-04 operator #g ("better representation for MY understanding… why didn't you invent this yourself?") is verbatim its trigger — the miss got institutionalized as a wakeup-cadence rule instead of routed to the skill |
| **diagnose** | **MISSED-ROUTING + Codex-invisible** | created 06-19, never synced to `~/.agents/skills`; 0 fires vs ~10 clean trigger-candidate sessions; red-loop-first spine NOT covered by any always-loaded rule |
| verify-before | **INTERNALIZED** | probe mode = global rule #8; status mode = `probe-primitive-first.md`; preregister = context-budget-orchestration + prereg practice; ~15 trigger-candidate sessions, 0 fires, lifetime 1 → demote to explicit-only (reverses fa0ce09's keep-ambient on 3 more weeks of evidence) |
| sweep | INTERNALIZED (reactive core) + NO-DEMAND (proactive) | class-sweep = global rule #21 + critique-to-hooks step 2; repo scans run via debug-until-dry recipes |
| census-data, oura-ring, neurokit2, manim, scientific-drawing, corpus, entity-management, life-science-research, x-api, google-workspace, youtube-transcript, data-acquisition | KEEP-DORMANT | deliberate-invoke domain capabilities; workload absent in window; 06-13 Revisions rule: doc-referenced = wired by definition |
| dataset-register | KEEP-DORMANT (merge RETRACTED) | doc-ref cross-check: wired in 3 repo CLAUDE.mds (research-misc/immigration-research/iq-sex-differences) — documented capability, not merged/cut on usage alone |
| illustration-gen | RETIRE candidate (sign-off) | lifetime 0, zero wiring, paid API, adjacent coverage exists |
| analyze, de-slop, orchestrate, cursor-agent | KEEP (alive) | 4/6/6/4 window uses |

## 8. Proposals (ranked)

P0. **Fix the rsi drain pipeline** (§2.1) — root cause + fail-loud denominators + Step-1 schema/session filter + attach-evidence reconciliation. Rule #22 class; the #4 skill by usage describes machinery that hasn't run in 18 days.
P1. **Progressive-disclosure pass on the hot 5** (§4) — one skill per commit, ~10K tokens/invocation saved. Shared skills → needs sign-off.
P2. **Fix the budget meter + Codex headroom** (§2.5) — `skills_budget.py` reports `effective_model_index` (subtract explicit-only descriptions); trim the 3 fattest descriptions (interface-thinking/diagnose/debug). No mass description surgery — the overflow was a metering artifact.
P3. **Fix the two confirmed routing misses** (§7) — via doc wiring + typed surfacing, NOT description tuning (main sessions essentially never ambient-invoke; ~90% of Skill calls are subagent-side, so a main-session skill won't fire itself however good its description). Wire interface-thinking as the named tool of the wakeup-cadence meta/observe front + trigger vocab (representation/cockpit/instrument); sync diagnose into `~/.agents/skills`, ~30 days, then demote-or-fold-into-/debug. Demote verify-before to explicit-only (internalized; the 227 ambient chars buy structurally-unrealizable value — keeps typed /verify-before, hutter/CLAUDE.md:96 stays wired). Mount-or-archive goals.
P4. **Small fixes**: critique budget floor (§2.2), research-ops pointers (§2.3), observe stub deletion (§2.4), decide Phase-0 "read-not-grep" checklist line + dissolved-at-Phase-0 ADR template (value-audit findings).
P5. **Arc-state externalization for long-arc skills** (§5) — PreCompact customInstructions injection of active skill arc + step, or a tiny arc-state file convention. Design first; measure which arcs actually break.
P6. **Skill self-annotation**: end-of-arc friction → `append-skill-memento.sh` nudge (mechanism exists, unused) — cheapest way to make skills self-improving between audits.
