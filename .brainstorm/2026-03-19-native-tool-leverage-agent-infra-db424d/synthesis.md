# Brainstorm: Native Tool Leverage for Agent Infrastructure

**Date:** 2026-03-19
**Perturbation:** Denial ×2, Domain forcing ×3 (Kitchen/ATC/Immune), Constraint inversion ×3
**Human seeds:** No
**Extraction:** 100 items total → 22 explore, 18 parked, 14 rejected, 46 merged/duplicates

## Ideas to Explore (ranked by novelty × feasibility)

| Rank | ID(s) | Idea | Why Non-Obvious | Effort | Source |
|------|-------|------|-----------------|--------|--------|
| 1 | 93,58,62 | **"Native until proven insufficient" design review** — require proof of native-tool insufficiency before any new script/MCP. Formalize as a pre-build gate. | Process change, not code. Addresses root cause (premature infrastructure invention). All three domains converged on this independently. | Low | domain-atc, domain-immune, synthesis |
| 2 | 94,64,61 | **Native Patterns Catalog** — map problem classes (history annotation, mutable state, event trigger, audit, search, orchestration) to default native solutions. Living document agents consult before building. | Immune memory pattern — learn once, apply forever. Prevents rediscovering solutions. | Low | domain-immune, domain-atc, synthesis |
| 3 | 1,2 | **SQLite views + triggers** in orchestrator.db/runlogs.db — v_stalled_tasks, v_daily_cost, auto-compute duration on status change. Agents query SQL directly, not Python wrappers. | Database IS the API. Removes entire script layer. | Low | initial-claude |
| 4 | 76,98 | **`just brief`** — generate session rehydration from live state: branch, dirty files, recent commits, failing hooks, last receipt. Replaces checkpoint.md for common case. | Constraint inversion insight: treat CLAUDE.md/memory as optional. Self-describing workspace should work without it. | Med | constraint-inv2 |
| 5 | 3,28 | **launchd WatchPaths + TimeOut + KeepAlive** — replace Python stall detection with OS-native process supervision. WatchPaths for file-triggered tasks instead of polling. | We built anyio.fail_after(600s) when launchd does this natively. Systemd article confirms most teams stop at "start/enable/status." | Med | initial-claude, initial-gemini |
| 6 | 91,92,71 | **Script/MCP triage audit** — inventory all 40 scripts + 7 MCPs by job-to-be-done, classify as: replace-with-CLI, replace-with-just-target, merge, keep, delete. | Not a new feature — a deletion exercise. Constraint inversion: "fewer repos, fewer scripts, fewer MCPs" was the winning design under ALL three inversions. | Med | synthesis, constraint-inv1 |
| 7 | 7 | **ast module for Python parsing** — replace regex parsers in repo-outline.py, codebase-map.py, repo-imports.py with single ast-based walker. | Already recommended in CLAUDE.md but unused. Three scripts share a common bug class (regex edge cases). | Med | initial-claude |
| 8 | 41 | **APFS copy-on-write clones** (`cp -c`) for agent sandboxing — instantaneous, zero-byte-cost workspace copies. Delete on failure. | Denial round surfaced this. We use git worktrees which suppress transcripts. APFS clones don't have that problem and are faster. | Med | denial-r1 |
| 9 | 81,85 | **Bounded action catalogs** — define finite approved actions per context (inspect, branch, edit, test, commit, merge, rollback). Machine-enforce spend/retry/time budgets. | Constraint inv3: "shrink freedom, increase constraints." Counter-intuitive but correct — bounded agents are more autonomous because they need less supervision. | Med | constraint-inv3 |
| 10 | 16 | **macOS Keychain for API secrets** — `security find-generic-password` replaces scattered .env files. One source of truth, no plaintext on disk, scriptable. | Low-hanging operational hygiene. Currently secrets in shell profiles + .env files = multiple sources of truth. | Low | initial-claude |
| 11 | 13 | **Python logging module with JSONFormatter** — replace manual JSONL file.write() in 5+ scripts with stdlib logging. Auto-rotation, levels, filtering. | We reinvented structured logging badly in every script. | Low | initial-claude |
| 12 | 70,73 | **Logic in data, not code** — SQL files for common queries, jq templates for JSON transforms. Scripts become thin shells around data artifacts. | Inv1 insight: move from "maintain code" to "maintain configuration + composition." | Med | constraint-inv1 |
| 13 | 66 | **Quarantine directory for experimental scripts** — marked sandbox with review expiry dates. Auto-archive after 30 days if not promoted. | Immune system: prevent experiments from ossifying into infrastructure. We have this problem — scripts written "temporarily" that persist. | Low | domain-immune |
| 14 | 22 | **launchd socket activation for MCP servers** — spawn on-demand, terminate when idle. Saves memory when servers aren't needed. | 7 MCP servers always running. Socket activation means they exist only when called. | Med | initial-gemini |
| 15 | 78,99 | **Rules → executable checks** — convert instruction-only rules into tests, linters, hooks. Inv2: "a rule that isn't enforced is basically trivia." | Echoes constitution principle "instructions alone = 0% reliable" but applied more broadly. | High | constraint-inv2 |
| 16 | 15 | **git config as typed KV store** for agent settings — `git config --get agent.cost-cap`, `git config --type=int agent.max-retries`. Per-repo, typed, no custom config file. | Underexplored git feature. Currently we have scattered JSON/YAML config. | Low | initial-claude |
| 17 | 5 | **Spotlight/mdfind for cross-repo search** — `mdfind -onlyin ~/Projects "keyword"` as lightweight alternative to meta-knowledge MCP for simple queries. | OS is already indexing everything. We built an MCP server when mdfind exists. | Low | initial-claude |
| 18 | 35 | **uv inline metadata (PEP 723)** for ephemeral scripts — declare deps in script header, no pyproject.toml needed. | `uv run script.py` auto-resolves inline deps. Eliminates friction for one-off tools. | Low | initial-gemini |
| 19 | 38 | **macOS `defaults` for atomic config** — plist-backed config with atomic writes, caching, and type safety via `defaults read/write`. | We use JSON files written with Python. Plists have atomic updates built in. | Low | initial-gemini |
| 20 | 11 | **git bisect for automated regression finding** — `git bisect run <test>` binary-searches commit history. | Manual regression diagnosis is slow. bisect automates with any test predicate. | Low | initial-claude |
| 21 | 33 | **zsh `chpwd` hook for context loading** — auto-trigger project-specific env/MCP config when cd'ing into a project directory. | Currently agents must manually discover project context. Shell hook does it automatically. | Low | initial-gemini |
| 22 | 14 | **SSH ControlMaster for persistent connections** — eliminate handshake overhead on repeated git push/fetch. | Minor but free optimization for multi-repo push workflows. | Low | initial-claude |

