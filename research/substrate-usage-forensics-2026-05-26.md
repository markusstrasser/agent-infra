---
title: Cross-Attestation Substrate — Usage Forensics
date: 2026-05-26
status: active
tags: [substrate, attestation, corpus, post-mortem]
---

# Cross-Attestation Substrate — Usage Forensics

## Verdict

The substrate is unused **primarily because of wrong wiring**: the MCP layer (`record_verdict` + `corpus_attest` ritual) is registered but the real verdict-write path bypasses MCP entirely (Bash → `cli.py drain` → `mutation_gateway.write_verdict()`), so the PostToolUse hook never has anything to remind. Demand exists (459 genomics verdicts written in the indexing window) — the agent invokes scripts, not MCP tools. Secondary: in phenome and intel, the contract is a wire-shape placeholder (`not_implemented_yet` / `unsupported`), so even if the agent tried to use it, the call would no-op.

## Evidence by question

### Q1. Is `record_verdict` actually exposed as an MCP tool?

Yes in all three repos — but two are stubs that always return placeholder status.

| Repo | File:line | Behavior |
| --- | --- | --- |
| genomics | `/Users/alien/Projects/genomics/scripts/genomics_mcp.py:2094-2125` | Registered. Returns `{"status": "not_implemented_yet", "message": "wire shape only; full write via MutationGateway"}`. Never writes anything. |
| phenome | `/Users/alien/Projects/phenome/mcp/src/phenome_mcp/substrate_tools.py:111-140` | Registered. Returns `{"status": "not_implemented_yet"}`. |
| intel | `/Users/alien/Projects/intel/tools/theses_mcp.py:471-496` | Registered. Returns `{"status": "unsupported", "error_code": "record_verdict_not_implemented"}`. |

So even if an agent followed the substrate ritual literally — step 1 `record_verdict` → step 2 `corpus_attest` — step 1 would be a no-op in every repo. The 2-call ritual the CLAUDE.md HARD RULE describes has no functional step 1 in the codebase today.

### Q2. What is the actual write path for verdicts?

**Genomics** — direct Python via Bash, never MCP. The agent runs `scripts/knowledge/cli.py drain ...`, which calls `MutationGateway.write_verdict()` (`/Users/alien/Projects/genomics/scripts/knowledge/mutation_gateway.py:443`, raw `INSERT INTO claim_verdicts`). agentlogs confirms: every verdict-producing invocation in 2026-05-11..23 was a Bash call to `cli.py drain` with `--model-version direction-d-router-stub`.

```
sqlite3 ~/.claude/agentlogs.db "SELECT s.project_slug, COUNT(*) FROM tool_calls tc
  JOIN runs r ON tc.run_id=r.run_id JOIN sessions s ON r.session_pk=s.session_pk
  WHERE s.start_ts>='2026-05-11' AND s.start_ts<'2026-05-24'
    AND tc.tool_name='Bash'
    AND (tc.args_json LIKE '%verdict%' OR tc.args_json LIKE '%mutation_gateway%')
  GROUP BY 1"
# genomics 260  intel 95  phenome 24
```

**Phenome** — has its own cert-stack tables (`current_assertions`, `assertion_evidence`, `answer_closure_certificates`, `claim_certificate_events`, etc.). No `cert_attestations` table exists — the audit script's `SELECT … FROM cert_attestations` query at `/Users/alien/Projects/agent-infra/scripts/audit_corpus_sync.py:62` would error if the table were required (it tolerates missing tables silently). Verdict-shaped writes happen through whatever the cert-stack mutation gateway is; that path also does not call corpus_attest.

**Intel** — has `entry_readiness_certificates`, `monitoring_certificates`, `contradiction_resolutions_log`. No `claim_verdicts` table; the audit's SQL `SELECT verdict_id FROM claim_verdicts` would also error against the live schema. Intel's MCP intentionally returns `unsupported` for record_verdict.

