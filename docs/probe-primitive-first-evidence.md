# Probe the primitive axis first: evidence

Moved verbatim from `.claude/rules/probe-primitive-first.md` on 2026-11-11 so the
always-loaded rule carries only the rule and the three-axes table.

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
