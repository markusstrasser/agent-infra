---
concept: agent-infra-mcp-registration
decision_date: 2026-08-01
status: decided
---

# agent-infra MCP deregistration — already complete

**Decision (operator yes 2026-08-01):** drop always-loaded registration; keep CLI/script.

**Probe at apply time:** zero `agent_infra_mcp` entries in any `~/Projects/*/.mcp.json`
and zero in `~/.claude.json` mcpServers. Nothing to edit — already deregistered.

**Pending file closed as satisfied:** `decisions-pending/2026-07-25-agent-infra-mcp-deregistration.md`

**Evidence:** `rg agent_infra_mcp ~/Projects --glob '**/.mcp.json'` → empty (2026-08-01).
