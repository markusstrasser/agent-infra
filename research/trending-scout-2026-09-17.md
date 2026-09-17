---
title: Trending Scout — 2026-09-17 (Delta by Zed + 7-week vendor sweep)
date: 2026-09-17
tags: [trending-scout, vendor, freshness, delta, agent-workspaces]
status: complete
window: 2026-08-01 → 2026-09-17
---

# Trending Scout — 2026-09-17

**Window:** 2026-08-01 → 2026-09-17 (~7 weeks; prior: `trending-scout-2026-08-01.md`)
**Trigger:** operator pointed at `delta.dev/docs/getting-started` ("top downloads rn") and asked for a vendor refresh.
**Sources:** delta.dev docs (26 pages via sitemap) + zed.dev blog + roadmap/pricing; Claude Code raw CHANGELOG (2.1.221→274, 44 releases); Agent SDK / MCP SDK / openai-python release APIs; openai/codex releases 0.144→0.154; developers.openai.com changelog + pricing (`.md` suffix gives clean markdown); cursor.com/changelog; gemini-cli releases; modal docs releases; GitHub REST for repo stats; `vendor-versions.py`.
**Method:** 4 researcher subagents (Anthropic, other vendors, ecosystem incl. Delta deep-read, papers), parent verified the decision-bearing claims by direct fetch/grep (marked ✓ below).
**Findings:** 1 product verdict (Delta = WATCH), 2 latent breaks, ~10 adopt-now harness primitives, 1 stale price, 1 dead hook.

Provenance: [DATA] live fetches 2026-09-17 · [INFERENCE] verdicts and fit reasoning · [UNVERIFIED] listed at the end.

---

## 1. Delta (Zed Industries) — WATCH, not adopt

Public beta 2026-09-16 (`zed.dev/blog/delta-public-beta`), announced 2026-08-12. Positioning: "a multiplayer environment for coding with agents"; thesis: threads replace PRs, DeltaDB records every edit between commits. Zed turned PRs off on its own repo ("33 of us have landed 570 changes to main").

| Question | Answer (primary source) |
|---|---|
| Whose agent runs | **Delta's own agent**, with Worker/Scout/Reviewer subagent profiles (docs/agents/subagents). Models: Zed-hosted (paid plan, token-metered), or subscription sign-in for **ChatGPT, GitHub Copilot, Grok only**, or **API keys** for Anthropic/OpenAI/OpenRouter/OpenCode ✓ |
| Claude subscription | **Not accepted.** Anthropic is API-key-only → every Claude turn would bill the metered key, colliding with our subscription-only rule ✓ |
| Claude Code integration | **Not shipped.** Blog claims "connects to third-party agent harnesses, starting with Claude Code"; `delta.dev/roadmap` lists "Claude Code plugin — In Progress". String "Claude Code" appears 0× across all 26 docs pages and release notes 0.1.1–0.16.0. MCP is also roadmap-only |
| Worktrees | **Not git worktrees** ("to avoid limitations around how many threads can work on one branch"). DeltaDB worktree + per-machine checkout under `.delta/` in your clone; requires an `origin` remote; adds a `local` remote pointing back at your clone ✓ |
| Scripting surface | **None.** Only `delta cli thread delete\|purge`, app must be closed. No thread-create, no headless, no API |
| Data plane | Backend "runs entirely on Cloudflare" (R2 + Durable Objects + KV/D1). **Uncommitted work syncs by default**; sharing one thread grants repository-wide worktree history; server-side deletion is an email to privacy@zed.dev; no self-host ✓ |
| Skills | Reads `.agents/skills/<name>/SKILL.md` and `~/.agents/skills` — the same path our `codex_parity_sync.py` already writes, so our skills would load unchanged ✓ |
| Pricing | Beta free. Personal $0 (BYO keys / "external agents"), Pro $10/mo with $5 tokens, Business. Shares the Zed account |

