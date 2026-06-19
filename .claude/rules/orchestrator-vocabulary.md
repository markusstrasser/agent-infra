# Orchestrator vs operator (load-bearing vocabulary)

Do not conflate these roles in docs, handoffs, skills, or commit messages.

| Role | Who | Does |
|------|-----|------|
| **Operator** | Human (Markus; `HUMAN.md`) | Goals, taste, approve/reject irreversible work, say yes/no |
| **Orchestrator** | Frontier model parent session (e.g. Claude Opus) | Read handoffs, dispatch scouts/subagents, triage, propose fixes/commits |
| **Scout / worker** | Cheaper isolated model (e.g. Composer ask-mode) | Write audit files only — no commit, no apply |

**File-bus tools** (see `.claude/rules/orchestrator-tool-names.md`) serve the **orchestrator model**. The **operator** uses **operator-status-briefing** and steers at boundaries (tier-1/2, taste, ship/no-ship).

Wrong: "orchestrator reads handoff" when you mean the human.  
Right: "orchestrator model reads handoff; operator approves apply."
