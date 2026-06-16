---
title: "Trending Scout — 2026-06-13 (2-day freshness diff)"
date: 2026-06-13
tags: [trending-scout, vendor-updates, claude-code, hooks, subagents]
status: complete
window: 2026-06-11 → 2026-06-13
prior: research/trending-scout-2026-06-11.md
---

# Trending Scout — 2026-06-13

**Window:** 2026-06-11 → 2026-06-13 (2 days — first run of the new 2-day freshness cadence)
**Sources:** Claude Code changelog (WebFetch), Brave (date-filtered). **Exa 402 — out of credits**, OpenAI/Google/arxiv axes not covered this run (see search log).
**Findings:** 3 infra-relevant (hook path-`if:`, nested subagents, Self-Harness paper), 1 dated flag (Gemini CLI EOL Jun-18), 5 version bumps, ~4 already-known/vetoed (filtered)

---

## Headline

A 2-day diff, so the residue is small by design. But it caught **two CC changelog items the 2026-06-11 memo missed** because that memo's source was "documented to .170" while the version had already moved to .172 — the gap is exactly the kind of thing a tighter cadence closes. Both are hook/subagent features that touch how this repo builds.

The deterministic half of the same surveillance loop (vendor-sweep launchd) already paid off today independently: caught CC **2.1.175 → 2.1.177** via the binary skill extractor.

---

## New Findings (ranked by value − maintenance)

### 1. Hook `if:` conditions now match Read/Edit/Write tool PATHS (2.1.176)

| Field | Content |
|-------|---------|
| Source | code.claude.com/docs/en/changelog (2.1.176, June 12) — "Fixed hook `if` conditions for Read/Edit/Write tool paths (e.g., `Edit(src/**)`, `Read(~/.ssh/**)`)" |
| What it does | `if:` hook conditions previously matched Bash command strings (since ~2.1.85/.141). Now they also match **file-path globs** on Read/Edit/Write tool calls. |
| Why relevant | We have several PreToolUse `Write\|Edit` hooks that filter target paths *inside the script* (e.g. data-protection, append-only, unsourced-claim on `research/**`). That path-gating can move into the declarative `if:` condition — fewer hook invocations, less bash, the gate is visible in settings.json not buried in a script. |
| Integration path | **Evaluate** — audit our `Write\|Edit` PreToolUse hooks; for any that early-exit on a path pattern, hoist the pattern into `if: "Edit(<glob>)"`. Single-variable commits, measure trigger-rate before/after. |
| Current overlap | We already use `if:` for `Bash(git commit*)` narrowing (claude-code-native-features-deferred.md, done 2026-03-29). This extends the same mechanism to file paths. |
| Maintenance | Lower than status quo (deletes in-script path checks). |
| Verdict | **Evaluate → adopt where it deletes script-side path filtering** |

### 2. Sub-agents can spawn their own sub-agents, up to 5 levels deep (2.1.172)