**Fit for us [INFERENCE]:** the product's value is multiplayer pre-commit review; we have no teammates. Three hard blockers stack: no Claude subscription auth, no scripting surface (nothing for `/loop`, `lane`, agentlogs to hold), mandatory cloud sync of uncommitted work. The one transferable idea (conversation + diff as one addressable artifact) we already approximate with `agentlogs.db` + `emb`, and ours is queryable from a shell.

**Steal regardless:** `.agents/prepare` (fast, idempotent per-checkout setup script) + `.agents/linked` (manifest of gitignored paths hard-linked across checkouts, e.g. `.env`). Cleaner than re-copying local config into every lane; ~20 lines in `lane`.

**Re-evaluate trigger:** "Claude Code plugin" AND "Remote runtime" both shipped AND a scriptable thread-creation surface exists. A shipped plugin alone is a viewer.

**Nearest competitors:** Conductor (v0.86, 2026-09-16) already runs first-party Claude Code/Codex/Cursor/OpenCode under your own subscription, has a public API, Firecracker sandboxes, iOS — ahead of Delta on our axis; the only candidate if remote/mobile visibility of a running lane is ever wanted. Cursor Projects (2026-09-10) attacks the layer above (coordinator that only delegates, project-scoped context files synced across machines, Slack/schedule/PR subscriptions) — Cursor-locked, cloud-first. `yc-software/qm` (15K★, MIT) is the OSS multiplayer harness, for companies not repos.

Pointer disposition recorded: `tried` (scripts/pointer_disposition.py, 2026-09-17).

## 2. Latent breaks (nothing broken today, both fire on the next resolve)

| Item | Evidence | Action |
|---|---|---|
| **openai-python 3.0.0 (2026-08-12): HTTPX2 default, `httpx` no longer installed** | `agent-infra/pyproject.toml:15` `openai>=2.26.0`, `llmx/pyproject.toml:9` `openai>=1.50.0` — no upper bound; installed 2.31.0 / 2.26.0 ✓ | Pin `openai<3` in both, then migrate deliberately (migration guide `openai-python/httpx2.md`) |
| **Modal 1.6.0 will flip Sandbox V2 default and remove deprecated object-type APIs** | modal.com/docs/sdk/py/releases 1.5.4/1.5.5; we are on 1.5.5, so warnings are visible now | Capture deprecation warnings from one Marker run before 1.6 |
| MCP python SDK 2.x (2026-07-28 stateless spec; `FastMCP`→`MCPServer`, handler exceptions swallowed unless `ToolError`) | Already known (2026-06-07 biomcp memo §3, HAD-PARTS). We import jlowin `fastmcp>=3.4.2,<4.0` (3.4.2 installed; **fastmcp 4.0.4 shipped**), `mcp 1.27.0` transitive; all servers stdio ✓ | Not urgent; upgrade fastmcp→4 as its own commit when convenient; imagegen pins `mcp>=1.0` directly and would float |
| Codex 0.154 removed `codex mcp-server` entry point; 0.152 disabled the planning tool by default | No executable caller found (`codex_mcp_smoke.py` uses `codex mcp list`) ✓ | None; decide `tools.update_plan.enabled` explicitly |

## 3. Claude Code 2.1.220 → 2.1.274 — adopt-now list

Full 44-release classification in the Anthropic scout file (scratchpad; key rows reproduced). Hook events wired today: PreToolUse 71, PostToolUse 70, Stop 19, SessionStart 18, UserPromptSubmit 11; **unwired and now documented:** `PostToolBatch`, `InstructionsLoaded`, `WorktreeCreate/Remove`, `PreModelSwitch/PostModelSwitch`, `PermissionDenied`, `ConfigChange`, `FileChanged`, `TeammateIdle`, `Setup`, `Elicitation*`.

