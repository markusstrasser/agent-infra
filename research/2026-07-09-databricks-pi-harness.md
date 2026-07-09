## Databricks coding-agent benchmark + Pi harness — Research Memo

**Question:** Is the 2026-07-08 Databricks blog relevant to us? Can we steal/learn from the Pi harness (inspect code clearly)? What does last-week harness research add?
**Tier:** Standard | **Date:** 2026-07-09
**Ground truth:** We already treat harness as a first-class lever (`decisions/2026-06-07-state-externalization-lens.md`, Harness-1, `research/2026-06-24-rsi-loop-vs-harness-evolution-sweep.md`, OpenClaw/Pi philosophy in `research/openclaw-deep-dive.md`). GLM-5.2 is opt-in critique cosigner, not a daily coding default (`decisions/2026-06-19-glm-5.2-integration.md`). Dispatch economics already warn that cheaper $/token ≠ cheaper $/task.

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | Blog is **highly relevant** — same thesis as our constitution: harness + task-level cost dominate model list price | Databricks conclusions 1–4; Writer harness-swap (−41% $/task, models fixed) | HIGH | [SOURCE: databricks.com/blog/…]; [SOURCE: arxiv.org/html/2607.06906] | VERIFIED |
| 2 | **Pi is open-source MIT** (~69k★) — inspectable; Databricks “~3× less context/turn” is a *workload claim*, not a published Pi API | GitHub `earendil-works/pi`; compaction docs | HIGH | [SOURCE: github.com/earendil-works/pi]; [SOURCE: raw …/compaction.md] | VERIFIED |
| 3 | Steal **mechanisms**, not a Pi migration — our RSI loop is Claude-Code-shaped (hooks/skills/SessionStart) | OpenClaw deep-dive already extracted Pi philosophy; Omnigent is a *meta*-harness we don’t need wholesale | HIGH | [TRAINING-DATA]+local memos | INFERENCE |
| 4 | Price-per-token is a bad proxy; Sonnet can cost *more* per task than Opus | Databricks: Sonnet 5 $2.09/task vs Opus $1.94 despite ~1.7× cheaper $/tok (1.9× more tokens) | HIGH | [SOURCE: Databricks blog] | VERIFIED (their bench) |
| 5 | GLM-5.2 “daily driver” on *their* PR-bench ≠ promote GLM as our coding default | Their tasks/tests/harness; our model-guide keeps GLM as calibration/critique opt-in | MED | [SOURCE: blog] + local routing | INFERENCE |
| 6 | Own-PR benchmark method (sealed git, held-out tests, no LLM judge) is the stealable eval pattern | Blog methodology + early “git history leak” failure mode | HIGH | [SOURCE: Databricks blog] | VERIFIED |
| 7 | Last ~2 weeks of harness lit converges: harness swap ≫ model swap for $/task | Writer 2607.06906; Harness-Bench 2605.27922; EFC 2605.29682; our 06-24 sweep | HIGH | arXiv HTML + local | VERIFIED |

### Key Findings

#### 1. Relevance — yes (method + economics, not their leaderboard)

The Databricks post is a **private, PR-derived coding bench** on a multi-million-LOC polyglot monorepo. Four conclusions map onto work we already do:

| Databricks claim | Our prior |
|---|---|
| Mix of models on the Pareto frontier | Multi-vendor routing (Opus / GPT / Cursor / GLM cosign) |
| Capability tiers → push routine work down | Verifier-conditioned dispatch (cheap lane when gates exist) |
| $/token ≠ $/task | Dispatch economics: Opus can be cheaper than Sonnet on gated work |
| Harness dominates cost at fixed model | Harness-1 fixed-model lift; Writer −41% $/task harness-only |

**What not to copy blindly:** their GLM-as-daily-driver recommendation, their Omnigent product path, or any absolute % from an unpublished private bench. [INFERENCE]