## Parked (interesting, no immediate path)

| ID | Idea | Why Parked |
|----|------|-----------|
| 42 | sandbox-exec kernel containment | Interesting for safety but unclear agent workflow integration, macOS deprecation risk |
| 46 | DYLD_INSERT_LIBRARIES hooking | Game-modding technique — fascinating for invisible compliance forcing but fragile + SIP restrictions |
| 47 | CoreMIDI for event choreography | Creative but wildly overengineered for our scale |
| 48 | taskpolicy core pinning | Apple Silicon optimization — premature, no measured thermal throttling problem |
| 49 | Metal compute shaders for state management | GPU search at hardware speed — cool, no measured bottleneck |
| 43 | Loopback aliasing for MCP routing | Neat network trick but MCP uses stdio transport, not HTTP |
| 20 | tmux session management | Already have launchd; tmux adds observability but also complexity |
| 23 | Custom Spotlight Importers | Engineering cost too high for benefit |
| 30 | JXA for application state queries | Niche, would need specific use case |
| 31 | Hard links as knowledge graph | Filesystem graph model — clever but brittle |
| 32 | Bonjour/mDNS for MCP discovery | Decentralized discovery — relevant if we had many machines |
| 27 | sys.settrace for runtime debugging | Interesting for failure forensics, no immediate need |
| 34 | pf firewall per-agent sandboxing | Network-level isolation — overkill for single operator |
| 36 | logging.Handler → Console.app | Sending to macOS unified log — interesting for observability |
| 40 | chmod 444 for verified outputs | Immutability via permissions — simple but easy to circumvent |
| 24 | zsh coprocesses | Persistent tool sessions — niche IPC pattern |
| 44 | Named pipes for backpressure | POSIX IPC — valid but no measured backpressure problem |
| 45 | RAM disk for ephemeral I/O | SSD wear isn't a measured problem, premature |

## Rejected

