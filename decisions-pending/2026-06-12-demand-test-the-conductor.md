# Pre-registered: does the loop conductor actually get RUN? (demand test)

**Boundary:** shared (decides whether to keep investing in the conductor or demote it to launchd)
**Recommendation:** Run the 14-day demand test below BEFORE building anything more on `/improve maintain`. If it fails, demote the deterministic SWEEP to a launchd job and stop maintaining the conductor skill.

## Why this exists

The Fable-5 review (2026-06-12) landed the sharpest critique of this whole work
stream: **we fixed supply, but the constraint is demand.** Three loop-conductor
skills had 0 invocations in 90 days — not because there were three, but because
the execution model needs a human to open a window and type `/loop 30m /improve
maintain`, and 90 days of data says that doesn't happen. Merging three 0-use
skills into one well-documented skill may just produce a bigger 0-use skill.

This is the real risk to the entire session's work. Pre-register the test so we
judge it on data, not on how elegant the consolidation feels.

## The test (pre-registered — fill in at the deadline)

- **Window:** 2026-06-12 → 2026-06-26 (14 days)
- **Metric:** count of `/improve maintain` invocations across all projects
  (`uv run agentlogs search "improve maintain"` / skill-routing over the window).
- **Decision rule (locked NOW, before seeing the result):**
  - **≥ 5 ticks that did real work** (not just noop) → the conductor earns its keep; proceed to refine the judgment lane.
  - **< 5, OR all ticks were noop** → the conductor is dead infra. Execute the demotion:
    1. Move the deterministic SWEEP (hooks-smoke + doctor + launchd glance) to a launchd job that writes red findings to an inbox file (native-patterns: scheduled execution = launchd, not a watched window).
    2. Push the inbox + decisions-pending count into **SessionStart** so it surfaces in sessions that *already happen*, with zero dependence on the human typing `/loop`.
    3. Keep only the judgment lane as an on-demand skill; stop maintaining the cadence machinery.

## Open question for you

Do you accept this decision rule as binding? The trap it guards against is the one
this system documents repeatedly: building elegant infrastructure nobody invokes
(generation-without-consumption). The honest move is to let usage data, not taste,
decide whether the conductor lives.

**Reversible?** Fully — it's a measurement + a conditional refactor.
**Evidence:** fresh-eyes Fable-5 review 2026-06-12; skill-routing.py --days 90 (3 conductors, 0 uses); native-patterns.md (scheduled execution → launchd).