**The 360 genomics annotations dated 2026-05-11 18:47** were not organic — they came from a **one-shot migration script** `/Users/alien/Projects/agent-infra/scripts/migrate_genomics_phase5.py:184-242` that imports `corpus_core.annotate` directly (NOT MCP) and backfilled annotations for the verdicts already in the DB at that time. Same pattern for the 28 phenome annotations on 2026-05-11 10:22 (`migrate_phenome_source_records.py:166-190`, `actor_id="urn:agent:service:phase-6-migration@2026-05-11"`). All of `actor_type=service` (389/396 annotations) are migration/CLI writes, never agent-orchestrated.

### Q3. Was there opportunity (denominator) for the ritual?

Yes, substantial.

```
sqlite3 ~/.claude/agentlogs.db "SELECT project_slug, COUNT(*) FROM sessions
  WHERE start_ts>='2026-05-11' AND start_ts<'2026-05-24'
  GROUP BY 1 ORDER BY 2 DESC"
# publishing 73  intel 60  genomics 41  phenome 36  agent-infra 31
```

Of those, 260 genomics Bash calls + 95 intel + 24 phenome touched verdict/mutation_gateway/assertion code. **Zero** of them made a `record_verdict` or `corpus_attest` MCP call (tool_calls table, full history 2025-08 → 2026-05-23):

| Tool | Calls |
| --- | --- |
| `mcp__research__list_corpus` | 114 |
| `mcp__corpus__corpus_lookup` | 3 |
| `mcp__corpus__corpus_dashboard` | 1 |
| `mcp__*__record_verdict` | **0** |
| `mcp__corpus__corpus_attest` | **0** |

The denominator is "every session that ran a drain in genomics" — that's where the 166 new verdicts after 2026-05-11 came from (genomics grew 293 → 459 between the two recorded audit runs; all 166 missing annotations are `direction-d-router-stub` writes from `cli.py drain` invocations on 2026-05-13).

### Q4. Did genomics' 360 verdicts also call corpus_attest?

Yes — via Python import, not MCP. `migrate_genomics_phase5.py` calls `corpus_annotate(canon_sid, repo="genomics", actor_type="service", actor_id="urn:agent:service:direction-d-router-stub", scope="verdict", ...)` in a loop after the canonical_source_id backfill. All 360 share the same actor and were written in a 12-minute window (`18:47:47` → `18:59:38` on 2026-05-11). The architecture works — just not via the MCP path the rule describes.

So the 2-call ritual reads more naturally as: "if you use the MCP write tool, the hook will remind you to use the MCP attest tool." If you bypass both (which everyone does in practice), the hook has no anchor and the rule has no enforcement surface. The only path that currently produces attestations is `corpus_core.annotate` imported by migration scripts — which is exactly the layer the constitution says SHOULD be the single writer (good!) — but only the migration scripts know to use it.

### Q5. Is the hook firing?

Effectively never. `~/.claude/event-log.jsonl` shows the corpus-attest-remind hook has fired **3 times total**, all on 2026-05-15 within a single agent-infra session (`cc2de7bd-b88e-4c97-a5dc-f8f763014bbf`) with detail values `phenome:v789`, `intel:v_intel_99`, `phenome:pending` — these look like a test/probe invocation, not real verdict-recording work.

The matcher (`~/.claude/settings.json:360`) is:
```
mcp__phenome__record_verdict|mcp__intel-theses__record_verdict|mcp__genomics__record_verdict|mcp__evals__record_verdict|mcp__agent-infra__record_verdict
```
This is **PostToolUse** + an MCP tool pattern. Since 0 of those MCP tools have ever been called by an agent (Q1+Q2), the hook is correctly wired but watching the wrong invocation layer. It cannot fire on a Bash invocation of `cli.py drain`.

`audit_corpus_sync.py` (the second enforcement layer) IS running daily and IS detecting the drift: `drift_total: 166` in 11 of the last 12 runs (genomics: `verdicts_local=459, verdicts_annotated=293, missing_annotations=166`). The audit is the only surface where the drift is visible — nothing acts on the report.

## What to do

Ranked by ROI. Items 1–2 are mechanical; 3–4 are design choices.

### 1. Move the hook trigger from MCP to mutation_gateway (highest ROI, fully mechanical)

