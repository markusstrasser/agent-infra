---
id: 2026-07-25-agent-infra-mcp-zero-consumption
concept: mcp-surface-retirement
repo: agent-infra
decision_date: 2026-07-25
recorded_date: 2026-07-25
provenance: contemporaneous
status: accepted
initial_leaning: deregister it — same shape as the already-vetoed repo-tools MCP
relations:
  - type: refutes
    target: 2026-06-14-search-retrieval-correction
  - type: relates_to
    target: 2026-03-20-retire-repo-tools-mcp
---

# 2026-07-25: The `agent-infra` MCP has no consumer — and the correction that said it did was wrong

## Decision

**Resolved (agent-decidable):** the 2026-06-14 correction claiming the agent-infra MCP is
"consumed by `just orient`" is **factually false**, and no longer blocks a retirement call.

**Escalated (operator-gated):** dropping the registration from 11 `.mcp.json` files is a
shared-infrastructure change across 3+ repos → hard limit #4. Recommended, not executed.

## Context

The 2026-07-24 harness audit found the MCP registered in 9 repos (now 11) with **0 protocol
calls across 4,561 runs** (2026-06-23..2026-07-24) and 2 Bash CLI invocations. That is the exact
profile that retired the **repo-tools MCP** on 2026-03-20 (0 usage / 4,287 runs).

The audit correctly refused to act, because `search-retrieval-architecture.md` §Revisions
records that on 2026-06-14 an agent claimed this MCP was dead and **was corrected** — "it is
live … consumed by `just orient`." A prior correction should not be silently re-overturned by a
later agent re-running the same measurement.

## The deciding probe

Three mechanism-level checks, not usage counts:

```
justfile:10-11        orient *args: → uv run python3 scripts/orient.py {{args}}   (only consumer)
rg agent_infra_mcp scripts/orient.py                       → 0 matches
git log -S"agent_infra_mcp" -- scripts/orient.py           → 0 commits, entire history
```

The third is the one that settles it. `-S` searches every commit that changed the string's
occurrence count in that file; an empty result means the string was **never present at any
point**. So this is *not* "consumption existed and was removed since" — the claimed consumer
never existed. The 06-14 correction asserted a call path that was never in the code.

Remaining referrers are all non-functional: `architecture.mmd` / `architecture.template.mmd`
(diagram), `scripts/_inventory.md`, `CLAUDE.md`, `improvement-log.md` (prose), `pyproject.toml`
(packaging), and two of its own test harnesses — `mcp_contract_smoke.py` and `orphan_check.py`.
A tool whose only live callers are its own smoke test and its own orphan checker.

## Alternatives considered

1. **Drop the 11 registrations, keep the script** — registration and CLI are separable; costs
   nothing if anyone still wants `agent_infra_mcp.py` from Bash. **Recommended.**
2. **Delete script + registrations** — hard limit #5 (architectural component). Not proposed.
3. **Keep and find it a consumer** — would need a named consumer today, not a hypothetical.
   Four months and 4,561 runs is a long enough window.
4. **Do nothing** — the status quo is 11 repos paying tool-list context rent per session for a
   surface nothing calls.

## Why this is recorded rather than done

Per constitution hard limit #4, deploying/removing shared surfaces affecting 3+ projects needs
human sign-off. The audit's blocker was epistemic (an unresolved contradiction); that is now
resolved. What remains is purely a permission boundary.

## The transferable lesson

A **correction** is not automatically better-grounded than what it corrected. This one was
asserted, never probed — and its unearned authority then blocked a correct retirement for six
weeks, exactly because the system is (rightly) built to respect priors. Corrections to
checkable claims owe the same inline probe as the original claim
(`.claude/rules/checkable-claims-carry-probes.md`). The `git log -S` history check is the cheap
instrument that distinguishes "was removed" from "never existed" — reach for it before
accepting either story.