| Item | Version | Why | Action |
|---|---|---|---|
| `updatedToolOutput` documented for **built-in** tools (PostToolUse/PostToolUseFailure) | docs live | Deferred item #2's exact trigger (tool-output compression). We already emit `updatedMCPToolOutput` in `posttool_research_reformat.py` | Bash/Read output-trimming hook; **trigger MET** in `claude-code-native-features-deferred.md` |
| `omitClaudeMd` agent frontmatter / `--agents` JSON | 2.1.271 | Every subagent spawn pays ~34K tokens of always-loaded instructions; the Fable 5.1 memo named instruction mass as the lever | Set on researcher / read-only analysis agents; measure |
| `--permission-prompts none` | 2.1.259 | Unattended `/loop` and headless lanes: prompts auto-deny while the mode still decides. Also supersedes deferred item #3 (scoped write-access MCP) together with `--restricted` (2.1.248) | Add to autonomous dispatch |
| `PostToolBatch` event | docs live | Turn-scoped checks (context-budget, provenance) fire N× per turn today | Move them to batch level |
| `InstructionsLoaded` event (`file_path`, `load_reason`) | docs live | Measures always-loaded mass instead of `wc -c` | Log it; real context-budget baseline |
| `WorktreeCreate` (non-zero exit aborts creation) | docs live | Native pre-flight for `lane run`; `WorktreeRemove` for reaping receipts | Wire as lane guard |
| Cross-session `SendMessage`/`ListAgents` + `notify_when_idle` | 2.1.224 / .236 | Native no-poll idle signal; zero references in our harness | Fold into `wakeup-cadence.md`; replace poll loops |
| `bashEditDiffEnabled` | 2.1.269 | Bash result carries a diff of files the command changed — ground truth for "did it change what it claimed" | Enable, watch context cost |
| `CLAUDE_CODE_MCP_STARTUP_WAIT_MS` | 2.1.274 | Bounds first-turn MCP stalls in `-p` dispatch | Set on headless dispatch |
| `PreModelSwitch` deny hook | 2.1.251 | Makes model-guide routing enforceable; catches silent downgrades mid-loop | Prototype for autonomous runs |
| Agent SDK py: `ResultError` typed payload, `forward_subagent_text`, MCP 2.x in-process | 0.2.140 | Death-class parser in wakeup-cadence string-matches `failureReason`; typed branching replaces it | Upgrade 0.1.55→0.2.154 (crosses 0.2.129 skill-name break — no `skills=[...]` callers ✓) |
| API: on-demand compaction beta `compact-2026-09-04` (signed reusable `compaction` block) | 2026-09-14 | The primitive the checkpoint ritual and Pi-harness study wanted | Evaluate |

**Silent-breakage greps (parent-verified ✓):** no `defaultMode: bypassPermissions` in project settings; no `CLAUDE_CODE_DISABLE_1M_CONTEXT`; no project `env` setting `CLAUDE_CONFIG_DIR`/`TMPDIR`; `CLAUDE_CODE_SUBAGENT_MODEL` only in old arc-agi observe artifacts (semantics inverted in 2.1.251 — override→default; nothing live sets it). **Dead hook:** `TaskCreated` → `task-created-log.sh` last fired 2026-08-19; task/todo tools are off by default on current models since ~2.1.245. Retire or set `CLAUDE_CODE_ENABLE_TODO_TOOLS=1`.

**Vetoed instrument warning:** `/skill-doctor` (2.1.261) "unused" column is usage-count skill-cutting, barred by `vetoed-decisions.md`; use only its context-cost column.

## 4. Other vendors

