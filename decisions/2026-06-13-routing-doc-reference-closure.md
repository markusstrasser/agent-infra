---
id: 2026-06-13-routing-doc-reference-closure
concept: state-externalization
repo: agent-infra
decision_date: 2026-06-13
recorded_date: 2026-06-13
provenance: contemporaneous
status: accepted
initial_leaning: hand-fix the dangling refs the pliability scan found
relations:
  - type: depends_on
    target: 2026-06-07-state-externalization-lens
---

# 2026-06-13: Routing-doc reference closure — dangling refs are a state-externalization failure

## Context
A `/upgrade pliability` pass on agent-infra plus a 5-repo scan surfaced one recurring
class far more than monoliths or bad names: a **live routing doc** (CLAUDE.md, cockpit.md,
README, a `.claude/rules/*.md`) pointing at a file that was deleted, moved, or absorbed.
Concrete instances — cockpit.md → dead `runlog.md` (its DB 0-byte since 2026-04);
intel `CLAUDE.md:59` → `_archived/INDEX.md` (moved in the 2026-05-11 rules refactor);
`skills/README.md` → 13 deleted skills (incl. `agent-pliability` itself); ~47
`~/Projects/meta/` refs left by the meta→agent-infra rename. Same failure in **3 of 5**
repos. The passive "file names are the index" rule could not catch it, and the existing
`skill_reference_validator` structurally could not see it (it checked absolute paths and
skipped `.md`/`.py` refs; it never scanned root routing docs).

## Alternatives considered
1. **Hand-fix each dangling ref** (initial leaning) — fixes today's instances, does nothing
   for recurrence; ~47 `meta/` refs + prose-mention false positives make it expensive and
   error-prone to do across sibling repos semi-blindly.
2. **Generic markdown link-checker** (lychee / markdown-link-check) in CI — mature, but
   checks markdown `[x](link)` targets only. The cases that bit us were backtick inline-code
   mentions and bare refs, which link-checkers don't see; and none catch skill-NAME inventory
   drift. Wrong instrument for the actual failure.
3. **Hard-gate a custom dangling-ref lint in smoke** — highest enforcement, but the measured
   hit count (2078 → 302 → 53 as precision improved) has irreducible false-positive classes:
   tombstones that name dead files *on purpose*, archival-*pattern* names, and
   documented-but-unbuilt data-layout paths. A blocking gate fails on legitimate prose.
4. **Extend the existing validator with a routing-surface-scoped, advisory relative-ref check,
   and generate the inventories that drift** (chosen).

## Counterevidence sought
Searched for whether a hard gate is justifiable now by running the lint at three precision
settings (2078 / 302 / 53 hits). Even at 53, inspection showed roughly half are intentional —
tombstone mentions (`session-forensics.md` naming retired `runlog.py`), archival-pattern names
(intel rules citing "the `_archived/INDEX.md` pattern"), and unbuilt data paths (phenome
`indexed/*.json`). That falsifies "make it blocking"; advisory is correct until those classes
are allowlisted. Searched for an off-the-shelf tool that catches the actual failure (backtick/
bare refs + skill-name inventory): lychee / markdown-link-check catch neither, so a thin
extension of the existing validator is warranted over a new dependency.

## Decision
Treat dangling references as a **state-externalization failure**: the index/inventory is
recoverable from the filesystem, so storing it by hand guarantees drift
([[2026-06-07-state-externalization-lens]]). Two-pronged:

- **Detection** — extend `skill_reference_validator.py` to scan the routing surface
  (`CLAUDE.md`/`AGENTS.md`/`GEMINI.md`/`README.md` + `.claude/rules/*.md`) for path-shaped
  relative refs that resolve to no file on disk. Advisory by default, `--strict-refs` to gate;
  wired into `just smoke` informational. Skips bare basenames (prose mentions), cross-repo
  sibling prefixes, and fenced code.
- **Prevention** — generate the inventories that drift instead of hand-maintaining them:
  regenerated the `skills/README.md` skill table from `skill_manifest.jsonl` with a
  do-not-hand-maintain marker.

Point-fixed the genuine *pointers* (cockpit→runlog, intel `CLAUDE.md:59`, two abandoned root
docs). Did **not** bulk-rewrite prose-mention FPs (intel `_archived/INDEX.md` ×5 are
archival-pattern names, not pointers an agent follows) — the advisory lint now tracks them for
the owning repo's own pass.

## Evidence
Precision sweep 2078 → 302 → 53 (routing-scope + path-shaped-only + cross-repo skip + a
`str.lstrip("./")` bug fix that had been mangling every `.claude/...` ref). agent-infra itself:
2 residual (a tombstone + a cross-repo ref). Cross-repo scan: 3/5 repos carried the
dead-reference class; phenome and genomics came back clean. Commits: 9fdde09, 0470daa,
a75615ef, 6702990, 3951cbc, a56b3bc.

## Revisit if
- The FP classes get allowlist markers (tombstone / pattern-name) → promote `--strict-refs` to
  a real smoke gate.
- A second inventory drifts the way `skills/README` did → wire generate-on-read for it rather
  than regenerate-once.
- The `meta/` husk refs get cleaned in skills/genomics → drop `meta` from the not-a-sibling
  carve-out (it is currently kept flaggable on purpose).

## Supersedes
None. Extends [[2026-06-07-state-externalization-lens]].
