# Architecture — how the whole setup ties together

**Start here** if you want the shape of the system in one screen. This is the visual
front-door; the prose detail lives in the pointers at the bottom. Revise the diagram
when you observe drift — don't let it rot (regen: `just refresh-arch` — see below).

![Architecture flowchart](architecture.png)

<details><summary>Mermaid source (edit this, then re-render)</summary>

```mermaid
flowchart TD
    subgraph SESS["🧠 Agent sessions — multi-vendor"]
        S1["Claude Code · Codex · Cursor · Gemini<br/>interactive + /loop + subagents"]
    end
    subgraph HARNESS["⚙️ Harness — shapes every session"]
        G["Global · ~/.claude/<br/>CLAUDE.md · rules/ · settings.json hooks"]
        SH["Shared · ~/Projects/skills/<br/>~40 skills + hooks/ — symlinked by friend-sync.sh"]
        P["Per-project<br/>CLAUDE.md (=AGENTS.md) · .claude/rules · settings.json · .mcp.json"]
        MCP["MCP servers<br/>research-mcp · agent_infra_mcp · exa/brave/perplexity · scite"]
    end
    subgraph STORE["💾 Durable stores — the memory"]
        GIT["git — the ledger<br/>Session-ID trailers · 'git log is the learning'"]
        DB["agentlogs.db<br/>sessions·runs·events·tool_calls<br/>+ git_commits → v_session_commits"]
        CORP["corpus<br/>bytes + parses + citations + belief-ledger<br/>cross-attestation outbox"]
    end
    subgraph WATCH["🔁 Self-monitoring — launchd · zero-API"]
        L["agentlogs-index (2h) · drift-sentinel · blindspot-miner<br/>vendor-sweep · gov-report · audit-corpus-sync<br/>codebase-map-refresh · test-health · reclaim-rotate"]
        DIG["digests @ SessionStart<br/>PRIORITIES · drift-digest · blindspot-digest"]
    end
    subgraph GOV["🧭 RSI governance loop"]
        OBS["/observe · /improve maintain"]
        LOG["improvement-log.md<br/>2+ recurrences → promote"]
        RULE["new rules · hooks · skills · decisions/"]
        KPI["supervision-kpi<br/>declining-supervision = the objective"]
    end
    subgraph PROJ["📦 Governed projects"]
        PR["intel · phenome · genomics · skills · research-mcp"]
    end
    S1 -->|shaped by| HARNESS
    HARNESS -->|context + tools| S1
    S1 -->|granular commits| GIT
    S1 -->|transcripts| DB
    S1 -->|sources / verdicts| CORP
    GIT -->|git_import| DB
    L --> DB
    L --> DIG
    DIG -->|surfaced| S1
    DB --> OBS
    CORP --> OBS
    DIG --> OBS
    DB --> KPI
    KPI --> OBS
    OBS --> LOG
    LOG --> RULE
    RULE ==>|propagate · the feedback edge| HARNESS
    HARNESS -->|skills + hooks| PR
    PR -->|sessions| S1
```
</details>

## The loop in one sentence
Multi-vendor **sessions** are shaped by a layered **harness** → their work lands in three
**durable stores** (git ledger, `agentlogs.db`, corpus) → **launchd self-monitors** mine those
stores into SessionStart **digests** → the **RSI governance loop** (`/observe`, `/improve`)
promotes recurring findings into rules/hooks/skills → which **propagate back into the harness**
(the heavy `==>` edge). Declining supervision is the objective; the blindspot/drift miners are
how the system notices its own misses.

## Legend (one line each → where the detail lives)
| Block | What it is | Deeper doc |
|---|---|---|
| Harness | The layered instruction/skill/hook/MCP surface loaded per session | `CLAUDE.md` §Cross-Project Architecture · `.claude/rules/context-budget-principles.md` |
| Durable stores | git + `agentlogs.db` + corpus — the system's memory | `.claude/rules/session-forensics.md` · `decisions/2026-05-26-cross-attestation-substrate-v2.md` |
| Self-monitoring | zero-API launchd jobs (sense half of RSI) — live set: `launchctl list \| grep com.agent-infra` | `CLAUDE.md` §Active launchd jobs |
| RSI governance | observe → improvement-log → promote to architecture | `CLAUDE.md` <constitution> · `.claude/rules/gov-id.md` |
| Governed projects | intel/phenome/genomics/skills + their stances | `research/cross-project-architecture-overview.md` (prose, 2026-05-11) |
| Codebase | py files by group + import-hubs (count is GENERATED, never hand-kept) | `.claude/rules/codebase-map.md` |

## Derive live state — never trust a hand-kept count

The blocks above show the **shape**; the exhaustive, current inventory is **derived**. A
hand-maintained list drifts the day you add a job (this doc said "13 jobs / 138 files" one
day after it was written). So: **what's POSSIBLE is a map (slow-changing); what's WIRED is
derived (changes hourly) — never hand-document liveness.**

### → Start with `just orient`
`just orient` (`scripts/orient.py`) IS the unifier: the live map — repos, launchd loops,
hook wiring (by event), MCP servers, skills — assembled from ground truth on every run, so
nothing in it can go stale. It correctly shows jobs added minutes ago (it reads `launchctl`,
not prose). `orient = what is it?` · `doctor = healthy?` · `dashboard = what happened?`

Drill deeper into one question:

| Question | Command |
|---|---|
| Doc-vs-reality drift (live jobs vs this doc / CLAUDE.md) | `uv run python3 scripts/orient.py --drift` |
| Dead scripts (generator, no consumer) | `uv run python3 scripts/orphan_check.py` |
| Scaffold lifecycle (rules/hooks, shrink-eligible vs backlog) | `just gov-report` |
| Cross-project health (hooks · MCP · skills · symlinks) | `uv run python3 scripts/doctor.py` |
| Which hooks actually FIRE (not just registered) | `uv run python3 scripts/hooks_smoke.py` |
| Open human-gated decisions (pending · steward · DUE predictions) | `just questions` |

## Regenerate the image
```bash
mmdc -i architecture.mmd -o architecture.png -t dark -b '#0b0f19' --scale 2 \
  -p /tmp/puppeteer-cfg.json   # cfg: {"executablePath":"<system Chrome>","args":["--no-sandbox"]}
```