| Vendor | Delta | Action |
|---|---|---|
| **OpenAI pricing** | GPT-6 Astra GA 2026-09-03 at $10/$50, 1.05M ctx — matches model-guide exactly. **GPT-5.6 Sol cut to $4/$20** (from $5/$30), promotional "at least through 2026-11-21" ✓ (pricing.md line 27/64). llmx `usage_report.PRICING` still says (5.0, 30.0) | Sync llmx PRICING; note the Nov 21 expiry as external state |
| OpenAI API | Agents API public beta (hosted Codex harness, 2026-09-10); Prompt Cache Diagnostics GA (per-request cache read/write breakdown — serves `eval-token-costs.md`); Assistants API shut down | Track; evaluate cache diagnostics |
| **Codex CLI 0.144→0.154** | experimental `--worktree`/`/worktree` (native version of our lane primitive); async hooks + MCP-tool hooks (re-run `codex_hook_shim` canary); `Interrupt` hook; `codex queue` (message into a running session); `--approve-for-me` Guardian LLM-judge approvals (pattern only — a model judge does not make taste verifiable); per-tool MCP `output_token_limit`; `--full-auto` removed (no callers ✓); MCP SDK 3.0 with opt-in 2026-07-28 | Evaluate worktree + queue; adopt `output_token_limit` |
| Gemini CLI 0.54→0.60 | Security hardening only (SSRF/OAuth/Seatbelt), no agent-surface feature; many `[SSR Agent]` bot-authored fixes | Defer local 0.49 bump; critique-only policy unchanged |
| Cursor | Projects (2026-09-10), Origin hosted repos (08-17), `/goal` + custom modes (skill pinned as always-on mode), cloud agents on Modal/E2B/self-hosted pools (09-02). No Grok/Composer pool change found; `cursor-agent 2026.09.02` | Design reference only; custom modes worth a look |
| Kimi | PyPI 1.50 is the same 1.x line (1.31 in April); local 0.29 is an older artifact. 1.47 added `/upgrade` to a standalone "Kimi Code" successor | Do not invest further in kimi-cli integration |
| Modal 1.5.5 | Logs APIs (`fetch/tail/stream` on App/Function/Sandbox — observable jobs), `Workspace.billing.summary()` (queryable cost oracle for the $25/day cap), Sandbox V2 opt-in | Adopt logs API where we poll; evaluate billing |

## 5. Ecosystem / "knowledge products"

| Name | Stars | What | Verdict |
|---|---|---|---|
| **vshulcz/deja-vu** | 822 (Go, MIT) | Indexes session JSONL already on disk for 20+ harnesses; recall via CC hooks at session-start / pre-edit / **post-failure**; claims 85.3% hit@1 LongMemEval-S, harness in-repo | **Extract**: run its harness against `evals/longmemeval_retrieval` (ours R@5 0.969) on the same split; steal the post-failure trigger. Don't adopt the binary (MemPalace parallel-store reasoning) |
| tigerless-labs/agent-memory | 919 | Markdown source of truth + deletable SQLite index, path-returning recall, sleep-time consolidation | Watch — converges on our design; consolidation collides with autoDream/append-only veto |
| okf-agent-memory + Google **Open Knowledge Format v0.2** | 686 / 9.2K (knowledge-catalog) | Vendor-neutral spec for agent memory files (Markdown + YAML frontmatter, validator) | Watch — read SPEC.md once; check if our memory frontmatter is OKF-shaped for free; don't migrate on v0.2 |
| redhat-et/ripwire | 2.2K (C++23) | Deterministic call graph / blast radius / tests-to-run CLI + MCP | Watch — only on a concrete "which tests" miss; codebase-memory-mcp burden of proof applies |
| Agent Memory Leaderboard | 1.2K | Open protocol + leaderboard for long-term memory systems, 20+ orgs | Watch — check if it subsumes our LongMemEval harness before extending ours |
| tigerless-labs/autoharness | 4.3K | Auto-distill skills from sessions, prune unused | **Ignore (vetoed)** — autobrowse graduation veto + usage-count cutting veto; no new evidence |
| yc-software/qm | 15K | OSS multiplayer agent harness for Slack/work | Ignore — no consumer; recorded so it is not re-scouted |

