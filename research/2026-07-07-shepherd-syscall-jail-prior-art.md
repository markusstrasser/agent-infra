---
title: "Shepherd — syscall-jail permissions as prior-art for hard enforcement"
date: 2026-07-07
axis: "What the Shepherd framework (Yu et al., arXiv:2605.10913) does that is DEEPER than our hook-based enforcement — source-verified, not README-trusted"
source_repo: "shepherd-agents/shepherd @ v0.2.1 (alpha)"
paper: "arXiv:2605.10913 (Yu, Chong, Nandi, Soylu, Sun, Manning, Shi — Stanford/Northeastern)"
status: COMPLETE
verdict: "NO-ADOPT the framework; CAPTURE 3 mechanisms as prior-art with a resurrection trigger"
---

# Shepherd — syscall-jail permissions as prior-art

Prompted by operator paste of the repo README (2026-07-07). Question asked: *what does
Shepherd do better than us?* Answered by cloning the repo and reading the enforcement,
trace, and meta-agent subsystems at file:line (three Explore agents). This memo keeps the
transferable mechanisms; the framework itself is NO-ADOPT (paradigm mismatch + no incident
that justifies the migration cost).

## What Shepherd is

A runtime substrate where a task is a **bodyless typed Python function** — the signature +
docstring ARE the agent contract, and the permission is a type annotation. `@task` detects
the empty body via AST and synthesizes the agent run [SOURCE: shepherd/packages/runtime/
.../nucleus/callable_task.py:204,352 | VERIFIED]. Runs are recorded as a reversible,
git-persisted trace; outputs are held as reviewable proposals until `select/release/discard`.
Self-labeled alpha; APIs changing per release.

## The three transferable mechanisms (source-verified — these are the "better")

### P1 — Hard permission enforcement at the OS syscall, compiled from the type signature
`May[GitRepo, ReadOnly|ReadWrite]` (`May = Annotated`; grants are frozen values
`ReadOnly=GitRepoGrant(mutates=False)`) [SOURCE: .../workspace_control/authority.py:12,973 |
VERIFIED] is parsed (AST + runtime) into a `ConfinementSpec` whose `writable_roots` are
realpath-canonicalized ReadWrite roots [SOURCE: dialect/.../confinement.py:183,194 | VERIFIED].
Lowered per-OS:
- **macOS**: generates an SBPL Seatbelt profile (deny-closed: `(deny file-write*)` +
  `(allow file-write* (subpath "<realpath root>"))`) and shells out
  `subprocess.run(["/usr/bin/sandbox-exec","-p",profile,*cmd])`
  [SOURCE: vcs-core/.../_seatbelt_containment.py:39,138 | VERIFIED].
- **Linux**: real **Landlock** via raw ctypes syscalls 444/445/446 + `PR_SET_NO_NEW_PRIVS`,
  self-restrict-before-`execvp`. Fully implemented, not stubbed
  [SOURCE: vcs-core/.../_landlock_containment.py:132,197 | VERIFIED].

A disallowed write is refused at the kernel (EPERM) **before it reaches disk** — not caught
at a merge gate [SOURCE: _containment.py:35 docstring | VERIFIED].

> Why deeper than us: our enforcement is fail-open hooks (advisory/block) + commit-time git
> guards. Hooks are dodgeable — global rule #18 ("acknowledge guardrails, don't route around
> them") exists *because* they are. Shepherd's jail can't be routed around. This is
> Constitution P1 (architecture over instructions) fully realized for the irreversible-state
> category.

### P2 — Fail-closed jail probe at launch (positive-control the enforcement before running)
Before any task body runs, `launch_confined` calls `probe()` fail-closed: it actively attempts
probe writes and raises `JailNotEstablished` unless the jail is BOTH live AND grant-conformant
(3 checks: out-of-workspace write denied, each granted root writable, in-workdir-outside-roots
denied) [SOURCE: vcs-core/.../_execution_capability.py:188,194 | VERIFIED]. No jail host →
refuses to run rather than running unconfined.