Replace the PostToolUse `mcp__*__record_verdict` matcher with a PostToolUse Bash matcher on commands that invoke the gateway (`cli.py drain`, `cli.py write-verdict`, etc.). Or — better, since the matcher would be fragile — add the corpus_attest call **inside** `MutationGateway.write_verdict()` at `/Users/alien/Projects/genomics/scripts/knowledge/mutation_gateway.py:443`. The gateway already has the verdict_id, claim_binding_hash, model_version, and source_observations needed; it can call `corpus_core.annotate.annotate(...)` in the same BEGIN/COMMIT span and the 2-call "agent ritual" collapses to a 1-call gateway invariant.

This is the same pattern the constitution endorses ("Architecture over instructions… Instructions alone = 0% reliable"). The advisory hook is instruction-shaped; the gateway side-effect is architecture-shaped. The audit script becomes a backstop for a property that's enforced at write time.

Caveat (flag-the-choice): doing this in the gateway makes corpus a hard dependency of genomics writes. If corpus is unavailable (graph.duckdb locked, corpus dir missing), the verdict write fails. Mitigation: wrap the annotate call in try/except and fail-soft to a local queue (`pending_corpus_attestations.jsonl`) that the audit job drains. This is fully reversible and meta-only-blast-radius if done in genomics' own gateway.

### 2. Drain the existing 166-verdict backlog (mechanical, no design choice)

The 166 missing annotations are knowable today: `migrate_genomics_phase5.py` already has the canonicalization + annotate loop. Run a one-shot variant that filters to verdicts where `verdict_id NOT IN (annotations.output_uri matching genomics://verdicts/...)`. ~30 seconds of script time, eliminates the standing `drift_total: 166`.

### 3. Decide phenome/intel substrate status explicitly (design choice — flag)

The audit's per-repo SQL fragments assume tables that don't exist (`cert_attestations` for phenome, `claim_verdicts` for intel). Three reasonable paths, all need user judgment:

- **(a) Land record_verdict for real in phenome and intel.** The wire shape is registered; the implementation isn't. This is a real multi-session piece of work because each repo's "verdict equivalent" has different ID/projection semantics. Probably the largest piece of work in this whole investigation.
- **(b) Update the substrate spec to reflect that genomics is the only producer.** Phenome's cert-stack and intel's theses-graph are different abstractions; mapping them through the verdict-shaped ritual may be category-error. Document this and remove the placeholder MCP stubs.
- **(c) Pick a per-repo natural emission point** (cert events for phenome, contradiction-resolution events for intel) and wire those to corpus_attest separately, dropping the "ritual" framing entirely.

The substrate decision record (`decisions/2026-05-11-cross-attestation-substrate.md` §J.1) committed to the agent-orchestrates-two-calls pattern. Reversing that mid-flight is a constitution-level call. Recommendation: surface this explicitly to the user before any phenome/intel implementation work — building the placeholders out into full implementations might be solving the wrong problem if the ritual itself is the wrong primitive.

### 4. Demote the corpus-attest-remind hook (low ROI, low cost)

If item 1 ships, the hook is redundant — it's a reminder for a path no one uses and which is now enforced architecturally. Remove from `~/.claude/settings.json:360`. If item 1 doesn't ship, the hook still fires ~0 times/session because no one uses the MCP path; it's dead code in the settings file. Either way it should go.

## Provenance

- agentlogs DB: `/Users/alien/.claude/agentlogs.db` (indexed 2025-08-06 → 2026-05-23; indexer stale since 2026-05-24, .indexlock).
- Corpus DB: `/Users/alien/Projects/corpus/graph.duckdb`, 396 annotations, distribution covered in user-supplied background.
- Hook trigger log: `/Users/alien/.claude/event-log.jsonl` (symlinked to `hook-triggers.jsonl`).
- Audit log: `/Users/alien/.claude/logs/corpus/audit-corpus-sync.out` (last run 2026-05-26 05:10).
- MCP source verified per-repo at file:line cited above; settings matcher at `~/.claude/settings.json:359-367`.

<!-- knowledge-index
generated: 2026-05-26T19:55:52Z
hash: f3c5f682e9c2

index:title: Cross-Attestation Substrate — Usage Forensics
index:status: active
index:tags: substrate, attestation, corpus, post-mortem
cross_refs: decisions/2026-05-11-cross-attestation-substrate.md

end-knowledge-index -->