No new commercial knowledge/notebook-with-agents product surfaced in the window; Exa's Aug–Sep agent-memory sweep beyond the above was 0–9★ repos.

## 6. Papers (arXiv 2026-08-01 → 09-17; 759 unique hits from 25 windowed queries, 8 PDFs title-verified)

| Paper | ID | Finding | Verdict |
|---|---|---|---|
| **Subagents vs Agent Skills** (MSR Cambridge + Cornell) | 2609.09233 | 64 SkillsBench tasks, 7 models: subagent execution beats in-context SKILL.md loading **only for skills with explicit input/output contracts**; with the curated non-contract skills the ordering reverses on all 7 models. Subagents hold lower peak context on 28–95% of tasks. Caveat: the two skill sets differ in content, so only the within-set execution-mode comparison is controlled | **Integrate** — a skill worth dispatching to a subagent must declare inputs and a return contract; loose guidance stays in-context |
| **Loop-Back Authority in LLM Agent Teams** (Leiden) | 2609.14767 | Paired n=43 / 86 runs, one link varied (manager may reject and force revision). Flat beats hierarchical on Utility d=0.42 p=0.009; hierarchical hedges 53% more and costs **51.5% more tokens**; the hierarchical writer's first draft equals flat output, damage happens in the revision loop. ~61% power; one open-ended synthesis task, not code | **Integrate** — a supervisor pays for itself when it can verify and is a liability when it can only opine (= our verifier-conditioned scope, now with a number) |
| **The Double Measurement Confound** (UAM Madrid) | 2609.09218 | Two frontier models posted identical 97.5 means on ComtradeBench and a rule-based baseline landed near them: the benchmark measured its scaffold. Scaffold ownership was an uncontrolled axis in every benchmark probed (4-scaffold × model interaction on tau-bench) | **Integrate (method)** in evals: de-scaffold, seeded ground truth, report tail alongside mean |
| **Skill Issue** (JetBrains Research) | 2609.12742 | Real merged-PR tasks, 3 Kotlin repos: GEPA-optimized SKILLs +4.9pp, SkillOpt +0.1pp, **neither significant** at 20–26 held-out tasks. Agent-generated init files (CLAUDE.md-class) −0.5%/−2% resolution at **+20–23% cost**. Prior SKILL-synthesis gains came from a reduced agent on a small model; real Claude Code saturates at 100% with no skill | **Cite (negative)** — supports the SkillOpt veto's "gated on scored evals" condition and the instruction-mass lever |
| Protocol-Preserving Context Trimming (Intuit) | 2609.16461 | Recency/relevance/summarization trimming: ~60% savings at 67–77% success; protocol-aware → 92.2%; adaptive guardrail → 96.0% at 56% savings. Retaining ≤25% of context raises failure odds **10.92×** vs ≥50%. Single author, no code, unstated corpus | Cite — directional numbers for compaction policy; HAD-PARTS vs 06-20 sweep item #6 |
| When Agents Slow Down (Elo-per-token; Berkeley/UW) | 2609.15309 | Agents beat independent-sampling Elo scaling early then fall below it; splitting 100M tokens at the inflection across parallel sessions gained +264 Elo over one long session | Cite — supports splitting long lanes per unit |
| What Eviction Destroys | 2609.08279 | Restore-counterfactual audit on LongMemEval-S: irreversible share of eviction errors 0.67–0.73 at 80k budget, **1.00 for all policies at 8k** | Cite — for compaction floor decisions |
| Scanning the Harness | 2609.07360 | 16.0% of 2,660 agent setups carry a confirmed security defect; 17.5% configure >1 assistant with nothing reconciling their instruction files (we do reconcile via parity sync) | Cite |
| Reviewer Habituation in AI Code Review | 2609.06213 | 11,429 reviews / 400 reviewers: approval rates rise 30.5% → 36.6% early→late under agent-PR volume | Cite — scrutiny decay is measurable |
| Judge papers: Debiasing as Measurement Intervention (2609.12439), Can We Trust LLM Judges (2609.12002) | — | Instructing judges to ignore presentation cues suppresses bias but damages resolution; a judge's own task accuracy predicts its bias in absolute scoring | Cite alongside 06-11 judge-bias memos |
| Persistent Memory Poisoning (2609.13889), CapScope (2609.08371), Agora git-as-shared-memory (2609.18094), RSIAgent (2609.15364), ModularRSI (2609.14857), Bad Genius (2609.18366), SkillSeam (2609.13321), Grounding Agent Memory (2609.11060) | — | Abstract-level only, not body-verified | Watch |
| Reality Is the Final Verifier (2609.12039), Reproducibility = Context Engineering (2609.11728) | — | Positions we already hold (live-execution-is-the-verifier; decision journal) | Ignore |

