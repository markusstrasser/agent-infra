## PHASE 0: TRIAGE GATE

Session b8098df4: YES
Session 019d6d86: YES

[2026-04-08] RECURRENCE: Exec session leak via blocking CLI commands (019d6d86)
[2026-04-08] RECURRENCE: HOOK OWNERSHIP GUARD INCOMPATIBLE WITH CODEX CLI (019d6d86)
[2026-04-08] RECURRENCE: Inline python3 -c journal queries instead of proper tooling (019d6d86)
[2026-04-08] RECURRENCE: MANUAL JOURNAL/STATE SURGERY (019d6d86)
[2026-04-08] RECURRENCE: Blind fix deployment — deployed fixes then waited for timeout without verifying (019d6d86)

### [CAPABILITY ABANDONMENT] [W:5]: Failed to follow tool CLI contract for review script
- **Session:** b8098df4
- **Score:** 1.0
- **Evidence:** `uv run python3 .../model-review.py --context .model-review/finding-ir-oss-context.md --context-files scripts/finding_ir.py ...` -> `error: argument --context-files: not allowed with argument --context`
- **Failure mode:** NEW: CLI argument collision
- **Proposed fix:** skill | Update review skill instructions to explicitly warn that `--context` and `--context-files` are mutually exclusive.
- **Severity:** medium
- **Root cause:** skill-execution

### [RULE VIOLATIONS] [W:3]: Failed to include turn budget in subagent dispatch prompt
- **Session:** b8098df4
- **Score:** 1.0
- **Evidence:** Tool error: `SYNTHESIS BUDGET REQUIRED: Dispatch prompt missing turn-budget instruction`. Agent had to retry the `Agent` tool call.
- **Failure mode:** NEW: Ignored explicit subagent prompt constraints
- **Proposed fix:** hook | Maintain the existing `pretool-subagent-gate.sh` hook, as it successfully caught the violation.
- **Severity:** low
- **Root cause:** agent-capability

### [REASONING-ACTION MISMATCH] [W:4]: Hacked around a VCF sample name mismatch instead of fixing the data provenance
- **Session:** 019d6d86
- **Score:** 1.0
- **Evidence:** "bcftools call is using sample name markus, but the mpileup stream does not have a sample called markus... I’m removing that boundary entirely for this stage rather than burning more retries on sample-file interpretation."
- **Failure mode:** NEW: Workaround instead of root-cause fix
- **Proposed fix:** rule | Mandate that data contract mismatches (like missing VCF samples) must be fixed at the source rather than bypassed by removing validation.
- **Severity:** medium
- **Root cause:** task-specification

### [BUILD-THEN-UNDO] [W:4]: Introduced raw json.dump then reverted to use existing atomic writer after hook failure
- **Session:** 019d6d86
- **Score:** 1.0
- **Evidence:** Agent wrote `json.dump(...)`, hook failed (`touched_files_no_new_raw_json_dump_to_file`), agent then rewrote to use `write_json_atomic`.
- **Failure mode:** NEW: Ignored existing codebase conventions until forced by hook
- **Proposed fix:** rule | Add rule to prefer existing codebase utility functions (e.g., `write_json_atomic`) over raw stdlib equivalents.
- **Severity:** low
- **Root cause:** skill-execution

### [TOKEN WASTE] [W:3]: Premature documentation of root causes led to repeated memo corrections
- **Session:** 019d6d86
- **Score:** 1.0
- **Evidence:** Agent documented `prs_dosage_ci` failure as an `init_stage` bug in the audit memo, then later discovered the real issue was a 500M loop and had to append a correction. "The audit memo is stale on one important point now... I’m appending that revision..."
- **Failure mode:** NEW: Premature documentation
- **Proposed fix:** rule | Do not write root causes into persistent audit memos until the fix has been deployed and verified.
- **Severity:** low
- **Root cause:** skill-execution

### Session Quality
| Session | Mandatory failures | Optional issues | Quality score (S) |
|---------|--------------------|-----------------|-------------------|
| b8098df4 | 1 | 1 | 0.15 |
| 019d6d86 | 2 | 1 | 0.30 |