> Why deeper: this is our own "positive-control every filter at arm time" discipline
> (~/.claude/rules/wakeup-cadence.md) built into the substrate. We assert our sandboxes work;
> they verify it, actively, every launch.

### P3 — Permission surface = the type signature, statically inspectable
The grant lives in the function signature, is lowered automatically, and `shepherd task show`
renders it expanded. One inspectable place, no separate allow/deny config to drift from the code.

> Why deeper: our permission story is `settings.json` allow/deny + scattered hooks — the
> permission and the code that needs it are in different files. An interface-thinking win:
> the contract IS the permission.

Adjacent-but-not-core wins: whole-workspace CoW fork (APFS `clonefile`/OverlayFS) with
world-lineage receipts [SOURCE: vcs-core/.../_clonefile_carrier.py:29 | VERIFIED]; retained
output as a read-only `Changeset` that cannot mutate until settled [SOURCE:
workspace_control/run_outputs.py:222 | VERIFIED]; content-addressed Merkle DAG persisted over
real git via pygit2 [SOURCE: commons-vcs/.../backends/git.py | VERIFIED]; deterministic offline
provider run through the SAME jail for $0 identical-semantics testing [SOURCE:
dialect/.../providers.py:805 | VERIFIED].

## What is HOLLOW (do not cite these as facts)

- **"5× faster than docker commit" and "~95% KV-cache reuse on replay"** — the strings appear
  NOWHERE in the repo. No benchmark, no KV-cache code. Paper + companion `shepherd-experiments`
  only. In-repo "replay" is deterministic SQLite/continuation-trace replay, NOT LLM token-cache
  reuse [UNVERIFIED — paper-only claim, no runnable backing in-tree].
- **tree-RL / MCTS / meta-agent *training*** (the repo's own topic tags; the paper's "supervise,
  optimize, train" headline) — absent as working code; grep hits only CONTRIBUTING.md, replay is
  a self-labeled "spike, not a production API." The meta-agent story today = typed-task +
  `Scope.fork/restore/snapshot` + a `CritiqueTask` that reads another task's source
  [SOURCE: agent 3, VERIFIED absence].
- `shepherd2` is a skeleton ABI-freeze rewrite that explicitly EXCLUDES replay/supervision/
  provider/attenuation. Canonical working system is `shepherd` + `vcs-core` + `commons-vcs`.
- Maturity: well-tested for alpha (649 test files / ~9.3K `test_` fns) but `sandboxes/`
  (daytona/e2b/modal/k8s/prime) has 0 tests.

## Decision

| | |
|---|---|
| **Framework** | NO-ADOPT. Paradigm mismatch (typed-Python-task → sandbox → proposal vs our Claude-Code interactive/`/loop`); alpha; and NO incident where our fail-open hooks caused irreversible loss (git guards + worktree isolation have held). Adopting = high-blast-radius migration for unclear payoff. |
| **P1 syscall jail** | CAPTURE as reference design. Do NOT build now. |
| **P2 fail-closed probe** | CAPTURE. Cheapest to steal independently — a pre-run positive-control on any worktree/sandbox dispatch, no Shepherd needed. |
| **P3 permission-as-signature** | CAPTURE as interface-thinking prior-art. |

## Resurrection trigger

Build the Seatbelt/Landlock jail (P1) **only if a fail-open hook ever lets an agent perform
irreversible damage** to protected data / another repo (the Replit-DB-deletion class,
constitutional invariant #5). Until then, hooks + git guards are the measured-sufficient floor.
P2 (fail-closed probe) may be lifted independently the next time we harden sandbox dispatch —
it does not wait on P1.

## Related

- Constitution P1 (architecture over instructions); invariants.md #5 (no irreversible deletion).
- Global rule #18 (don't route around guardrails) — the exact weakness P1 closes.
- ~/.claude/rules/wakeup-cadence.md (positive-control watchers at arm time) — P2 is the same idea.
- decisions/2026-06-07-state-externalization-lens.md (externalize recoverable state) — the trace
  substrate is a maximalist version of this lens.
