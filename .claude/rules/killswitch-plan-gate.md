# Kill-switch plan vertical slice (agent-infra local)

<!-- Gov-ID: rule:killswitch-plan-gate
goal: authority-deleting / kernel-cutover plans front-load a kill-switch race before multi-phase build
verifier: null
blast_radius: local
-->

When writing or reviewing a plan that **deletes an authority**, does a **dual-write cutover**, or
is a **multi-phase kernel / control-plane refactor**, the plan MUST include a front-loaded section:

```markdown
## Kill-switch vertical slice
- **Race:** <cheapest alternative that could falsify the multi-phase design>
- **Pass:** <pre-registered observable that means "ship the rest">
- **Fail:** <pre-registered observable that means "stop / redesign — do not continue phases">
- **Budget:** <time/$/one real chain>
```

## Triggers (any)

- Deletes or replaces a single source of truth (receipts, journal, control-plane, SSOT module)
- Dual-write → cutover → remove-old-path sequences
- Multi-phase kernel / stage-runner / admission redesign
- "Rewrite the pipeline" / "new authority for X"

## Not triggers

- Single-file bugfix, pure docs, additive hooks with no deletion
- Plans that only *add* a detector without removing an existing principal check

## Enforcement

- **Advisory** this cycle (agent-infra plans under `.claude/plans/` and harvest/observe plans).
- Lint helper: `uv run python3 scripts/lint_plan_killswitch.py <plan.md>` (exit 2 = missing section when triggers fire).
- Shared skills plan-review-gate extension is a **separate** operator-visible proposal — do not silently globalize.

## Evidence

- genomics session `cac39da3` (2026-08): journal race beat a 989-line design; sequencing was the win.
- observe promote `arch_0811_killswitch_plan_gate` (2026-08-11-1258).
