# Stale-question drain — 2026-07-04

_First execution of the drain discipline (plan `.claude/plans/17d2a35c-middle-manager-harvests.md`,
MIDDLE_MANAGER harvest: a stale open item is a defect to drain, not a flag to display).
7 in-session revalidation scouts (fable-low), one per stale item; every load-bearing evidence
claim re-verified at source by the orchestrator before disposition. Future runs:
`just questions-drain --dispatch` (scout_backends lane, reports tokens per eval-token-costs;
this run used in-session subagents — token use not separately metered)._

**Outcome: 7 stale → 1.** 6 archived to `~/.claude/steward-proposals/implemented/` with
dated Resolution blocks (append-only honored — annotated + moved, never deleted).

| Item (age) | Verdict | Disposition | Key evidence (orchestrator-verified) |
|---|---|---|---|
| llmx -f polling loop (104d) | MOOT | archived | llmx@873d313 fixed it 1 day after filing (commit cites the proposal); guard live at `llmx/cli.py:628` |
| Brainstorm dedup pre-check (98d) | MOOT | archived | skills@a6eb857; `brainstorm/SKILL.md:73-75` Pre-Flight = the proposed check |
| --no-verify AGENTS.md mirror (78d) | SUPERSEDED | archived | `pretool-foreign-staged-guard.sh:33` hard-blocks it — landed as architecture, not instructions |
| genomics pre-commit repair (78d) | SUPERSEDED | archived | staged-file scoping + genomics b827f343d/9e911795c/6e663fec7 |
| /observe TECHNICAL FINDINGS mode (78d) | SUPERSEDED | archived | /debug + adversarial-debug-scout / debug-until-dry own the output shape; observe `failures` mode (0f98c1d) |
| Truth-seam lint genomics (78d) | SUPERSEDED | archived | evolved lint suite (lint_no_singletons, lint_runtime_reader_boundary, lint_control_plane_drift); `_STATUS.json` writer killed 2026-05-17 |
| **Hook-state stateless revalidation (78d)** | **STILL-VALID** | **kept — operator call** | forgery substrate unchanged: restart guard still greps agent-writable `/tmp/claude-session-verified-$SID.txt`; post-proposal commits added MORE forgeable markers; Option A unlanded |

## The one residual question for the operator

`~/.claude/steward-proposals/hook-state-stateless-revalidation.md` — genomics' orchestrator
restart guard trusts an agent-writable token file; any agent can forge `ORCH_VALIDATE`/
`CONTROL_PLANE_PROOF` markers with one `echo >>`. Scout confirms the architectural fix
(stateless inline revalidation) never landed and the bypass still works. Given genomics is
winding down to stable CLI use: implement Option A, or accept-and-close on telos grounds?

## Scout verdicts (raw)

Full verdict blocks with per-scout evidence live in the session subagent transcripts
(`~/.claude/projects/-Users-alien-Projects-agent-infra/17d2a35c-*/subagents/agent-areval-*.jsonl`);
the Resolution block appended to each archived proposal carries the surviving evidence.
