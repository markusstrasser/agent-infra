# Phenome cascade-deletes leave orphaned corpus annotations — add supersede-on-delete to its mutation gateway?

**Boundary:** shared (phenome mutation gateway + the shared corpus ledger; mirrors the genomics cross-attestation contract in CLAUDE.md `<cross_project_rules>`)
**Recommendation:** Add a supersede/retract enqueue to phenome's mutation gateway so that when a verdict/assertion is cascade-deleted, the corresponding corpus annotation is superseded in the same transaction — mirroring genomics `MutationGateway._enqueue_corpus_attestation`. Low urgency: 6 orphans, advisory-only, non-blocking.
**Dissent / risk:** The orphans may be *acceptable* — a corpus annotation recording "phenome once asserted X" is arguably still true history even after X's backing claim is deleted (append-only ledger ethos: mark stale, don't delete). If so, the fix is the opposite: teach `audit_corpus_sync` to treat post-deletion orphans as expected (a tombstone join), not drift. Picking supersede-on-delete vs. tolerate-as-history is the actual decision.
**Open question for you:** When phenome intentionally deletes a claim (Phase 2c deleted 752 pseudo-entities), should its corpus annotation be **retracted** (supersede-on-delete) or **kept as historical record** (audit tolerates the orphan)?
**Reversible?** Yes — either direction is a small gateway/audit change; the 6 orphans cause no data loss, only a persistent advisory exit-1 on the daily `audit-corpus-sync` job.

## What's established (this session, verified)

- **Stable, not transient.** I triaged this at 14:55 as "surgery-in-flight, recheck at 04:30." Re-checked read-only at 19:10 (`audit_corpus_sync.py --no-drain --json`): **same 6 phenome orphans, 4.5h unchanged**, despite continuous phenome claim commits (dade42d3, cb28843e, 63bf1347). The transient assumption is **falsified** — this is settled drift, not a moving target.
- **Mechanically healthy job.** `com.agent-infra.audit-corpus-sync` exits 1 = "drift detected" (by design; argparse help: "Emit JSON; non-zero exit on drift"). The launchd "red" is the advisory signal firing, not a broken job. genomics 459/459 clean, intel 0/0 clean, phenome 52 local / 52 annotated / **6 orphan**.
- **Cause:** phenome's Phase 2b/2c claim surgery (752 scaffold-value pseudo-entities cascade-deleted, commits 3d9da6e8/04f95bbe/bfde8976) removed verdicts whose corpus annotations remain. genomics' gateway already enqueues supersede intent inside the delete txn; phenome's does not.

**Evidence:** `audit_corpus_sync.py` summary (phenome orphan=6, stable 14:55→19:10); CLAUDE.md `<cross_project_rules>` (genomics reference impl); phenome commits 3d9da6e8 / 04f95bbe; maintenance-actions.jsonl 14:55 + 19:10.
