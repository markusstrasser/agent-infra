---
concept: agent-commit-architecture
decision_date: 2026-06-14
status: proposed
supersedes_in_spirit: research/2026-06-14-git-janitor-subagent-verdict.md (subagent was the wrong layer)
relates: decisions/2026-05-27-corpus-as-event-log-repos-as-hybrid.md, decisions/2026-06-07-state-externalization-lens.md, decisions/2026-05-26-cross-attestation-substrate-v2.md
---

# Commit is a gateway-mediated mutation, not hand-operated git

> **Status: proposed — REVISED post cross-model critique round 1 (2026-06-14).** Core spine
> survived (both models endorsed explicit-pathspec + message-transform); three overclaims
> corrected. See "## Critique round 1 — folded" at the bottom for the hardened spine + 2 open
> forks. The Decision section below is the ORIGINAL (kept for the audit trail); read it through
> the corrections.

## Context (the pain, measured)
Multi-agent (Claude 95% / Codex 5% / Gemini 0), multi-repo system; agents commit constantly
(4,279 commit calls / 386 sessions / 21d). Failure classes: shared `.git/index` races between
concurrent agents (biggest-volume, GF-1; a `[readiness]` change swept into a foreign `[quality]`
commit 2026-06-08), pre-commit-hook rejection retry-loops (single session: 22 failed commits),
`git commit --no-verify` bypassing guards (14 sessions). Anthropic ships no commit-hygiene
primitive (bet on worktrees; gaps open at #4834/#40117/#46808/#56865). genomics has a proven but
substrate-coupled bash mitigation (`session_commit.sh`: mkdir spinlock + explicit pathspec).

## The real axis
Not "which wrapper." **Commit is the one mutation that escaped this system's own
mutation-gateway + transactional-outbox discipline** — every other mutation goes through a gateway
(`corpus_core.outbox.enqueue`, the genomics `MutationGateway`), but commit is still hand-operated
raw git through bash. The decision: bring commit under the same discipline, at the deepest
principled representation (breaking migration, no backward-compat, dev-effort-free).

## Decision (the principle) — three cleanly separated layers

1. **Representation — `ChangeIntent`.** The agent emits a typed record: `paths`, semantic
   `type`+`scope`, `why`, `session`, optional `task`/`decision`/`attest` links. The agent's only
   job is the *semantic decision* (what + why). Everything mechanical is externalized
   (state-externalization lens). `ChangeIntent` is the commitment-loop's *resolution event*
   (ideas.md: observation→…→commitment→**resolution**→score) — the seam that lets a commit also
   project to corpus attestation / provenance / decision-journal.

2. **Gateway — the single writer.** Validates the intent (hard-blocks — protected-paths,
   large-binary, append-only — stay HARD blocks; message format becomes a **transform**, not a
   reject-then-retry), serializes the stage→commit critical section, and **projects** the intent to
   the substrate + side-effects. **Enforcement lives HERE, not in git hooks.** Consequence:
   `--no-verify` bypass is **structurally impossible** — the gateway is the only commit path (raw
   `git add`/`git commit` removed from the agent's path and blocked by a single redirect guard).
   The index race is closed by single-writer serialization, not by a spinlock bolted onto bash.

3. **Substrate — abstracted, swappable.** **git first** (proven, Codex-compatible; the
   single-writer gateway closes the index race). **jj (Jujutsu) is a designed-in swappable
   substrate** (no staging index → race class gone; operation log → inspectable + `jj undo`;
   conflicts-as-data → "feisty" shrinks). jj's lack of native git-hook firing (verified 2026-06-14,
   jj docs "Hooks: No", v0.40) **stops mattering** because enforcement no longer lives in git
   hooks — which is precisely what makes jj viable later without the third-party hook shims.

## Invariants the design must preserve
- HARD blocks (protected-paths / large-binary / append-only) are never auto-fixed or bypassable.
- The gateway is a **CLI/contract callable by any process** (Claude + Codex + cron), not an
  SDK-locked tool — cross-vendor by construction.
- **Feisty git stays with the reasoning agent**: merge conflict / rebase / revert / non-ff escalate;
  the gateway does routine commits only.
- Breaking migration: raw `git add`/`git commit` is **removed** from the agent path, not wrapped.
  No compat shim, no dual path (constitution P14).
- Inspectable: the intent ledger (and, on jj, the op-log) is a queryable record. Debuggable: replay
  intents / `jj undo`. Robust: one validated path.

## Rejected (do not re-propose)
- **A. commit-hygiene subagent** (built+tested today) — wraps the low-level interface, re-encounters
  every root cause; not composable (CC-only) / inspectable (transcripts). **Retire**, or demote to a
  thin gateway caller if context-shielding is still wanted.
- **genomics `session_commit.sh` as the extraction target** — proven but substrate-coupled bash
  duct-tape (mkdir spinlock, bash-3.2 array hacks). **Harvest its lessons** (explicit-pathspec is the
  real cross-sweep fix; the lock rationale) into the gateway; do not bless the script as shared infra.
- **E. async daemon / transactional outbox NOW** — single-writer gateway achieves race-freedom
  synchronously; async adds complexity with no current payoff. Outbox stays the *pre-registered
  escalation* if real cross-process contention is later measured, not a thing we build speculatively.
- **jj as the migration target NOW** — 0.x + breaks git-hook enforcement; neutralized to "optional
  substrate" by the gateway. Adopt after the gateway is solid.
- **worktree-per-agent as THE fix** — concurrency-only; #46808 (hooks silently don't fire in
  worktrees) is a guard-death landmine.

