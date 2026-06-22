# Substrate apply-handoff — backfill 0003 currency (incident fix)

**Status:** ready-to-apply · **Owner action:** apply in substrate, or hand to the live substrate
session (`018ee7c8`). NOT applied by the loop — substrate has a live checkout (committed 2 min ago);
direct edit = clobber risk.

**Why this is a handoff, not a direct edit:** boundary = another repo + a live peer session. The two
edits are append-safe and low-risk; they just must land in substrate by its owner.

**Context:** the general prevention (read-time currency whitelist gate) is now LIVE in agent-infra and
fires on `0003` already (status=`proposed` → warns "not current, don't execute"). These two edits are
the **backfill**: they record WHY 0003 is dead + what replaced it, so the warning is actionable and the
operator-confirmed correction is compaction-surviving. Decision:
`agent-infra/decisions/2026-06-21-decision-currency-whitelist.md`.

---

## Edit 1 — `docs/decisions/REFRAMINGS.md` (append a new section)

```markdown
## Absorb verification machinery onto claimcore (ADR 0003) — REVERSED to reconcile/project
**SETTLED (operator-corrected):** ADR 0003's "absorb genomics/phenome verification machinery INTO
claimcore" premise was REVERSED across [[0007]] (project from one ledger), [[0010]] (content-addressed
identity — reconcile, don't absorb; Phase-3 reversed the premise), and [[0011]] (verticals EMIT;
substrate owns the engine). Do NOT lift `CanonicalStageHash` into claimcore — build run-staleness right
in substrate ([[0011]]:26).
**NOT:** "execute ADR 0003's absorption set" — 0003 is `PROPOSED` and superseded-in-effect; it is NOT a
current/ratified direction.
**Refs:** ADR 0003, [[0007]]/[[0010]]/[[0011]], `deferred-and-open.md:24-26`. **corrected: 1×.**
```

(REFRAMINGS is already surfaced at SessionStart via `sessionstart-compact-resume.sh:46-49`, so this
becomes the compaction-surviving, ADR-keyed signal an agent sees before re-deriving the absorb framing.)

## Edit 2 — `docs/decisions/0003-unify-verification-machinery-onto-claimcore.md` (insert after the title/status, append-safe)

```markdown
> **⚠ Superseded-in-effect (2026-06-22):** the "absorb" premise was REVERSED by [[0007]]/[[0010]]/[[0011]]
> (reconcile/project, don't absorb; do NOT lift `CanonicalStageHash`). This ADR is `PROPOSED` and NOT a
> current direction — see `REFRAMINGS.md`. Do not execute its absorption plan.
```

(Optional once substrate adopts the flip-verb convention: change `**Status:** PROPOSED` →
`**Status:** SUPERSEDED-IN-EFFECT by [[0011]]` — but that is an in-place status edit; the blockquote
above is the append-only-safe form and the gate already fires on `PROPOSED`.)
