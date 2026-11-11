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

Dated evidence and related rules: `docs/probe-primitive-first-evidence.md`.