## Open tension for cross-model critique (Phase 4)
Is the `ChangeIntent` → multi-projection (corpus / decision / provenance) layer **real value or
speculative coupling**? The "speculative shared-utility extraction" veto (proven-common across ≥2
repos first) bites here. **Disciplined fallback if critique says coupling:** ship the gateway +
`ChangeIntent` input + git projection as the spine; make corpus/decision/provenance projectors
**extension points** adopted only when proven-common — not coupled in v1.

## Pre-registered success criterion (per /decide)
Zero spine reversals across escalating cross-model rounds. If a round overturns "enforcement moves
to the gateway" or "substrate is abstracted," the spine was wrong. If rounds only resolve HOWs
(intent schema fields, lock vs queue, projector boundaries), the decision is sound and those HOWs
become the first build tasks.

---

## Critique round 1 — folded (cross-model, Gemini-arch + GPT-formal, 2026-06-14)

Audit trail: `.model-review/2026-06-14-commit-gateway-architecture-ac37c7/`. Both models verified
against git semantics + the quantitative grounding (203.8 commits/day → 2.4% lock utilization).

### Corrected (overturned overclaims — the spine had 3 weak joints)
- **"`--no-verify` structurally impossible" → FALSE (CONVERGENT, both models).** A redirect-guard
  is itself a git hook; `--no-verify`/`commit-tree`/absolute-path/`core.hooksPath` bypass it, and the
  agent must hold real `git` for reads. Enforcement cannot be *impossible*, only *auditable*.
  → **Replace with a receipt-audit invariant:** every commit carries a gateway-receipt trailer or is
  a flagged authorized exception; daily `HEAD@{24h}` audit, alert on any unreceipted commit.
- **"Enforcement leaves git hooks" → FALSE (GPT).** Hooks cover ALL commit paths by default; a
  gateway covers only its callers → removing hooks *strictly decreases* coverage.
  → **Keep git hooks as defense-in-depth**, running the SAME shared policy engine (one impl, two
  callers: gateway + hooks). No policy drift.
- **Synchronous multi-projection → SPOF (CONVERGENT).** Projecting to corpus/DB inside the commit
  loop fails the commit when the DB is locked / MCP times out.
  → **Projections are async, rebuildable, extension points — never in the commit critical path.**
  v1 = commit + receipt only. Minimal `ChangeIntent` {paths, type, scope, why, session, policy_version}.
- **Substrate abstraction → YAGNI (CONVERGENT).** No incident needs jj that the git gateway doesn't
  solve; VCS abstraction is leaky; 2.4% utilization means jj's concurrency edge isn't the bottleneck.
  → **git-only v1; jj = pre-registered SHADOW experiment** (mirror N intents, compare
  pathsets/conflicts/undo/policy over 500 commits; promote only on evidence). No abstraction layer.

### Surfaced (new axis I missed — Gemini, verified)
- **Workspace isolation is a SEPARATE axis the gateway does not address.** Explicit-pathspec stops
  foreign files being *committed*, not being *written* to the shared working tree — two agents editing
  one file collide at the filesystem before any commit. Only **worktree-per-session** isolates the
  *mutation phase*. (Consistent with `research/2026-06-13-multiagent-state-coordination-prior-art.md`
  + the SessionStart peer-warning.) Complementary to the gateway, not competing.

### Survived (HOLD — both models endorsed)
- Lock-serialized **explicit-pathspec commit** ("battle-tested", "neutralizes the 2026-06-08 race").
  **Message-format transform-not-reject** ("structurally superior"). Minimal ChangeIntent.

### Hardened spine — THREE complementary axes
1. **Workspace isolation (mutation phase):** worktree-per-concurrent-session.
2. **Commit mediation (commit phase):** lean **git-only commit-gateway CLI** (cross-repo, any vendor):
   lease-based lock (harden session_commit.sh's PID+age reaping), explicit-pathspec commit, SHARED
   policy engine (transform format; hard-block protected-paths/large-binary), gateway-receipt trailer.
3. **Enforcement perimeter (auditable, not impossible):** keep git hooks as defense-in-depth (shared
   policy) + best-effort steering to the gateway + **receipt-audit** as the load-bearing guarantee.
- **Projections** async/extension-point; **substrate** git-only + jj-shadow.
- **Retire** the commit-hygiene subagent (redundant) AND genomics `session_commit.sh` (harvest its
  mechanics into the gateway — justified over the script by: shared policy engine [guards ARE already
  cross-repo in skills/hooks = proven-common], the receipt-audit invariant, a maintainable typed CLI
  vs bash-3.2 duct-tape, and the message-transform — NOT by projections/substrate).

### Open forks (user's call — models split here)
1. **Worktree-per-session (Axis 1): enforce now, or keep as convention?** Only fix for workspace
   write-collisions; adds session-setup friction. (#46808 hook-death is mitigated — enforcement is
   the gateway + receipt-audit, not worktree-bound git hooks.)
2. **Perimeter strength (Axis 3): receipt-audit + defense-in-depth hooks (detection-first, simpler, $0)
   vs PATH-wrapped `git` (prevention-first, catches `--no-verify`, more invasive).** Gemini leaned
   PATH-wrap; GPT leaned receipt-audit. Recommend: receipt-audit + hooks first; PATH-wrap as optional
   later hardening.
