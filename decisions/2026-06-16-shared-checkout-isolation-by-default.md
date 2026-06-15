---
id: 2026-06-16-shared-checkout-isolation-by-default
concept: agent-session-isolation
repo: agent-infra
decision_date: 2026-06-16
recorded_date: 2026-06-16
provenance: contemporaneous
status: accepted
initial_leaning: dedup the stop-uncommitted-warn advisory (band-aid)
relations:
  - type: depends_on
    target: 2026-06-16-agentlogs-write-gateway   # steward proposal; same shared-substrate class
---

# 2026-06-16: Shared-checkout concurrency is the norm — isolate by default, retire attribution heuristics

## Context
`stop-uncommitted-warn.sh` re-emits a non-blocking "N unattributable files" advisory every
Stop, each costing a model turn. It carries ~200 lines of attribution heuristics (per-session
ledgers, baselines, fail-closed branches) — every branch citing a past misattribution incident.
The surface ask was "make the hook stop nagging." The real axis: **is concurrent shared-checkout
the NORM (→ enforce isolation structurally) or a today-anomaly (→ manual habit, don't build
infra)?** Decided by measuring, not reasoning (constitution: measure before enforcing; verify
failure claims in logs before architectural fixes).

## Measured behavior (the counterevidence test)
`agentlogs.db` session-overlap (sessions sharing a `project_root` with overlapping
[start,end]), indexed window 2026-05-26→06-16:

| project | sessions | overlapped a peer | rate |
|---|---|---|---|
| intel | 585 | 567 | 97% |
| phenome | 232 | 225 | 97% |
| publishing | 43 | 38 | 88% |
| genomics | 178 | 151 | 85% |
| hutter | 75 | 63 | 84% |
| agent-infra | 308 | 241 | 78% |

- **78–97% of real-project sessions overlap a peer on the same checkout.** Concurrency is the
  standing reality, not a spike.
- Hook's legit auto-commit path: **17 fires since May**. Attribution/sweep-related commits: **~113**.
  The machinery protects a low-frequency path while breaking on the high-frequency condition.

This is the adversarial test the `/decide` arc requires: low overlap (<10%) would have falsified
isolation-by-default and favored the band-aid. It did not — it strongly confirmed.

## Decision
1. **Isolation by default for project checkouts.** Make worktree-per-session the default, enforced
   at LAUNCH (the one place that prevents the shared-state class), not coped with downstream in 5
   hooks. Matches the repo's own prior art (isolate-per-agent + merge-via-git; CAID 7.8pp;
   event-sourcing/locking NOT needed — `research/2026-06-13-multiagent-state-coordination-prior-art.md`).
2. **Enforce by PROMPTING at launch — not a silent wrapper, not a manual habit** — at 78–97%
   concurrency a manual `--worktree` is forgotten ~80% of the time, but a *silent* auto-worktree
   carries real costs (see Revisions 2026-06-16). The launch path detects a live peer via the lock
   and *asks* (`[w] isolate / [s] share`): isolation can't be forgotten, without a surprise context
   switch.
3. **One primitive underneath: a per-checkout claim-lock** `.claude/checkout-claim.json`
   = `{pid, session_id, started_at}` (gitignored runtime state), reclaimed when pid is dead.
   Composable — replaces the imprecise global `pgrep -x claude` in the peer-warn hook (also closes
   the pending pgrep-overcount decision) and is the wrapper's isolate/no-isolate signal.
4. **Once isolation is default, RETIRE the attribution heuristics.** With one writer per tree,
   every changed file is unambiguously this session's → the unattributable/foreign/fail-closed
   branches become dead code. `stop-uncommitted-warn.sh` collapses to "commit my delta." Delete,
   don't wrap (constitution #14).

## Alternatives considered
1. **Dedup the advisory** (hash the set, fire once/session) — band-aid; leaves 80% concurrency
   coping with heuristics forever. *Rejected* (data shows the condition is permanent, not transient).
