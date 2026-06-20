# Autonomous Coding Agents + Benchmark Movement Scout

Date anchor: 2026-06-20. Search path: Exa primary. I did not use Brave. I did not use Perplexity. I prioritized May-June 2026 and primary sources only.

## Ranked Findings

### 1. Claude Code Dynamic Workflows
Primary URL: https://claude.com/blog/introducing-dynamic-workflows-in-claude-code  
Date: 2026-05-28, with explainer 2026-06-02: https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code  
Claim: Claude Code can now generate task-specific orchestration workflows that fan out tens to hundreds of subagents, use isolated worktrees, and checkpoint long runs.  
Demonstrated vs asserted: Mostly asserted by Anthropic, but the mechanism is concrete: JavaScript workflow files, subagent spawning, model selection, and worktree isolation.  
Maturity: Official Claude Code feature; available in CLI/Desktop/VS Code extension for Pro/Max/Team/Enterprise and API routes.  
Why it matters locally: This is the closest direct steal for a single-operator harness: file-bus/workflow scripts, worktree-isolated scouts, and verifier agents as first-class runtime, not just prompt discipline.

### 2. Claude Opus 4.8 + Claude Code Benchmark/Agent Upgrade
Primary URL: https://www.anthropic.com/news/claude-opus-4-8  
Date: 2026-05-28  
Claim: Opus 4.8 improves agentic coding and terminal-task performance; Claude Code gains higher effort modes, dynamic workflows, and larger-rate-limit support for long runs.  
Demonstrated vs asserted: Vendor-reported benchmark table; useful but not independent. Anthropic explicitly distinguishes Terminus-2 public harness from Codex CLI harness on Terminal-Bench.  
Maturity: Official model release; no repo.  
Why it matters locally: Use higher effort only for hard/long async runs; defaulting everything upward is likely waste. The harness-level improvement is dynamic workflow, not just model swap.

### 3. Codex CLI 0.141.0 Remote Executor / MCP Changelog
Primary URL: https://developers.openai.com/codex/changelog  
Date: 2026-06-18  
Claim: Codex CLI added authenticated end-to-end encrypted Noise relay channels, cross-platform remote execution fixes, and selected executor plugin stdio MCP activation per thread.  
Demonstrated vs asserted: Demonstrated as official changelog entries tied to release numbers and PR references.  
Maturity: GitHub repo https://github.com/openai/codex — about 92.2k stars, last push 2026-06-20, latest prerelease `rust-v0.142.0-alpha.7`.  
Why it matters locally: Codex is moving toward local/remote executor parity plus per-thread MCP activation; good pattern for keeping tool scope thread-local instead of globally loaded.

### 4. Terminal-Bench 2.1 Becomes the Better Local-Agent Signal
Primary URL: https://www.tbench.ai/  
GitHub: https://github.com/harbor-framework/terminal-bench-2-1  
Date: 2026-05-05 repo; leaderboard active June 2026  
Claim: Terminal-Bench 2.1 fixes flawed 2.0 tasks and evaluates real terminal agents in containerized environments; Codex CLI and Claude Code are top named CLI surfaces in current rankings.  
Demonstrated vs asserted: Demonstrated benchmark harness and official leaderboard; exact rankings still depend on agent+model+scaffold.  
Maturity: arXiv 2601.11868 for Terminal-Bench paper; GitHub repo is active.  
Why it matters locally: More relevant than SWE-bench Verified for our harness because it measures shell, build, dependency, process, and end-state correctness, not just patch generation.

### 5. SWE-bench Pro Replaces SWE-bench Verified as the Harder Coding-Agent Yardstick
Primary URL: https://labs.scale.com/leaderboard/swe_bench_pro_public  
GitHub: https://github.com/scaleapi/SWE-bench_Pro-os  
arXiv: https://arxiv.org/abs/2509.16941  
Date: public repo active, last push 2026-05-18; June leaderboard movement ongoing  
Claim: SWE-bench Pro is contamination-resistant, long-horizon, and harder than Verified; public set has 731 instances, total benchmark has 1,865 tasks across 41 repos.  
Demonstrated vs asserted: Demonstrated benchmark/dataset, but vendor-reported scores must be separated from Scale-standardized entries.  
Maturity: GitHub 445 stars, last push 2026-05-18; arXiv 2509.16941.  
Why it matters locally: Stop treating Verified deltas as frontier signal. Pro-style held-out/local repo evals are the right model for our own harness gates.

