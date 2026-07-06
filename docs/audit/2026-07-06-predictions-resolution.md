# Predictions Resolution — 2026-07-06

Resolved 6 DUE predictions in `predictions.jsonl`. Append-only: each verdict is a new
`kind:"resolution"` row (via `scripts/predictions.py resolve`), never an edit of the prediction.

HEAD at resolution: `4020598`. Ledger had **0 resolution rows** before this run (the loop had
never closed autonomously — see prediction #5).

| # | id | verdict |
|---|----|---------|
| 1 | 2026-06-15-scite-scope | **CONFIRMED** |
| 2 | 2026-06-28-prior-context-cluster | ~~REFUTED~~ → **CONFOUNDED** (instrument was dead; see addendum) |
| 3 | 2026-06-28-peer-warn | **REFUTED** (noisy verifier) |
| 4 | 2026-06-28-autockpt-failclosed | **CONFIRMED** |
| 5 | 2026-06-28-prereg-adoption | **PARTIAL** |
| 6 | 2026-06-30-clash-shadow-precision | **PARTIAL** (UNRESOLVABLE-YET — no data) |

---

## 1. `2026-06-15-scite-scope` — CONFIRMED

**Prediction:** scite MCP relocated user→project (bio repos only) → non-bio sessions
(agent-infra/intel/hutter) load ~11.5k fewer MCP tokens; scite absent in non-bio, present in genomics/phenome.

**Measured:**
- `~/.claude.json` GLOBAL `mcpServers` = `context7, research, exa` — **no scite globally**. (The
  2 grep hits are inside the `~/Projects/research` project block, a bio/research repo.)
- Project `.mcp.json`: genomics=scite present (2), phenome=scite present (2), intel=**0**,
  agent-infra/hutter=no `.mcp.json` (→ no scite).
- **This live agent-infra session's deferred MCP tool list = context7 / research / exa; NO
  `mcp__scite__*`** — direct confirmation scite is not loaded in a non-bio session.

The ~11.5k token delta itself isn't independently re-measured (no baseline `/context` capture),
but the relocation mechanism is fully confirmed and the target outcome (scite absent in non-bio,
present in bio) holds on every repo checked.

Commands: `grep -c scite ~/.claude.json`; per-repo `.mcp.json` grep; `json.load(~/.claude.json)`
global vs project `mcpServers`.

## 2. `2026-06-28-prior-context-cluster` — REFUTED

**Prediction:** prior-context front-load hook (skills@a174cf0) → the prior-context/rediscovery
cluster stops dominating the blindspot-digest top flags. Metric: prior-context no longer #1
theme AND `label=prior-context` fired.

**Measured:**
- rediscovery/GROW_COVERAGE is **still the #1 direction category in every recent digest**:
  06-28=45, 07-04=58, 07-05=44, 07-06=47 (baseline ~45). It never shrank / stopped dominating.
- The `prior-context` hook fired only **~5 times, all ≤2026-06-16** (projects `hooks`, `evals`),
  then went **dormant** — 0 fires since. (`grep prior-context ~/.claude/hook-triggers.jsonl`.)

Conjunct A (no longer #1) is FALSE. Conjunct B (fired) is technically true but the hook is
effectively dead, so it never got a fair test. The predicted OUTCOME (cluster stops dominating)
is clearly falsified. Note: the *individual* top-flags-by-confidence are now over_caution-
dominated, but that shift is not attributable to a dormant hook.

**Actionable:** investigate why the front-load hook stopped firing after 06-16 (deploy regressed
or trigger too narrow). Command: `grep 'prior-context' ~/.claude/hook-triggers.jsonl`.

### ADDENDUM 2026-07-06 — verdict downgraded to CONFOUNDED (measurement invalid)

The REFUTED row stays in the ledger (append-only), but it is **superseded**: the measurement was
invalid because the instrument was **dead, not ineffective**. Per `docs/audit/2026-07-06-dead-llm-hooks.md`
+ fix `skills@17c97b5`:

- `userprompt-prior-context.py` is **pure Python, no LLM** — it read `env.get("user_message")`,
  but CC 2.1.x renamed the UserPromptSubmit envelope field `.user_message`→`.prompt` (~2026-06-16).
  The hook read empty and silently no-op'd for ~3 weeks — which is **exactly** the boundary my
  fire-count data showed (~5 fires, all ≤06-16, then dormant). The dormancy was the field rename.
- Because the hook was never actually exercised on real prompts, "the cluster stayed #1" cannot
  refute the hook's efficacy — it measured a dead instrument (global rule #19: separate transport
  failure from capability value).
- The hook is now fixed (reads `.prompt` with `.user_message` fallback, `[DEGRADED]` stderr on a
  missing-both envelope, test 26/26). Live-replay: **49% of real prompts match the gate** — so it
  will actually fire going forward.

Efficacy is now **re-opened** as a fresh forward-looking prediction registered this run
(`2026-07-20-prior-context-cluster-refire`, commit `skills@17c97b5`, due 2026-07-20): does the
rediscovery/prior-context cluster shrink in the blindspot digest over ~2 weeks now that the hook
actually fires?

## 3. `2026-06-28-peer-warn` — REFUTED

**Prediction:** loud one-paste peer warning (skills@4348399) → operator isolates more →
peer-warning fire-rate declines vs ~6 peers/session baseline (2026-06-14). Explicitly a NOISY
human-judged operator-behavior verifier.

**Measured (weekly `peer-session-warn` fires, `~/.claude/hook-triggers.jsonl`):**
W24=52 (baseline week) · W25=192 · W26=89 · W27=186 · W28=20 (partial). Fire-rate **rose**, did
not decline. peers-per-session still routinely hits 6 (today's live session: `detail=peers=6`).
539 fires across 334 distinct sessions.

Operator did not isolate more — concurrent-session behavior is unchanged-to-heavier (consistent
with the digest showing Markus running many parallel sessions). Noisy verifier, but the direction
is unambiguously against the prediction. REFUTED.

## 4. `2026-06-28-autockpt-failclosed` — CONFIRMED

**Prediction:** auto-checkpoint fails closed on empty-ledger+peers (skills@f12a1cd, deployed
2026-06-14 16:40) → zero cross-session `[wip]` commits of unowned files (the 2026-06-14
contamination stops).

**Measured:**
- All post-deploy `[wip] Auto-checkpoint` commits are single-author (Markus Strasser) and
  **topically coherent single-session file sets** — e.g. `addc326` (review+git_import.py+its
  test), `16a6584` (decision+template+lifecycle json), `622840c` (CLAUDE.md+one memo),
  `d29d462` (three research scripts in one dir). No cross-session sweep of unrelated files.
- `[wip] Auto-checkpoint` commits **ceased entirely after 2026-06-20** — none in the rest of the
  2-week window (to 06-28) nor since (to 07-06). Consistent with fail-closed suppressing sweeps
  when peers are present.
- The 2026-06-14 cross-session contamination did not recur.

CONFIRMED. Caveat: exact per-session ledger cross-check isn't fully reconstructable, so this is
"no contamination detected across all 25+ post-deploy wip commits" — which is precisely the
predicted outcome. Commands: `git log --all --since=2026-06-14 --grep='Auto-checkpoint'`;
`git show --stat` per multi-file commit.

## 5. `2026-06-28-prereg-adoption` — PARTIAL

**Prediction:** the ledger survives contact — by 2026-06-28 it has NEW predictions beyond the 4
seeds AND its DUE predictions got resolved (none left open past check_date). Metric: BOTH must hold.

**Measured:**
- Registration adoption: **CONFIRMED** — 39 total predictions, **34 with ts>2026-06-14** (mostly
  `register_implementations` auto-registrations). The ledger is actively written.
- Resolution adoption: **FAILED** — **0 resolution rows** in the ledger before this run. The 6
  DUE predictions sat OPEN **8–21 days past check_date** until this manual resolution.
  `auto-resolve` only refutes the unreachable-SHA subset (all 6 are reachable/non-SHA → 0 caught);
  `questions_view` surfacing did not produce an autonomous verdict.

BOTH did not hold → PARTIAL. Registration side is healthy; the **resolution loop does not close
without a manual operator-initiated run** (this one). Per the metric's own remedy: the fix belongs
on the resolution side (a stronger actuator/prompt), not registration.

Commands: `predictions.py list`; count `kind:"prediction"` rows with `ts>2026-06-14`;
`grep -c '"kind":"resolution"' predictions.jsonl` → 0.

## 6. `2026-06-30-clash-shadow-precision` — PARTIAL (UNRESOLVABLE-YET)

**Prediction:** clash-detector holds ≥80% precision on real captured directives → promote feeder
into Questions VIEW; else CUT. Rule: need ≥5 CLASH verdicts to decide, else resolve 'partial' and
extend the window.

**Measured:** the data to judge precision **does not exist**. All three clash logs are MISSING:
`~/.claude/clash-capture.jsonl`, `~/.claude/clash-shadow.jsonl`, `~/.claude/clash-capture.cursor`.
`just clash-detect --summary` → "no shadow data yet". **0 captured directives, 0 shadow verdicts,
0 CLASH** (need ≥5). The `clash-detect` launchd job exists (`llm=required`, idle/ok) but has
captured nothing since deploy (d355ee8, 2026-06-16).

Per the prediction's own <5-CLASH rule and the task's UNRESOLVABLE-YET guidance → resolved
**partial**; registered a follow-up prediction extending the window.

**Actionable:** the capture pipeline produces no data — either no directive messages trigger
capture, or the capture hook isn't wired to `clash-capture.jsonl`. This must be fixed before an
extended window is meaningful. Commands: `just clash-detect --summary`; `ls ~/.claude/clash-*`.

---

## Cross-cutting finding

The predict-then-falsify loop's **generation half works, consumption half doesn't**: 34 auto-
registered predictions but 0 autonomous resolutions in ~3 weeks. Prediction #5 predicted exactly
this failure mode and it landed. The clash feeder (#6) shows the same shape one layer down — a
live job generating no consumable data. Both point at the same gap: actuators that *close* loops,
not ones that open them.