Hindsight grading (rg over research/, decisions/, .claude/): protocol-aware trimming, de-scaffolding, Elo-per-token, restore-counterfactual, loop-back authority, harness supply-chain — **NOVEL** (zero matches). SkillsBench and GEPA present; the contract condition is new. 2609.16461 is HAD-PARTS.

Tool gotcha from the sweep: Python `urllib` to arxiv.org is blocked in the Bash sandbox while `curl` is not; shell out for arXiv Atom queries.

## 7. Version table

| Tool | 08-01 scout | 09-17 |
|---|---|---|
| Claude Code | 2.1.220 | **2.1.274** |
| Agent SDK py / ts | 0.2.128 / 0.3.220 | **0.2.154 / 0.3.274** (installed py 0.1.55) |
| Anthropic py SDK | 0.120.2 | **1.6.0** (v1.0 2026-08-20; installed 0.107.1) |
| MCP py / ts | 2.0.0 / 1.30.0 | 2.2.0 / 1.30.0 (installed mcp 1.27.0 via fastmcp 3.4.2; fastmcp 4.0.4 available) |
| Codex CLI | 0.146.0 | **0.154.0** (local 0.153.4) |
| OpenAI py SDK | 2.50.0 | **3.14.1** (installed 2.31.0 / 2.26.0) |
| Gemini CLI | 0.53 (local 0.49) | 0.60.0 (local 0.49) |
| Modal | 1.5.3 (local 1.4.2) | 1.5.5 (local 1.5.5) |
| Kimi CLI | 1.49 (local 0.29) | 1.50.0 (local 0.29) |

## Not promoted

- Delta as a product (above). Conductor as a product (no remote-visibility need today).
- `/advisor` headless second-model consult — overlaps `/critique`; never run one diff through both.
- Codex `--approve-for-me` Guardian — LLM-judge approvals on the autonomy boundary.
- `promptCacheTtl` settings — API-key users only; we are subscription.
- `blockReadsOutsideWorkingDirectories` — cross-repo work needs the reads.

## Unverified / gaps

- Delta's Claude Code sync mechanism (plugin vs ACP vs wrapper) — inferred from the roadmap word "plugin".
- DeltaDB open-sourcing intent — secondary reporting only.
- Gemini model/pricing changes and google-genai 2.x breaking changes in window — not fetched.
- Codex `ultra` effort reachability through llmx — not probed.
- deja-vu 85.3% and ripwire 74.7% are self-reported READMEs.
- ampcode.com/news is JS-walled; Amp row rests on framing.
- Issue #32105's own disposition (capability present regardless).

## Search log

Routing gotchas worth keeping: `code.claude.com/docs/en/changelog` only renders 2.1.261+ — use the raw GitHub CHANGELOG for older versions. `developers.openai.com` docs return clean markdown with a `.md` suffix. Modal changelog moved to `/docs/sdk/py/releases`. `api.github.com/repos/openai/codex/releases?per_page=100` hangs; `gh release view rust-vN` works. WebSearch tool was unavailable this run; Exa + direct fetch covered it.
