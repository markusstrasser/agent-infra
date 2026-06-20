# oh-my-openagent — extracted primitives, tricks & methods

**Date:** 2026-06-20
**Source:** `github.com/code-yeongyu/oh-my-openagent` @ HEAD (dev), 174K LOC TS, 5269 files. Deep-dive via 7 parallel extraction agents (sonnet workers, Opus synthesis). Raw per-area findings were in `/tmp/omo-deepdive-findings/01..07` (ephemeral); the actionable content is folded in below.
**What OmO is:** a mature multi-model orchestration harness for OpenCode/Codex (11 named agents, category model-routing, 54+ lifecycle hooks, team-mode, custom edit primitive). It solves "give the masses a Claude-Code-equivalent over cheap multi-provider models." We're at-or-ahead on RSI/observe/cross-model-review; the value here is **specific primitives**, not the architecture.

> Provenance caveat: claims below are extracted from OmO source with file:line and are mostly directly verifiable. Two are inferential about *Claude Code's own* internals (marked ⚠ VERIFY) — OmO reimplements a CC-compat layer, so its behavior may not mirror real CC.

---

## TL;DR — the build table

Gate is Value | Maintenance | Prereq (constitution P8), not effort.

| # | Primitive | Value | Maint | Verdict |
|---|---|---|---|---|
| 1 | **edit-error-recovery hook** — Edit fails → inject corrective reminder | High (our Edit is brittle exact-match) | ~0 (bash PostToolUse) | **BUILD** |
| 2 | **Post-compaction degradation monitor** + preemptive compact | High (= our 9×-compact failure class) | low | **BUILD/probe** |
| 3 | **Subagent dispatch-receipt verification** | High (= our 2× ~9M-tok rediscovery burns) | low (agentlogs query) | **BUILD** |
| 4 | **Rules char-budget silent-drop** ⚠ VERIFY | High if real (explains `context_budget OVER`) | 0 (verify only) | **VERIFY FIRST** |
| 5 | **hyperplan** 5-hostile→distill→dedicated planner | Med-High (upgrades /decide) | low (skill text) | **FOLD into /decide** |
| 6 | **Opus-4.8 "counter these 4 defaults" calibration block** | Med (our exact model) | 0 | **ADOPT (CLAUDE.md/skill)** |
| 7 | **Turn-local intent reset** prompt rule | Med | 0 | **ADOPT (rule line)** |
| 8 | **Durable append-only notepad** for /loop | Med | low | **ADOPT (/loop convention)** |
| 9 | **empty-task-response-detector** | Med (subagent stall) | ~0 | **BUILD (cheap)** |
| 10 | **review-work sharpenings** (per-change isolation, no-sev-without-PoC, permalink-or-no-claim) | Med | 0 | **FOLD into /code-review** |
| 11 | **hashline** LINE#ID edit addressing | Med (can't swap native Edit) | high | **STUDY, don't build** |
| 12 | LSP-as-MCP `find_references(decl=false)` for dead-code | Low (we're Python-heavy) | high (daemon) | **SKIP (note for TS)** |
| — | category 5-stage resolution, file-mailbox stack, boulder-state machine, model-fallback, git-bash-mcp, read-image-resizer | — | — | **SKIP** (we have better or N/A) |

---

## Tier 1 — build these (novel, real pain, cheap)

### 1. edit-error-recovery — corrective reminder on Edit failure
**Mechanism** (`hooks/edit-error-recovery/hook.ts`): PostToolUse on `edit`; exact-string match on 3 known failure outputs — `"oldString not found"`, `"oldString and newString must be different"`, `"oldString found multiple times"` — appends a structured reminder to the tool result. Idempotency via a marker substring so it never stacks.

Their reminder text (portable verbatim):
> `[EDIT ERROR - IMMEDIATE ACTION REQUIRED] You made an Edit mistake. STOP and do this NOW: 1. READ the file immediately to see its ACTUAL current state ...`

**Why for us:** Claude Code's Edit is exact-string-match — the same three failures are our most common tool error. A bash PostToolUse hook that pattern-matches the Edit error and injects "re-Read first, the file state differs from your assumption" is ~20 lines, zero maintenance, fail-open. Companion: **json-error-recovery** (8 JSON-error regexes + an exclude-list for bash/webfetch/todowrite so legit "invalid json" in *output* doesn't false-trigger).

### 2. Post-compaction degradation monitor (+ preemptive compaction)
This is the one I flagged last turn — now with mechanism.
- **no-text-tail primitive** (`preemptive-compaction-no-text-tail.ts:18-29`): an assistant message is "empty/degraded" iff ALL its parts are `step-start`/`step-finish` with no text content (model emitting tool-steps but no reasoning/prose).
- **Degradation monitor** (`preemptive-compaction-degradation-monitor.ts`): on `session.compacted`, watch the next 5 assistant messages; if ≥3 are no-text-tail → fire a recovery re-compaction + toast warning.
- **Preemptive trigger** (`preemptive-compaction-trigger.ts`): cache token counts on `message.updated`; every `tool.execute.after` compute `(input + cache_read)/model_limit`; at ≥78% fire `/compact` proactively, 60s cooldown.
- **Todo preserve/restore** (`compaction-todo-preserver`): snapshot `session.todo()` pre-compaction; if post-compaction todos are empty or only bootstrap stubs, restore the snapshot (intercepts the TodoWrite call and swaps `args.todos`).

