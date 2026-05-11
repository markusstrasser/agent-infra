---
title: Phase 0 preflight audits — shared papers store migration
date: 2026-05-11
status: complete
verdict: BLOCKED — three issues require resolution before Phase 2 migration
---

# Phase 0 preflight audits — shared papers store migration

Done inline (~10 min) after a subagent stalled at 87 lines / 0 output dir
in 20 minutes. Four audits, in order of blocking severity.

## Top-line verdict

**Migration BLOCKED on three findings.** None catastrophic. All resolvable
with explicit migration-time work, but the original Phase 2 plan's
"single atomic transaction" assumption needs revision.

| # | Finding | Severity | Resolution |
|---|---|---|---|
| 1 | `claim_binding_hash` is path-coupled via SourceRecord JSON | **BLOCKER** | Migration must rewrite SourceRecord JSON AND run rebind drain on all 492 verdicts |
| 4 | 77 DOI-slug collision pairs in existing 248 bundles | **BLOCKER** | One-time slug-form merge (dot vs underscore) before/during migration |
| 2 | 21 of 27 genomics worktrees are divergent / unmerged; 14 dirty | warning | Filter-repo will orphan their HEADs; merge or delete first |
| 3 | 1 hardcoded genomics SHA in non-genomics repos | trivial | Single find/replace post-migration |

## Finding 1: `claim_binding_hash` path coupling — BLOCKER

**Audit:** Trace every call site of `claim_binding_hash`, classify by
whether the hash inputs include path strings.

**Result:** The hash function itself doesn't take paths — it hashes the
canonical claim payload (target_ref, owner_key_path, source_ids,
attestation, lifecycle_state) PLUS `cited_source_hashes` from
`SourceSnapshot`.

