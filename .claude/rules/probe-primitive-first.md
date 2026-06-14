---
# Gov-ID: rule:probe-primitive-first
# goal: prevent escalating into run-state forensics / producer re-runs when the underlying artifact is already present
# verifier: null
# blast_radius: local
---

# Probe the Primitive Axis First

<!-- Gov-ID: rule:probe-primitive-first
goal: prevent escalating into producer re-runs when underlying artifacts are already present
verifier: null
blast_radius: local
-->

Before escalating into run-state forensics, producer re-runs, or pipeline
re-dispatches on a "blocked / unavailable / incomplete / running" report:

1. **Is the underlying artifact actually missing?** Per-artifact presence check (resolve + sha), NOT the certificate or bundle verdict.
2. **Is the process actually live?** Live app-list query, NOT the DB status column.

## The three axes (never let a higher gate a lower)

| Axis | Cost | What it tests |
|------|------|---------------|
| **Readable** (per-artifact, local) | Cheap | resolves + parses + sha |
| **Coherent** (cross-artifact, same-run) | Medium | cross-artifact consistency |
| **Policy/complete** (publication seal, bundle cert) | Expensive | aggregate policy verdict |

A higher-axis failure does NOT imply a lower-axis failure. The certificate can fail
while all 302 producer artifacts are present and sha-verifiable. The DB can show
`status: running` while every process is a zombie from a prior budget-kill.

Check the lowest (cheapest) axis first. It falsifies the re-run hypothesis without
spending quota on forensics.

## Evidence

- phenome 2026-06-01: `medical_intelligence` bundle reported `blocked`. Spent a
  long session on Modal run-state forensics. All 302 producer stages were present
  and sha-verifiable the entire time. Blocker: stale publication seal's
  `complete: false` flag.
- genomics zombie runs: DB `status: running` = 4 dead processes from a budget-kill
  at 02:55 UTC. Rule: call `list_apps` FIRST before reporting any stage as "running."

## Related

P8 face (a) "fail loud on a dead data plane" (the SOURCE is dead, not the rollup);
`feedback_aggregate_verdict_not_data_presence` (phenome memory);
`feedback_verify_modal_apps_before_claiming_running` (genomics memory).
