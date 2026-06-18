---
id: 2026-06-18-phaseB-implements-trailer
concept: lifecycle-graph-spine
repo: agent-infra
status: spec — awaiting operator sign-off (B2-hook is the only gated piece; B1 + B2-lite are autonomous)
decision_date: 2026-06-18
relations:
  - type: depends_on
    target: 2026-06-07-verifier-conditional-autonomy
---

# Phase B — `Implements:` ship-time edges: a B1 (ungated) / B2 (gated) ladder

Spec for Phase B of the RSI lifecycle-graph spine (Phase A `ee2955a`/`647b9b1`,
Phase C agentlogs-native `aa49e4b` already shipped). Phase B captures `Implements:`
edges (commit → decision/finding) to densify the graph's currently-sparse
commit→decision edge (Phase C reindex today: **9 dangling**, log→decision join ~25%).

## TL;DR

Phase B splits cleanly, and **most of the densification value is in the ungated half**:

- **B1 — read-side recovery (agentlogs-local, NO gate, autonomous).** Extend
  `git_import.py` to (a) populate `git_commits.body`, (b) parse `Implements:`
  trailers + resolving decision-id mentions → `lifecycle_edges` as `commit
  --implements--> decision` (traversable). **Recovers ~23 edges from existing
  history today** (probe below). No shared-infra touch.
- **B2 — write-side, makes FUTURE commits reliably carry the trailer.** A ladder:
  - **B2-lite** — a `CLAUDE.md` convention ("write `Implements: <slug>` when a
    commit implements a decision"). Ungated (agent-infra doc). Adherence is then
    *measurable* via B1's parser.
  - **B2-hook** — a `prepare-commit-msg` opt-in scaffold that auto-appends the
    trailer like Session-ID. **Shared global git hook ⇒ constitution hard-limit
    #4 ⇒ needs your explicit sign-off.** Build ONLY if B2-lite adherence is
    measured insufficient (constitution P1: instructions ~0% reliable on what
    matters; P3: measure before enforcing).

**Recommendation:** build B1 now (ungated, recovers history); ship the B2-lite
convention; keep B2-hook spec-only behind a measured-low-adherence gate + sign-off.

## Grounding probes (2026-06-18, agent-infra)

```
git_commits rows: 12924 | with non-empty body: 0
  → body column exists but git_import does NOT populate it; B1 must add that first.
distinct decision-slugs mentioned in commit bodies AND resolving to decisions/: 23
  (last 400 commits) → real, recoverable commit→decision edges sitting in history.
existing Implements:/Decides:/Refutes:/Supersedes: trailers: 0 → greenfield, no migration.
```

## B1 — read-side edge recovery (autonomous, no gate)

Lives entirely in agentlogs (the Phase C home). No shared hook, no commit-flow change.

1. **`git_import.py`: populate `git_commits.body`.** The column exists, is empty.
   Populate it during import (the per-commit `%b` is already available to the
   git-log parse). One-time reindex backfills all 12,924 rows.
2. **`src/agentlogs/lifecycle.py`: parse body → edges.** In `build_edges`, after
   the frontmatter pass, scan `git_commits.body` for:
   - explicit `^Implements:\s*<slug-or-SHA>` trailers (the forward path, 0 today);
   - best-effort: any `YYYY-MM-DD-slug` (or `decisions/<slug>`) that resolves to a
     decision node → a `commit --implements--> decision` edge, `source =
     'commit-mention'` (lower-confidence than `'commit-trailer'`, both traversable).
   Unresolved mentions stay `dangling` (already handled). Edge type = `implements`
   (already canonical in `lifecycle_relations.json`).
3. **`lifecycle_neighbors` query** already surfaces these (it selects by
   subject/target); a decision node now shows the commits that implement it.

**Effort:** ~1 module-pass + a git_import field. **Gate:** reindex shows
commit→decision edge count rise from ~0 to ~23; `just graph <a-decided-slug>`
lists implementing commits. **Autonomy:** agentlogs-local, reversible → I can build
this without sign-off.

## B2 — reliable forward authoring (the gated escalation)

`implements` is **ship-time/immutable** (a commit DID implement X — a historical
fact), which is *why* it belongs on the commit (trailer), not in mutable decision
frontmatter. This is the edge-KIND split the Phase-4 critique required: design-time
relations (decision→decision) stay in frontmatter; ship-time edges (commit→decision)
live on commits. No edge authored in two places.

The open problem: *which* decision a code commit implements is **not ambient-
derivable** (unlike Session-ID, which is). Only the author knows. So "reliably
present like Session-ID" needs one of:

- **B2-lite (build now, ungated):** a one-line `CLAUDE.md` convention. Adherence
  measured by B1's parser (how many new commits carry `Implements:`). Cheapest;
  honors measure-before-enforce.
- **B2-hook (GATED, build only if B2-lite adherence is low):** a
  `prepare-commit-msg` step (sibling to `prepare-commit-msg-session-id.sh`) that
  auto-appends `Implements:`. Two candidate signals (operator picks IF we get here):
  - **session→decision binding** — agent sets `.claude/current-decision` once when
    starting work on a decision; the hook auto-appends `Implements: <that>` to every
    commit in the session (declare once, reliable thereafter — closest to the
    Session-ID model);
  - **commented-template fill** — the hook injects `# Implements: <best-guess>?`
    for the agent to uncomment (weaker; suggestion-shaped).
  Default to NO trailer when no signal — the abandoned Session-ID *suggestion*
  was 97% noise (1,996/2,065 commits, measured 2026-06-12); do not repeat that.

### Hard-limit #4 (B2-hook only)

`prepare-commit-msg` is wired in **global `~/.claude/settings.json`** — it fires in
*every* repo. B2-hook is therefore a live shared-infra change. Mitigation (GPT-5.5's
altitude fix): the scaffold is **inert unless the repo opts in** (a
`.claude/lifecycle-trailers` marker, or presence of `lifecycle_relations.json`) —
shared mechanism, repo-local policy. agent-infra opts in; genomics/phenome unaffected.
**Even so, deploying it edits the shared hook → explicit operator sign-off required.**
B1 and B2-lite are NOT shared-infra (B1 = agentlogs-local; B2-lite = agent-infra doc).

## Measure-first gate (when B2-hook earns its build)

Build B2-hook only after ALL of: B1 live · B2-lite shipped · measured `Implements:`
adherence on new commits < ~50% over ≥N commits · `just graph` answers still
materially incomplete *because* commit→decision edges are missing (not because the
view is unused). Until then B2-hook stays spec-only. This is the same
demonstrated-demand bar the Phase-4 critique set for the whole of Phase B.

## Open for operator

1. **Build B1 now?** Autonomous, ungated, recovers ~23 historical edges + makes the
   graph self-densifying from commit history.
2. **B2-lite convention** — ship the one-line `CLAUDE.md` rule, or hold until B1
   shows whether the edge is even the binding gap?
3. **B2-hook signal** (only if we get there): session→decision binding vs
   commented-template — which feels right? (My lean: session→decision binding.)