2. **Extract+test the attribution classifier** (tested lib + `--explain`) — robustifies machinery
   that isolation makes deletable. Investing in cruft the right architecture removes. *Rejected.*
3. **Manual `--worktree` habit + lock for detection only** — fails at 78–97% prevalence (forgotten).
   *Rejected* as the default; the lock is still built (it's the wrapper's substrate).
4. **Process-ancestry / FS-level write attribution** — still attribution (band-aid layer 2), still
   shared-tree. *Rejected.*
5. **Delete the Stop auto-commit entirely** — loses the (low, 17-fire but real) forgotten-work net.
   *Deferred*, not chosen — keep the net, simplify it post-isolation.

## Counterevidence sought
Searched for the case that kills isolation-by-default: session-overlap < ~10% (→ anomaly → band-aid
suffices). Found the opposite (78–97%). Also checked the hook's legit value (17 fires → low, so
simplifying it is cheap) and isolation's hidden cost (CAID already measured isolation *beats* shared
+7.8pp → no net cost). Decision survives consider-the-opposite.

## Invariants the implementation must preserve
- Lock is per *physical checkout dir* (worktrees have separate working trees → separate locks).
- Stale lock (dead pid) is reclaimable, never a deadlock. Fail-open: no lock ⇒ behave as today.
- Wrapper is inspectable (`--dry-run` prints the isolate decision) and debuggable (shell `-x`).
- Cross-model critique deliberately skipped: the agentlogs numbers ARE the adversary; an external
  model can't verify our DB, and context-blind models hallucinate repo internals
  (this session's Git-AI amend-restamp lesson). The data is the anti-sycophancy test.

## Evidence
agentlogs.db overlap query (above); 17 `[wip] Auto-checkpoint` commits since May; ~113
attribution/sweep commits; `sessionstart-peer-session-warn.sh` uses global `pgrep -x claude`
(imprecise). Prior art: CAID isolate-per-agent +7.8pp.

## Revisit if
- Measured overlap drops below ~20% sustained (concurrency stops being the norm) → manual habit suffices.
- Worktree merge friction proves costly in practice → reassess enforcement mechanism (not the principle).

## Implementation gate (NOT done here)
Shared infra (5 projects) + currently 4 live peers running these hooks → propose-and-wait + execute
only from a clean worktree, single-variable commits: (1) claim-lock + gitignore, (2) repoint
peer-warn to the lock, (3) launch PROMPT (warn + one-key opt-in; headless `-p` passes through; NOT a
silent auto-wrapper — see Revisions), (4) retire the Stop-hook attribution branches. Each its own
commit so a regression is bisectable.

## Revisions

### 2026-06-16 — Phase 3 softened to a prompt (driven by a "any downside?" probe)
Original Decision said "enforce via a launch wrapper." A downside review surfaced costs the overlap
data hadn't priced — enough to change the *mechanism*, not the principle (enforcement still beats a
forgettable habit):
- **Wrapping the binary:** sits on every launch's critical path (must fail-open → `exec` the real
  binary on any error); recursion risk (invoke the real binary by absolute path); **headless `-p`
  must pass through** — auto-worktreeing /loop/cron/llmx dispatches would silently break them.
- **Auto-worktree behavior:** implicit context switch (land in a worktree you didn't ask for → commit
  to a branch you forget to merge → "lost" work); **path-keyed infra goes blind until merge** —
  launchd WatchPaths, agentlogs `project_root`, `.mcp.json --directory` all key on the canonical path,
  so a worktree is invisible to them until merged back; plus worktree proliferation + merge burden.
- **Resolution:** keep precise lock-based DETECTION (Phase 2 — pure win, unchanged). Replace the
  silent auto-wrapper with a **launch prompt** (`[w] isolate / [s] share`): preserves "can't forget"
  without the surprise/headless/path-blindness footguns. Full-auto only earns its keep once path-keyed
  infra is worktree-aware (out of scope). Principle unchanged; enforcement surface moved silent→prompted.