| ID | Idea | Why Rejected |
|----|------|-------------|
| 68,100 | Top-level Makefile replacing justfile | We already have justfile with groups — Make is strictly worse ergonomics for our use |
| 10 | git blame as primary provenance | Session-ID trailer already provides commit→session, blame is too granular |
| 18 | git stash for workspace isolation | Stash is fragile for multi-agent — worktrees or APFS clones are safer |
| 12 | uv workspaces for shared deps | Our scripts are independent — workspace coupling adds friction without benefit |
| 8 | In-memory SQLite for analytics | We already use pandas/dicts for small analytics — no clear improvement |
| 17 | functools.lru_cache | Per-process caching — scripts are short-lived, cache never warms |
| 19 | flock everywhere | Orchestrator already uses flock; other scripts write to independent files |
| 9 | just recipe DAG | We already use just for tasks — the DAG use case is the orchestrator |
| 4,21 | xattr for file metadata | Fragile across git (xattr not tracked), not portable, easily lost |
| 6 | zsh precmd for human activity logging | Privacy concern, low signal-to-noise, agents already see git log |
| 29 | SQLite FTS5 for document retrieval | Sessions.py already uses FTS5 — not a new idea |
| 39 | SQLite JSON1 functions | Already used in substrate — not a new idea |
| 25 | just for cognitive task topological sort | Conflates task runner with workflow engine |
| 26 | Named pipes for LLM streaming | LLM APIs use HTTP streaming; FIFOs don't help |

## Process/Methodology Ideas (cross-cutting)

These aren't tool features — they're operational patterns that emerged from domain forcing and constraint inversion.

| ID(s) | Pattern | Source | Action |
|-------|---------|--------|--------|
| 50,55 | Prep vs service separation | Kitchen | Define "infrastructure freeze" during active sessions |
| 56-57 | Standard phraseology + authoritative sources | ATC | "This is history metadata → git" vocabulary table |
| 60 | One source of truth per state type | ATC | Audit for duplicated state across JSONL/SQLite/files |
| 65 | Self/non-self discrimination | Immune | Label scripts: core substrate / local workflow / experiment |
| 67,97 | Anti-autoimmunity review | Immune | Quarterly check: surprising hooks, opaque failures, over-engineering |
| 83 | Ephemeral-first, promote-to-main | Inv3 | Default to sandbox, explicit promotion step |
| 87 | Restrict self-modification of control logic | Inv3 | Already in constitution — validate enforcement |
| 89 | Complexity as autonomy risk surface | Inv3 | Every component is supervision overhead |
| 90 | Inaction as valid outcome | Inv3 | Already in hooks (fail open) — broaden to agent behavior |
| 95 | Glue vs shadow infrastructure test | Synthesis | "Does it store state? Does it define metadata? → shadow infra" |

## Paradigm Gaps

What was NOT covered:
- **Networking beyond localhost** — all ideas assumed single-machine. What about multi-machine agent fleet? (deferred — single operator)
- **Hardware peripherals** — Touch Bar, Force Touch, ambient light sensor as agent feedback channels (silly but unexplored)
- **Time-based native features** — NTP, timezone databases, chrono libraries for temporal reasoning
- **Accessibility APIs** — VoiceOver, Accessibility Inspector as alternative input/output for agents
- **Compiler infrastructure** — LLVM/Clang as code analysis tools (we use regex/ast but not the actual compiler)

## Technique Effectiveness

| Technique | Items generated | EXPLORE items | Hit rate |
|-----------|----------------|---------------|----------|
| Initial (Claude) | 20 | 11 | 55% |
| Initial (Gemini) | 20 | 5 | 25% |
| Denial R1 | 5 | 1 | 20% |
| Denial R2 | 4 | 0 | 0% |
| Domain Forcing | 18 | 4 | 22% |
| Constraint Inversion | 22 | 5 | 23% |
| Cross-cutting synthesis | 11 | 4 | 36% |

Initial generation had highest hit rate — unsurprising since these are "obvious but unused" features. Denial rounds pushed into increasingly exotic territory (CoreMIDI, Metal shaders) that's creative but impractical. Domain forcing and constraint inversion produced the highest-value *process* insights (native-first rule, patterns catalog, script triage).

## Suggested Next Step

**Top 3 to prototype first (cheapest validation):**

1. **Native Patterns Catalog** (Rank 2) — write the catalog as `.claude/rules/native-patterns.md`. Zero code, immediate agent impact. 30 min.
2. **SQLite views** (Rank 3) — add 5 views to orchestrator.db. Test with `sqlite3` queries. 30 min.
3. **Script/MCP triage audit** (Rank 6) — inventory + classify the 40 scripts. Decision document, then execute cuts. 60 min.

Want a plan for any of these, or `/model-review` to stress-test the catalog design?