**Why for us:** our `postcompact-verify` only checks *hallucinated completed work*. It does NOT catch the silent **quality** collapse where a compacted session keeps tool-calling but stops reasoning — which is exactly the `genomics-1c094e24` 9×-compact correction case (own-code-drift blindness after repeated compaction). The "no-text-tail ratio over next N messages" is a cheap, hookable degradation signal we don't have. Claude Code exposes a `PreCompact` hook event (⚠ verify our settings use it) — usable for the todo/state snapshot.

### 3. Subagent dispatch-receipt verification
**Their mechanism** (`team-core .../pending-delivery-recovery.ts:44-69`): a delivered message embeds a `messageId`; on `session.idle` they scan the recipient's actual session history for that id. Present → ack (move to `processed/`); absent → requeue. I.e. **don't trust "dispatch accepted" — verify the payload actually landed in the recipient's context.**

**Port for us:** embed a unique `dispatch_id` UUID in every subagent briefing; after the subagent returns, query `agentlogs.db` for that token in the subagent's turns. Absent → the subagent ran with lost/compacted/wrong context and its output is suspect. **This would have caught both ~9M-token "subagent rediscovered completed work" burns** in CLAUDE.md. Fits our SQLite forensics exactly; pairs with the existing inventory-before-dispatch gate.

---

## Tier 1.5 — verify before anything

### 4. ⚠ Rules character-budget silent-drop
Extraction claim: OmO's rules-engine applies `maxRuleChars` / `postCompactMaxRuleChars` budgets and **silently drops rules when exceeded** — larger post-compaction drop. IF Claude Code does the same, it would explain our live control-plane `context_budget OVER` flags (agent-infra 32848 tok, phenome 32526 tok, ceiling 30000) — meaning over-budget CLAUDE.md/rules may be **silently truncated in compacted sessions**, i.e. our governance text is quietly not loading when we most need it.
**Action:** this is about OmO's CC-*compat* layer, not proven CC behavior. Verify against actual Claude Code (docs / `--debug` / a controlled over-budget probe) before trusting. If real, the `context_budget OVER` drift flag graduates from cosmetic to load-bearing and the rule-slimming work becomes urgent. Cheap to check; do it before acting.

---

## Tier 2 — adopt as method/prompt (no code)

