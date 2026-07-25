# Drop the `agent-infra` MCP registration from 11 repos (2026-07-25)

**Status:** ESCALATED — blocker resolved, permission boundary remains

## The ask

Remove the `agent-infra` MCP server entry from the 11 `.mcp.json` files that register it
(genomics, intel, personal, arc-agi, evals, anki, people, anim-workbench,
immigration-research, +2). **Keep `agent_infra_mcp.py` itself** — registration and CLI are
separable; anyone wanting the scoped search can still call it from Bash.

Yes/no. Reversible (`git revert`).

## Why it needs you

Shared surface across 3+ projects → constitution hard limit #4. Not agent-decidable.

## Why it is ripe now

| Signal | Value |
|---|---|
| MCP protocol calls, all projects, 2026-06-23..07-24 | **0** across 4,561 runs |
| Bash CLI invocations | 2 |
| Live functional referrers in agent-infra | **none** — only its own smoke test + orphan checker |

This is the profile that retired the **repo-tools MCP** on 2026-03-20 (0 calls / 4,287 runs).

The 2026-07-24 audit found this and correctly refused to act, because a 2026-06-14 correction
had recorded the MCP as live ("consumed by `just orient`"). **That correction is now
disproven:** `just orient` runs `scripts/orient.py` only, which has zero references, and
`git log -S"agent_infra_mcp" -- scripts/orient.py` returns **no commits in the repo's entire
history** — the claimed consumer never existed. Full reasoning:
`decisions/2026-07-25-agent-infra-mcp-zero-consumption.md`.

## What you're buying

Every registered repo pays tool-list context rent in every session and every subagent spawn
for a surface nothing calls. Same class as the skills-farm cut that took the global
description budget 9,902 → 7,390 chars this week.

## The one argument against

Zero-usage measurement is the *wrong instrument* for deliberate-invoke tools — that is the
lesson from the genomics skill cut-and-reverse (`.claude/rules/vetoed-decisions.md`). The
counter here is that this is not a usage-only case: there is **no functional referrer in the
code at all**, which is a mechanism check, not a usage count. If you believe the scoped
cross-project search is a capability worth keeping reachable, the answer is to keep the script
(this proposal does) and drop only the always-loaded registration.
