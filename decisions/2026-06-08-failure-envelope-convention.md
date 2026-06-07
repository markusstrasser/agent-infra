---
date: 2026-06-08
status: accepted
concept: agent-self-correction / check-output-format
supersedes: none
relates:
  - research/agent-dev-loop-tooling-2026-06.md
---

# Failure-envelope convention — make every gate one-turn self-correctable

## Decision

Every automated gate an agent hits — pre-commit hook, linter, test wrapper,
verification recipe — emits failures in a uniform, greppable envelope:

```
[<check>] BLOCKED — <one-line reason>
<optional detail an agent can grep to localize the problem>
fix: <a deterministic command the agent can run verbatim>
```

Rules:
- **`<check>`** is a stable identifier (recipe name, lint id) the agent can map
  back to a re-run.
- **reason** is one line. The agent decides its next move from this line alone.
- **`fix:`** names a **deterministic, idempotent project command** — a `just`
  target, a specific recipe — **never free-form generated shell**. The agent may
  run it directly; it must not be an injection surface or a stale-fix spiral
  (cross-model review 2026-06-08: a generated shell string is advisory text, but
  pointing at a real recipe removes the ambiguity entirely).
- On success, a check stays quiet or prints `[<check>] OK — <what passed>`.
- The **primary channel is stdout** — the agent reads it directly. Structured
  artifacts (JSONL report logs) are supplementary, added only where an agent
  demonstrably needs to parse them, not as a replacement for stdout.

## Why

Instructions are 0% reliable; the lever that actually shrinks supervision is
**externalizing recoverable state into the environment** (Harness-1). A blocked
agent's recovery is gated by how legible the block is. A uniform envelope with a
runnable `fix:` turns "agent stalls / asks the human / thrashes" into "agent reads
one line, runs one command, self-corrects." This is the generative principle
(declining supervision) applied to the check surface.

## This is a convention, not a shared library

Per the standing veto on cross-project utility libraries, there is **no shared
`emit_envelope()` import**. Each repo implements the format in its own checks
(a 3-line helper at most). The standard is the shared artifact; the code is local.

## Exemplars (already emitting the format)

- genomics bash pre-commit hooks (`[content-floor] ✗ BLOCKED …` + verbatim
  override command) — the original pattern this generalizes.
- genomics `scripts/verify_diff.py` — `[verify-diff] BLOCKED — … / fix: just …`
  (agent-infra@… → genomics 35f56ea3).
- genomics `scripts/lint_runner.py` — per-failing-linter `[lint:<recipe>]
  BLOCKED — exit N / fix: just <recipe>` (genomics 4611877e).
- genomics ast-grep rules — `error[<rule-id>]: <message>` at `file:line`
  (ast-grep native format; already envelope-shaped).

## Propagation

Adopt opportunistically: when a check in any repo is touched and its failure
output is not envelope-shaped, reshape it. No flag-day migration — the format
earns its place check-by-check, measured by whether agents self-correct from it.

## What this is NOT

Not a new dependency, not a hook, not enforced by a gate (the format is itself
the thing that makes gates legible — gating the format would be circular). It is a
documented standard with live exemplars, like `commit-conventions.md`.