### 5. hyperplan — adversarial planning that actually kills weak assumptions
`.agents/skills/hyperplan/SKILL.md`: Lead spawns **5 hostile members** (mapped to model categories: skeptic/simplicity, validator/blast-radius, researcher/evidence, architect, creative/lateral). **3 rounds**: independent analysis → cross-attack → defend/refine/**concede**. Conceded findings are *dropped*. Lead distills ONLY survivors. **Hard invariant: the Lead never writes the plan** — the survivor bundle is mandatorily handed to a dedicated `plan` subagent that owns sequencing + success criteria.
**vs our /decide:** /decide is largely single-pass cross-model review. The 3-round attack/concede filter + writer/planner separation is a real upgrade. Fold the "concede-drops-the-finding" and "distiller ≠ planner" mechanics into `/decide` (or `/brainstorm`'s multi-model volume mode).

### 6. Opus-4.8 calibration block — counter the model's known defaults
`src/agents/sisyphus/claude-opus-4-8.ts` ships a block targeting **our exact model**:
> Four 4.8 defaults you MUST counter: 1. LITERAL FOLLOWING (apply "every/all" to EVERY case, never infer "first only"). 2. OVER-EXPLORATION (sufficient > complete; once you can act, ACT). 3. OVER-ASKING (naming/defaults/formatting → pick a reasonable option, never close with "Want me to also…?"). 4. CAPABILITY UNDER-REACH (trigger matches → fire immediately, no debate).

These map almost 1:1 to our own feedback memories (`feedback-see-it-through-when-confident`, `feedback_question_scope`, "fix no-brainers same turn"). An external team independently deriving the same Opus-4.8 failure modes is strong cross-validation. Worth a compact calibration block in our harness (we have the rules in prose; the tabular "counter THIS default" framing is sharper and possibly more hook-checkable).

### 7. Turn-local intent reset
Sisyphus Phase 0: *"Reclassify intent from CURRENT message ONLY. NEVER auto-carry implementation mode from prior turns. Implementation authorization does NOT persist — it must be RE-ESTABLISHED by an explicit verb in the current message."* Sharper than our existing "answer vs implement" discipline; prevents drift where a question after an implementation turn silently keeps editing. One-line rule addition.

### 8. Durable append-only notepad for /loop
ultrawork inits `NOTE=$(mktemp …)` and APPENDS (never rewrites) sections: `Plan / Scenarios / Now / Todo / Findings (with file:line) / Learnings`. "If context is lost, re-read the notepad and resume." Cleaner externalized-state for long autonomous runs than our single `checkpoint.md` — append-only fits our institutional-knowledge principle. Adopt as a `/loop` convention (complements, doesn't replace, checkpoint.md).

### 9. empty-task-response-detector
PostToolUse on Task: empty subagent output → inject *"Note: the call has already completed — you are NOT waiting for a response. Proceed accordingly."* Prevents the parent stalling/polling after a silent subagent failure. ~10 lines, cheap, real failure mode in fan-outs.

### 10. review-work sharpenings → fold into /code-review & /critique
- **Per-change context isolation:** each reviewer gets ONLY its change group's diff (not the whole changeset) — cleaner signal per unit.
- **Security: no severity without a working attack path** — hunters propose, independent PoC engineers reproduce-or-falsify; "downgrade anything without a working path."
- **Permalink-or-no-claim** (github-triage): every claim needs a SHA-pinned URL; unbackable → `[UNVERIFIED]`. Matches our quoted-evidence discipline; the hard "no permalink = no claim" framing is enforceable.
- **5-axis all-must-pass:** goal / autonomous-QA (brainstorm 15-30 scenarios then run on the real surface) / code-quality / security-only / context-mining (git history + issues + xrefs). ANY inconclusive = not approved.

---

## Tier 3 — study, mostly skip

### 11. hashline (their headline edit primitive) — STUDY, don't build
Addresses a line as `{lineNumber}#{2-char-hash}` (xxHash32 over `trimEnd(stripCR(line))`; **seed=0 for significant lines** so the same content hashes identically regardless of position — model locates by content; seed=lineNumber for blanks/punctuation to disambiguate). Read-format the model sees: `N#XX|raw content`. Edit op: `{op, pos:"11#XJ", end?:"12#MB", lines:[…]}`. Killer features exact-string-match structurally **cannot** do: duplicate-line disambiguation, trailing-whitespace immunity, and **stale-reference detection with guided recovery** (on mismatch, the error embeds the corrected `N#XX` tags so a single retry fixes it without a full re-read). Edits applied **bottom-up** (descending line no.) so earlier edits don't shift later addresses. Plus 5 autocorrect passes for model output quirks.
**Verdict:** genuine improvement over our brittle Edit — but we can't swap Claude Code's native Edit tool, so building the full stack is out of scope. **Borrowable idea even without it:** the stale-reference-with-guided-recovery concept is what #1 (edit-error-recovery) approximates cheaply. Keep hashline as the reference design if we ever own our edit path.

### 12. LSP-as-MCP — SKIP for now (note for big TS refactors)
8 tools incl. `find_references(includeDeclaration=false)` — the primitive that makes dead-code removal *reliable* (grep misses re-exports / structural typing / dynamic imports). Real win for large TypeScript refactors; cost is a language-server daemon lifecycle. We're Python/Modal-heavy; not worth standing up permanently. Note it if we hit a large TS dead-code sweep.

### Explicit skips (we have equal/better, or N/A)
category 5-stage model resolution (our llmx + measured model-guide already pick model/effort from **real per-task eval numbers**; theirs is hardcoded intuition with zero measurement) · full file-mailbox stack (our Workflow/SQLite dominate; only the *receipt* idea #3 ports) · boulder-state JSON machine (checkpoint.md + plans/ cover it) · model-fallback/runtime-fallback (llmx transport covers; the permanent-vs-transient error classifier is a minor `--fallback-model` idea for long loops) · git-bash-mcp (Windows-only) · read-image-resizer · tool-output-truncator (native).

---

## Cross-cutting insight
Four of the highest-value items (#2 degradation monitor, #3 dispatch-receipt, #4 rules-budget-drop, and the todo preserve/restore) all attack **context/compaction integrity** — precisely our documented weak spot (`genomics-1c094e24` 9×-compact case + the live `context_budget OVER` flag). OmO independently treats compaction as a first-class failure surface with active detection, where our harness treats it as automatic+verify-after. That's the theme worth a focused pass.

## Philosophy NOT to adopt
OmO's manifesto: *"Human intervention is a failure signal / HUMAN IN THE LOOP = BOTTLENECK."* Autonomy-maximalism with no verifier-quality conditioning — the blunt version of our verifier-conditioned autonomy, and the stance behind the Replit "deleted prod DB in 9s then faked success" failure already in our `invariants.md`. Borrow the mechanisms, not the slogan.

## Suggested next actions (if pursued)
1. Verify #4 (rules char-budget drop) against real Claude Code — cheapest, gates how urgent the budget work is.
2. Ship #1 (edit-error-recovery) + #9 (empty-task-response-detector) — trivial bash hooks, agent-infra-only, autonomous per constitution.
3. Probe #2/#3 as the "compaction-integrity" pass.
4. Fold #5–#7, #10 into existing skills/rules (text-only).