### 6. Cursor Bugbot / Composer 2.5 Review Loop Upgrade
Primary URL: https://cursor.com/blog/bugbot-updates-june-2026  
Date: 2026-06-10  
Claim: Bugbot is over 3x faster, 22% cheaper, finds 10% more bugs, and can run `/review` before pushing code in Cursor 3.7+.  
Demonstrated vs asserted: Vendor production metrics; no public eval harness in the post.  
Maturity: Official Cursor product release; no public repo.  
Why it matters locally: The steal is pre-push review dedup by diff identity: if the same diff was reviewed locally, don’t re-review it in PR; carry review provenance forward.

### 7. OpenHands 1.8.0 Adds Sub-Agent Delegation
Primary URL: https://github.com/OpenHands/OpenHands/releases/tag/1.8.0  
Date: 2026-06-10  
Claim: OpenHands added LLM profiles, sandbox grouping strategy selection, sub-agent delegation, and a minimal generic ACP agent UI.  
Demonstrated vs asserted: Demonstrated in GitHub release notes and PR references.  
Maturity: GitHub https://github.com/OpenHands/OpenHands — about 77.5k stars, last push 2026-06-17, release 1.8.0 on 2026-06-10.  
Why it matters locally: Sub-agent delegation and sandbox grouping are relevant, but OpenHands is heavier than our local single-operator setup; pattern-steal, not wholesale adoption.

### 8. OpenHands Agent Canvas
Primary URL: https://www.openhands.dev/blog/introducing-agent-canvas  
Date: 2026-06-16  
Claim: OpenHands introduced a self-hostable workspace for running and automating coding agents across local, VM, cloud, and enterprise backends.  
Demonstrated vs asserted: Product release; self-hostable claim is official but still platform-shaped.  
Maturity: Tied to OpenHands repo above; active and large.  
Why it matters locally: Most of this is too hosted/org-control-plane shaped, but the useful steal is a local “control plane” view over multiple agent sessions and automations.

### 9. Amp Custom Agents
Primary URL: https://ampcode.com/news/custom-agents  
Date: 2026-06-19  
Claim: Amp plugins can now define custom agents, register them as main modes or subagent tools, create threads, and run async review workers.  
Demonstrated vs asserted: Official product docs with concrete plugin API examples.  
Maturity: Commercial CLI; npm package `@sourcegraph/amp` has about 50k weekly downloads; public org has small support repos, not the main product source.  
Why it matters locally: Strong steal: agent modes and subagent tools should be programmable objects with thread IDs and parent-thread callbacks, not only prompt templates.

### 10. Cline CLI / Provider Churn
Primary URL: https://github.com/cline/cline/releases/tag/cli-v3.0.21  
Date: 2026-06-09  
Claim: Cline CLI added global auto-update control, Vertex AI ADC tool-use support, connector thread routing fixes, and cleaned up Codex model lists.  
Demonstrated vs asserted: Demonstrated GitHub release.  
Maturity: GitHub https://github.com/cline/cline — about 63.5k stars, last push 2026-06-20, latest release `cli-v3.0.28` on 2026-06-19.  
Why it matters locally: Cline is still the most relevant open IDE/CLI runtime to watch for MCP/provider interoperability, but June releases are incremental rather than benchmark-moving.

## Lower-Relevance / Watchlist

Devin had June 2026 product activity, including Devin Desktop and productivity/guarantee posts, but the surface is hosted and less aligned with a single local operator harness. Primary page: https://cognition.ai/blog/introducing-devin

Zencoder’s most useful recent eval post was March 2026, not within the last four weeks: https://zencoder.ai/blog/20k-bug-that-changed-evals. The core lesson still matters: benchmark adapters can leak tests and produce false confidence, but it is not a fresh May-June development.

Aider remains active but did not surface a genuinely new June 2026 benchmark or architecture move in the primary sources I found. Repo: https://github.com/Aider-AI/aider, about 46k stars, last push 2026-05-22.

## Top Steals

1. Build workflow scripts as runtime artifacts: generated, inspectable, resumable, and capable of spawning isolated verifier/scout threads.  
2. Treat diff review as provenance: cache review by diff identity, avoid duplicate PR/local review, and carry findings into the next loop.  
3. Benchmark our harness on terminal/end-state tasks and held-out local repo tasks; downweight SWE-bench Verified-style scores unless they change a concrete operating decision.