| Field | Content |
|-------|---------|
| Source | code.claude.com/docs/en/changelog (2.1.172, June 10) — "Sub-agents can now spawn their own sub-agents (up to 5 levels deep)" |
| What it does | Removes the prior 1-level subagent nesting limit; a dispatched subagent can now itself dispatch. |
| Why relevant | Our orchestration (improve maintain, researcher epochs, workflow fan-out) was built around single-level nesting + the parent-controlled-epoch pattern partly *because* subagents couldn't recurse. Worth checking whether any epoch/coordinator workaround is now unnecessary. |
| Integration path | **Watch / probe** — do NOT rush to deep nesting (context cost + the worktree-isolation + zero-output gates compound per level). Note it; revisit if a real 2-level need appears. The CORAL parent-controlled-epoch rule still stands (it's about *review checkpoints*, not a nesting limitation). |
| Current overlap | researcher-epochs + workflow() one-level-nesting cap in the Workflow tool. |
| Maintenance | High if adopted naively (compounding gates). |
| Verdict | **Watch** — capability noted, no action; flag if a concrete 2-level case arises |

## Version Bumps

| Tool | Prev (per .144/Jun-11 memo) | Current | Notable |
|------|------|---------|---------|
| Claude Code | 2.1.172 (doc'd .170) | **2.1.177** | .173 Fable-5 `[1m]` suffix auto-normalized; .174 wheel-scroll setting; .175 `enforceAvailableModels`; .176 hook path `if:` (Finding 1), `footerLinksRegexes`, Bedrock cred caching |
| codex-cli | (memo) | **rust-v0.139.0** | not diffed this run (Exa down) |
| uv | — | **0.11.21** | routine |
| anthropic-sdk / openai-sdk / google-genai / mcp / exa-py / modal / fastmcp | — | 0.109.1 / 2.41.1 / 2.8.0 / 1.27.2 / 2.13.2 / 1.5.0 / 3.4.2 | snapshot baseline now in `docs/vendor/` cache |

## Already Known / Filtered

- **Token Savior** (symbol-graph MCP, "77% token cut") — surfaced via awesome-harness-engineering. **Vetoed class**: PageRank symbol graph for code nav (vetoed-decisions.md 2026-03-19, repos 20-50 files). No action.
- **`enforceAvailableModels` / `requiredMinimum/MaximumVersion`** managed settings — enterprise model/version governance; low value for a solo operator. Noted, no action.
- **microsoft/skills**, **awesome-harness-engineering** (GitHub) — external confirmation of the harness-as-first-class bet; the harness-eng list is a decent periodic reference but nothing adopt-grade. Watch.

## Deferred Axes — covered after Exa recovered (same session)

Exa came back mid-session; the OpenAI/Codex, Google/Gemini, GitHub-trending, and research axes were then run.

### 3. Self-Harness: harnesses that improve themselves (arXiv 2606.09498, Shanghai AI Lab)

| Field | Content |
|-------|---------|
| Source | arxiv.org/abs/2606.09498 (2026-06-08) |
| What it does | An LLM agent improves its OWN operating harness via an iterative loop: **Weakness Mining** (model-specific failure patterns from execution traces) → **Harness Proposal** (diverse minimal harness edits tied to failures) → **Proposal Validation** (accept only after regression testing). Terminal-Bench-2.0, 3 base models (MiniMax M2.5, Qwen3.5-35B-A3B, GLM-5); held-out pass rates 40.5→61.9%, 23.8→38.1%, 42.9→57.1%. |
| Why relevant | This is **almost exactly this repo's `reflect.py` deep-pass thesis** (mine failures → propose enforcer/mint → validate before promote) and the gov-shrink loop. External, quantified validation of the core bet — and a concrete 3-stage decomposition + the "minimal edits + regression-gate before accept" discipline worth comparing against ours. |
| Integration path | **Read + compare** — map their Weakness-Mining/Proposal/Validation stages onto our reflect→improvement-log→verifier flow; their regression-gate-before-accept is the part we do most loosely (we promote to `[ ]` for human disposition, they auto-validate). Candidate for a decisions/ memo. |
| Current overlap | reflect.py (deep pass), gov.py (gov-shrink), the FM taxonomy + verifier-sketch convention. |
| Maintenance | Reading only; no infra adopted yet. |
| Verdict | **Read closely — highest-signal item this run; possible decisions/ memo** |

### Flag: Gemini CLI fully shuts down **2026-06-18** (5 days out)

The free Gemini CLI retired 2026-05-31 (already in `llmx info` / routing mirror); now the **AI Pro/Ultra/free tiers stop processing on June 18** too — migrate to Antigravity `agy`. **Audited this session** (`rg gemini` over scripts/ops/launchd): we route Gemini via llmx paid API, so the live paths are clean. Two residues, neither newly-broken by June 18: `scripts/code-review-scout.py` has a `gemini-cli` provider option (already dead since the May-31 free-tier retirement; script is not launchd-scheduled), and `friend-sync.sh` npm-updates `@google/gemini-cli` (harmless). **Action:** fold the code-review-scout gemini path into the agent-infra-sweep dead-path cleanup, not an urgent fix.

### Ecosystem (watch, no action)

- **ECC 2.0.0** (github affaan-m/ECC) — "agent harness operating system," 261 skills / 64 agents / 84 commands, cross-harness (Claude Code/Codex/OpenCode/Cursor), control-pane TUI. The maximalist version of what this repo does. Star count claim (214K) is implausible — discount. **Watch**: it's a competing whole-harness; our bet is curated+measured, not 261-skill breadth. Possibly mine its MCP-inventory/drift-detection idea later.
- **codex** rust-v0.140.0-alpha (from .139) — alpha prereleases only this window, no notable feature text. Version bump.
- **openai-agents-python 0.17.5**, **vercel/ai @ai-sdk/mcp 2.0.0-canary**, **IBM mcp-context-forge 1.0.3** (enterprise MCP gateway, FedRAMP/FIPS) — routine / not our use case.

## Search Log

- **WebFetch** code.claude.com changelog → full, high-signal (primary source for findings 1-2 + version deltas).
- **Brave** date-filtered 2026-06-10..13 → worked; mostly listicles, one useful repo (awesome-harness-engineering).
- **Exa** `web_search_advanced_exa` → 402 on first batch (credits), **recovered mid-session**. Re-ran OpenAI/Codex, Gemini, GitHub-trending, research-paper axes. Lesson logged: narrow/domain-filtered Exa queries + `contextMaxCharacters` avoid the 80–320KB temp-file dumps two broad queries produced.
- **All axes now covered** for the 2026-06-11→13 window.