`SourceSnapshot.cited_source_hashes(source_ids)` returns
`sha256(json(SourceRecord))` per cited source. **SourceRecord JSON
contains literal paper_evidence/* paths:**

```json
{
  "source_id": "doi:10.1002/art.27190",
  "retrieved_path": "config/source_retrievals/doi_10.1002_art.27190.json",
  "retrieved_sha256": "cf478b4c...",
  "paper_bundle": {
    "bundle_path": "paper_evidence/doi_10.1002_art.27190",
    "bundle_manifest_path": "paper_evidence/doi_10.1002_art.27190/manifest.json",
    "bundle_manifest_sha256": "33448701...",
    "markdown_path": "paper_evidence/doi_10.1002_art.27190/paper.md",
    "markdown_sha256": "621be45d...",
    "tables_path": "paper_evidence/doi_10.1002_art.27190/tables.md",
    ...
  }
}
```

Six path fields per paper-backed SourceRecord
(`retrieved_path`, `bundle_path`, `bundle_manifest_path`, `markdown_path`,
`tables_path`, `figures_path`) all reference `paper_evidence/<slug>/...`.

**Implication for Phase 2 migration:**

Moving files from `paper_evidence/<slug>/` to `~/Projects/papers/<paper_id>/`
requires editing every paper-backed SourceRecord's path fields. Those
edits change the SourceRecord JSON → `cited_source_hashes` flips → every
verdict that cites the source has its `claim_binding_hash` mismatched.
The Phase B source-kind backfill earlier this week already invalidated
~290 verdicts the same way; another sweep would invalidate them again.

**Two viable resolutions:**

1. **Re-rebind during migration** (consistent with the genomics Phase 2
   already shipped at `338fe2a4`): migration script writes new
   SourceRecord JSON + immediately enqueues every affected claim for
   rebind via `seed_rebind_for_stale_or_unbound_verdicts`. Subsequent
   `knowledge drain --tier <T> --budget-approved` actually re-runs the
   verifier. Cost: same as Phase 2 of the genomics plan
   (~$5-15 clinical, ~$30 full).

2. **Schema migration to canonical_paper_id**: drop the path fields from
   SourceRecord; add `canonical_paper_id: str` pointing at the canonical
   store; consumers resolve paths via `paper_store.paper_path()`. The
   SourceRecord JSON becomes path-free → `cited_source_hashes` becomes
   path-independent → migration doesn't invalidate verdicts. **This is
   the cleaner long-term move** but requires updating
   `build_source_paper_bundle.py` + all 8 known readers (the same set
   I audited for Phase 2 of the shared-store plan).

Recommend (2). It's a one-time schema change, reduces drift risk
permanently, and aligns with the shared-store plan's
"`canonical_paper_id` on SourceRecord as the only cross-reference"
design decision.

## Finding 2: Stale worktrees — warning

27 worktrees under `~/Projects/genomics/.claude/worktrees/`:
- 6 in main history (safe to delete)
- **21 divergent / unmerged** — their HEADs would be orphaned by a
  history rewrite (filter-repo invalidates commit SHAs)
- 14 have uncommitted local changes

Migration would silently break in-flight work in these. Resolution:

```bash
# Inventory
for wt in ~/Projects/genomics/.claude/worktrees/*; do
  head=$(git -C "$wt" rev-parse --short HEAD)
  dirty=$(git -C "$wt" status --porcelain | wc -l)
  git -C ~/Projects/genomics merge-base --is-ancestor "$head" main \
    && echo "  $wt: in-main, $dirty dirty — DELETE safe" \
    || echo "  $wt: divergent, $dirty dirty — MERGE OR ABANDON"
done
```

Operator decision per worktree before Phase 2 force-push. Likely most
divergent ones are abandoned experimental branches and can be deleted.

## Finding 3: Cross-repo genomics SHA references — trivial

`git grep` across phenome, agent-infra, research-mcp for any 7-40 char
hex strings that resolve to a genomics commit:

| Repo | Count of genomics-resolved SHAs |
|---|---|
| phenome | 0 |
| agent-infra | 1 (`2550686`) |
| research-mcp | 0 |

Post-migration, run `git -C ~/Projects/agent-infra grep -l 2550686` and
update the single reference to the rewritten SHA. Trivial.

## Finding 4: DOI slug collisions — BLOCKER

Computed proposed `paper_id` for every bundle in `paper_evidence/`:

```
Total bundles: 248
Unique paper_ids after slug normalization: 171
Collision groups: 77
```

Every collision pair is the SAME DOI represented in two slug forms:
- Old genomics convention: `doi_10.1002_art.27190` (preserves `.`)
- New shared-store convention: `doi_10_1002_art_27190` (normalizes `.`→`_`)

Examples:
```
doi_10_1002_ajmg_b_32213: ['doi_10.1002_ajmg.b.32213', 'doi_10_1002_ajmg_b_32213']
doi_10_1002_art_27190:    ['doi_10.1002_art.27190',    'doi_10_1002_art_27190']
...
```

This isn't a true paper-identity collision — it's a partial-migration
artifact (the genomics agent's Phase 0a writer was using the new
convention while the older bundles still have the legacy dot form).

**Resolution:** Migration script merges each collision pair into the
canonical form. Decision: keep the new convention (`.`→`_`), so 77 pairs
need merging by:

```python
for old_dir, new_dir in collision_pairs:
    # Merge new into old by content sha; conflict if both have differing PDFs
    merge_bundle(old_dir, new_dir)  # rename + dedupe metadata
```

This must happen INSIDE the migration script before any
SourceRecord-JSON rewrites — otherwise the new SourceRecord
`canonical_paper_id` ambiguates.

## What changed since the original plan

The plan said "DOI collision count = 0 (or resolved with manual
suffixes)". Reality: 77 collisions exist due to a migration-in-progress
that landed during this session. They're not random — they're a
deterministic slug-form drift. A migration script that normalizes both
forms to the canonical underscore form handles them.

The plan said `claim_binding_hash` should be content-coupled vs
path-coupled. Reality: it's content-coupled to a JSON blob THAT
CONTAINS PATHS. So functionally path-coupled. Resolution: schema
migration (drop paths from SourceRecord, add canonical_paper_id) OR
accept that migration triggers a full rebind drain.

## Audit provenance

- Computed inline in session 13a597a5 after subagent stalled
- Replaces unrunnable subagent `a3c531236654b37fc.output` (killed at 87 lines)
- All commands re-runnable from this directory's `audit-commands.md`

## Files in this directory

- `INDEX.md` — this report

<!-- knowledge-index
generated: 2026-05-11T06:47:31Z
hash: 091aec2fc753

title: Phase 0 preflight audits — shared papers store migration
status: complete

end-knowledge-index -->