**Stealable methodology (if we ever build a private coding eval):**
1. Mine recent **human** PRs with real tests.
2. Prompt = intent only (strip solution narrative).
3. Hold out tests; grade with **tests**, not LLM-as-judge.
4. **Seal git history** for the run (they caught agents walking `git log` to the merged fix).
5. Report **$/task and tokens/task**, not just pass rate.

That is closer to `/eval` design than to a new coding agent. Hand off to `/eval` if we want a genomics/agent-infra PR-bench.

#### 2. Pi harness — inspectable; steal context discipline

**What Pi is:** MIT coding-agent toolkit (`earendil-works/pi`, formerly in the pi-mono / badlogic lineage). Packages: `pi-ai`, `pi-agent-core`, `pi-coding-agent`, `pi-tui`. ~69k stars; active 2026-07-09. Docs: [pi.dev](https://pi.dev). Omnigent lists Pi alongside Claude Code / Codex as a swappable harness. [SOURCE: github.com/earendil-works/pi API; Databricks Omnigent blogs]

**Databricks’s Pi claim (workload-specific):** same model + thinking effort → Pi vs Claude Code/Codex: **quality ≈ same, $/task often >2× different**, because Pi sent **~3× less context per turn** and finished in fewer runs. Mechanism attributed to tighter working set, not magic model weights. [SOURCE: Databricks blog] — **not independently replicated here**.

**Documented Pi mechanisms worth stealing into *our* stack** (from published compaction docs — primary):

| Mechanism | Detail | Our analogue / gap |
|---|---|---|
| Auto-compaction threshold | `contextTokens > contextWindow - reserveTokens` (default reserve **16 384**) | CC native compact + our PreCompact hooks |
| Keep-recent budget | `keepRecentTokens` default **20 000** | We don’t own this knob under CC |
| Structured summary | Goal / Progress / Decisions / Next Steps + `<read-files>` / `<modified-files>` | Checkpoint.md is weaker / instruction-driven |
| Summarizer serialization | `TOOL_RESULT_MAX_CHARS = 2000` in `utils.ts` before summarization LLM | High-leverage: tool-result bloat is our token tax |
| Session trees + branch summarization | Side-quest then merge with summary | Partially mirrored by worktrees; no first-class branch-summary |
| Extension hooks | `session_before_compact` can cancel or supply custom summary | We have PreCompact side-effects; less control of summary body |
| Minimal core | 4 tools (Read/Write/Edit/Bash); extensions/skills for the rest | Already noted in `openclaw-deep-dive.md` |

Primary doc: [SOURCE: https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/compaction.md]  
Source pointers in that doc: `compaction.ts`, `branch-summarization.ts`, `session-manager.ts` under `packages/coding-agent/src/core/` (repo may also reference `pi-mono` paths — same lineage).

**Permissions caveat:** Pi has **no built-in FS/network permission system** — sandbox via Docker / Gondolin / OpenShell. Our fail-closed hooks are a different (and for us, load-bearing) design. Don’t “steal” permissiveness. [SOURCE: Pi README]

**Practical steal list (ranked):**
1. **Tool-result truncation before any summarizer / long-context refeed** (2000-char pattern) — highest transfer, harness-local.
2. **Structured compaction summary with cumulative file ops** — improve checkpoint / PreCompact consumers.
3. **Measure context tokens *per turn* and $/task** on a fixed task set across CC vs Cursor vs (optional) Pi — don’t believe Databricks’s 3× until we meter it.
4. Optional: one-day **Pi dogfood** on a disposable repo for qualitative feel — not a migration plan.
5. **Do not** replace Claude Code with Pi as the RSI home (hooks/skills/SessionStart are our moat).

Clone for local read (when network/sandbox allows):  
`git clone --depth 1 https://github.com/earendil-works/pi.git` → read `packages/coding-agent/docs/compaction.md` + `src/core/compaction/`.

#### 3. Omnigent — meta-harness, not the Pi lesson

Databricks open-sourced **Omnigent** (Apache 2.0): YAML-swappable runners over Claude Code / Codex / Pi / Cursor + **contextual policies** (session spend, risk). [SOURCE: databricks.com/blog/introducing-omnigent-…]

For us: interesting as **validation of multi-harness routing**, not as a dependency. We already swap via llmx / Cursor / Codex. Adopting Omnigent would be shared-infra blast radius with unclear ROI vs tightening *our* context assembly.

#### 4. Last-week / recent harness research (convergent)

| Work | Date | Steal |
|---|---|---|
| **Writer — The Harness Effect** (arXiv:2607.06906) | Jul 2026 | Controlled harness-only swap: **−41% $/task, −38% tokens, quality ≈ flat**; “token maxing” framing; harness leverage (strong models gain more quality from structure) [SOURCE: arxiv.org/html/2607.06906] |
| **Harness-Bench** (2605.27922) | May 2026 | Report **model×harness** configs, not model alone — matches Databricks + our F3 consumer-tier note |
| **EFC scaling laws** (2605.29682) | May 2026 | Optimize for *effective feedback*, not raw tokens |
| **Our 2026-06-24 RSI↔harness sweep** | Jun 24 | Frontier validates verifier-conditioned loop; F3 consumer-tier split **parked** (gate unused) |
| **Lilian Weng harness-RSI survey** | ~Jul 4 | Cited in our 07-08 improvement-log revision — convergent, not new build |

Writer’s mechanism families (cache-shape, structured compaction, context offload, failure-spend governance) are the same family as Pi’s tight working set — different product, same lever. [SOURCE: 2607.06906 abstract/intro]

### What’s Uncertain

- Exact Databricks task count, CI, and statistical tests — blog is qualitative on error bars. [UNVERIFIED]
- Whether Pi’s 3× context reduction reproduces on *our* repos (CC always-loaded skills/hooks may dominate). Needs a meter, not a blog cite.
- GLM-5.2 coding daily-driver claim under *our* hooks + genomics/intel workloads — open; would need `/eval`, not a routing flip.
- Live clone of Pi into `.scratch/` failed in this session’s sandbox (git hooks permission) — inspection used published docs + GitHub API; full `compaction.ts` line-read still recommended offline. [DATA]

### Verdict / recommended actions

**Relevant: yes.** Treat as convergent evidence for (a) task-level cost metering, (b) harness context discipline, (c) private PR-bench methodology — not as a mandate to switch agents or promote GLM.

**Steal from Pi:** structured compaction ideas + optional dogfood; **don’t** migrate the RSI home. **Do not** adopt global 2k tool-result truncation (SKIP — not strictly better; see plan).

**Actions (2026-07-09):**
1. Memo written (this file); research-index already lists it.
2. **B SKIP** — Pi 2k is summarizer-serialization only; we lack that hook surface; live PostToolUse 2k would be worse.
3. **A DONE** — `just harness-cost-meter` (`scripts/harness_cost_meter.py`): observe (agentlogs vendor rollup) + probe (cursor/llmx/pi).
4. Still open: `/eval` sealed-git PR microbench; Pi dogfood after install.

### Sources & Search Log

- Databricks blog (fetched): https://www.databricks.com/blog/benchmarking-coding-agents-databricks-multi-million-line-codebase
- Pi repo: https://github.com/earendil-works/pi (API: stars≈69045, MIT, pushed 2026-07-09)
- Pi compaction docs: https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/compaction.md
- Pi README: https://raw.githubusercontent.com/earendil-works/pi/main/README.md
- Writer Harness Effect: https://arxiv.org/html/2607.06906
- Omnigent intro: https://www.databricks.com/blog/introducing-omnigent-meta-harness-combine-control-and-share-your-agents
- Local: `decisions/2026-06-07-state-externalization-lens.md`, `research/2026-06-24-rsi-loop-vs-harness-evolution-sweep.md`, `research/openclaw-deep-dive.md`, model-guide GLM/dispatch sections
- Queries: “Pi coding agent harness Databricks Omnigent”, “earendil-works/pi”, “agent harness efficiency arxiv July 2026”
