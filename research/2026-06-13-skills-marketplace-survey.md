---
title: "Skills Marketplace Survey — skills.sh + awesome-claude-skills as dependency evaluation"
date: 2026-06-13
status: complete
tags: [skills, marketplace, dependency-evaluation, claude-code, ecosystem-health, supply-chain]
---

# Skills Marketplace Survey

**Frame:** dependency evaluation, not skill-shopping. Evaluated skills.sh + the six
largest "awesome-claude-skills" GitHub indexes against the existing 21 global skills,
under the repo's standing priors (maintenance-not-effort gate; veto on speculative
extraction, MCP rebuilds, native-tool re-treads; Claude-Code+Codex / macOS / single-user).

**Bottom line: 2 survivors, both narrow and conditional. 0 unconditional adopts.**
The marketplace is real and large but ~70% frontend/web-dev, and the *security model of
the whole distribution channel is broken* (verified, below) — which dominates integration
cost for every candidate. A near-zero survivor count is the correct, healthy outcome.

---

## 1. What's actually out there

### skills.sh (Vercel, launched 2026-01-20)
- **Scale:** ~284 ranked skills on the public leaderboard; **695K cumulative installs** all-time. A curated sibling `officialskills.sh` lists 577 skills from 48 publisher teams.
- **Distribution:** `npx skills add <owner/repo>` (GitHub shorthand / URL / local path). Drops a folder into `.claude/skills/<name>/` (or `~/.claude/skills` with `-g`), writes `.skills.json` (manifest) + `skills-lock.json` (version pin). Supports 70+ agents (Claude Code, Codex, Cursor, Gemini CLI, …).
- **SKILL.md format:** identical to what we already use — YAML frontmatter (`name`, `description` required; `license`, `allowed-tools`, `metadata` optional), optional `scripts/` `references/` `assets/`. **No format lock-in: we already author this exact shape**, so "integration" = copy a folder, not adopt a packaging system.
- **Composition of the top 30 by installs:** find-skills (vercel, 2.0M) · frontend-design (anthropic, 539K — *we already symlink this*) · vercel-react-best-practices (473K) · agent-browser (446K) · Azure AI suite (microsoft, ~389K×4) · remotion video (368K) · web-design-guidelines (387K) · shadcn (188K). **~70% is web-dev / cloud-SDK / design** — outside this system's domain (cross-project research + genomics/phenome/intel data pipelines).

### The awesome-list indexes (maturity-ranked)
| Repo | Stars | Last push | Character |
|---|---|---|---|
| ComposioHQ/awesome-claude-skills | 64.4K | 2026-05-22 | Largest by stars; heavy on Composio's 78-app SaaS automation layer |
| hesreallyhim/awesome-claude-code | 46.3K | 2026-04-27 | Skills+hooks+slash-commands+orchestrators; README is a placeholder, data in CSV |
| VoltAgent/awesome-agent-skills | 25.2K | 2026-06-12 | Org-indexed registry of 1000+ official-team skills |
| travisvn/awesome-claude-skills | 13.4K | 2026-04-28 | Clean curated list |
| karanb192/awesome-claude-skills | 375 | 2025-10-21 | **Stale 8mo**; many "community-needed" placeholders |
| Chat2AnyLLM/awesome-claude-skills | 138 | 2026-06-13 | Auto-generated index, low curation signal |

### Official-publisher skill packs (the real signal — these have a bus factor)
Anthropic (`anthropics/skills`, **150K★**, pushed 2026-06-09): docx/pdf/pptx/xlsx, doc-coauthoring, frontend-design, skill-creator, mcp-builder, webapp-testing, web-artifacts-builder, claude-api, canvas-design, algorithmic-art, brand-guidelines, internal-comms, slack-gif-creator, theme-factory. **License is `Proprietary` (per-skill LICENSE.txt), not Apache/MIT.**
Trail of Bits (`trailofbits/skills`, 5.7K★, CC-BY-SA-4.0): ~21 security skills (static-analysis, differential-review, semgrep-rule-creator, property-based-testing, entry-point-analyzer, building-secure-contracts, constant-time-analysis, …).
Others: Sentry (32 obs skills), Datadog (APM/logs/LLM-trace-RCA), HashiCorp (11 Terraform), Cloudflare (8 Workers), Figma (7), Microsoft (133+ Azure), Google Workspace (17), Stripe (2), OpenAI (security/notion/gh-ci/linear).
Community standout: **obra/superpowers** (`MIT`, **226K★**, v5.1.0 2026-05-04) — brainstorming, TDD, systematic-debugging, writing/executing-plans, using-git-worktrees, dispatching-parallel-agents, requesting/receiving-code-review, verification-before-completion.

---

## 2. The dominant dependency risk: the distribution channel is unsafe (verified)

This is the single most important finding and it applies to **every** candidate.

**Trail of Bits, "The sorry state of skill distribution" (2026-06-03, blog.trailofbits.com).** Verified at primary source. They bypassed **all three scanners integrated into skills.sh, plus ClawHub, plus Cisco's agent-skill scanner** — 3 of 4 malicious skills built in **under an hour**:
- `simple-formatter` — claims to format text; uses **Python bytecode poisoning** to exfiltrate env vars (i.e. our `~/.env` API keys).
- `dev-env-setup` — claims to bootstrap a dev env; ships **prompt injection**.
- `context-loader` — claims to sync context; **smuggles a malicious script inside the XML of a hidden .docx**.
Verdict from ToB: static scanners give an adversary unlimited retries; marketplace scanning is not a trust boundary. (Companion repo: `trailofbits/overtly-malicious-skills`.)

**Implication for this system.** A skill is arbitrary instructions + `scripts/` executing in the agent's context with our filesystem, git, and `~/.env`. `npx skills add` from an unknown publisher is `curl | bash` with a marketing page. The repo's existing posture already encodes the mitigation: `skill-provenance-controls-2026-03.md`, the data-protection commit-time guards, and the global rule "AI-generated text is unverified by default." **Therefore the only defensible integration path is: vendor the folder from a named-org repo, read every line + every script, pin the SHA, drop it under `~/Projects/skills/` (our governed dir), never `npx skills add` community skills, never auto-update.** This converts "install a dependency" into "copy + audit a snippet," which is the only mode that survives the priors.

---

## 3. Why almost everything is rejected (the overlap wall)

The existing 21 skills already own the high-value generic-agent workflows that the marketplace's non-frontend skills also target. Concretely:

| Marketplace skill(s) | Already covered by | 
|---|---|
| superpowers brainstorming · grill-me · to-prd | `brainstorm`, `interview-prompt`, `decide` |
| superpowers TDD · testing-anti-patterns · pypict | `eval` (decision-grade eval discipline); TDD is a workflow we deliberately don't ritualize |
| superpowers systematic-debugging · diagnose · root-cause-tracing · garry-tan/investigate | `analyze` (causal/ACH/weakest-link lenses), `observe` |
| superpowers writing-plans/executing-plans · subagent-driven-development · AB-method | `decide` + `execute` (phase-gated, worktree-isolated, probe-before-build) |
| superpowers dispatching-parallel-agents · agentic-workflow-patterns · loki-mode · great_cto · Septim | `execute`'s worktree subagent fan-out + `Agent` tool; multi-named-subagent packs are exactly the "speculative orchestration" the constitution distrusts |
| requesting/receiving-code-review · coderabbit · sentry-code-review · differential-review (generic) | `upgrade`, `critique`, `code-review`, `simplify` |
| recursive-research · claude-scientific-skills · article-extractor · youtube-transcript | `research` + research-mcp (S2/Exa/Perplexity, source grading, citation traversal) |
| handoff · caveman · lean-ctx (context compression) | our checkpoint.md + context-budget rules + state-externalization lens |
| using-git-worktrees · git-pushing · finishing-a-branch | native git + `execute` worktree isolation + git hooks |
| skill-creator · write-a-skill · Skill_Seekers | `skill-authoring` skill (already present) |
| Composio/google-workspace/n8n/CRM SaaS actions | **blocked by invariant #3 (no external contacts)** — a feature, not a gap |
| HashiCorp Terraform · Cloudflare Workers · Netlify · Azure · AWS-CDK · Figma · shadcn | **not this system's stack** (no IaC, no edge deploys, no frontend) |
| read-only-postgres | native SQLite is the system's DB; no live Postgres to guard |

That table is the whole point: the marketplace's generic-agent skills are **redundant**, and its specific skills are **off-domain**. What's left after removing both sets is tiny.

---

## 4. Ranked shortlist — survivors (2)

### #1 — Anthropic office-document **generation** skills (`docx` / `xlsx` / `pptx`) — CONDITIONAL ADOPT, vendor-on-first-need
- **Gap it fills:** generating Office files as **output**. Verified the system has PDF→markdown *input* extraction (Modal+marker, `corpus ingest --pdf`) and downloads PDF codebooks, but **no office-doc generation path**. `openpyxl` is already a direct `intel` dependency, so xlsx writing is partially in use ad-hoc — the skill would standardize it. These are real, not demos: each ships `scripts/` + reference docs over `pypdf`/`python-docx`/`openpyxl`/`python-pptx`.
- **Why our tools don't cover it:** `pdf` (input) is the marker pipeline; there is nothing for "emit a formatted .xlsx/.docx report." This is the one capability axis genuinely absent.
- **Dependency risk:** LOW on bus-factor (Anthropic, 150K★, current), but **license is `Proprietary`** — must read each LICENSE.txt before vendoring; do not assume reuse rights. Scripts are short and auditable.
- **Integration cost:** LOW-but-deferred. **Do NOT pre-install.** This is a "build when the problem occurs" item per the repo's own gate — there is no current incident of "needed to emit a .docx and couldn't." When a task first needs office-doc output, vendor the single relevant skill folder (read it, pin SHA) into `~/Projects/skills/`. Until then: noted, not adopted.
- **Verdict:** the best candidate, but its trigger hasn't fired. Pre-registered trigger: *first task that must emit a .xlsx/.docx/.pptx report.*

### #2 — Trail of Bits **security-audit** skills (`semgrep-rule-creator`, `static-analysis`, `differential-review`) — WATCH, narrow conditional
- **Gap it fills:** real SAST (CodeQL+Semgrep+SARIF) and security-diff review. `upgrade`/`critique`/`code-review` find correctness + design issues, not CVE-class vulns or timing side-channels.
- **Why our tools don't cover it:** none of the 21 run a static-analysis engine or author Semgrep rules.
- **Dependency risk:** LOW (ToB is the credible security org here; CC-BY-SA-4.0, 5.7K★, current) — ironically the only publisher who *proved* the channel is unsafe, so trustworthy to vendor-and-audit.
- **Integration cost:** MEDIUM and **mostly off-domain.** The suite is built for smart-contracts (Slither/Echidna) and web-app attack surface — this system is Python research/data pipelines with no untrusted-input-facing service and no deployed product. The actual security need here is *supply-chain* (the skill channel itself), which a SAST skill doesn't address.
- **Verdict:** **WATCH, don't adopt.** Pre-registered trigger: *if any project grows a network-facing service or processes untrusted external input*, vendor `static-analysis` + `differential-review`. No such surface exists today.

**Explicitly considered and rejected as #3-5 (no padding):** obra/superpowers (highest-quality community pack, 226K★ — but every one of its 13 skills maps onto `decide`/`execute`/`brainstorm`/`analyze`/`eval`/`critique`; adopting it would be duplicate-with-different-vocabulary, which the constitution treats as harness noise). Datadog/Sentry observability (no production service to monitor). Composio SaaS layer (invariant #3). great_cto / Septim multi-subagent packs (speculative orchestration; `execute` already does worktree fan-out). figma/shadcn/Terraform (off-stack).

---

## 5. Ecosystem-health verdict

**Healthy and worth watching — but as a frontier-signal feed, not a dependency source.**

- **Real, not thin:** 695K installs, 48 official publisher teams, active tooling (lockfiles, multi-agent support), 226K★/150K★/64K★ anchor repos pushed within days. This is a genuine ecosystem, not a name-squat. It already feeds `trending-scout` indirectly; worth an explicit periodic skim there.
- **But two structural problems cap its value for us:** (1) **frontend/cloud-SDK gravity** — the install-weighted center of mass is web-dev, which is orthogonal to this system's research/genomics/pipeline domain, so the hit-rate for *us* is low by construction; (2) **broken trust boundary** — ToB demonstrated the scanners are theater, so the channel can never be used in its intended "install with one command" mode; we must downgrade every "install" to "vendor + audit a snippet," which removes most of the marketplace's convenience value.
- **Watch-list action (cheap, no new infra):** add a quarterly line to `trending-scout`'s scope — "new *official-org* skills in off-our-stack-but-adjacent categories (research, data, document, security)." Filter on official publishers only; ignore community skills as install-grade. No standing automation, no MCP, no scraper — this fits the existing trending-scout cadence and the native-first / maintenance-gate priors.

**One-line summary:** the marketplace is a real, growing, but web-dev-centric ecosystem with a verified-broken security model; against 21 mature skills the only genuine gaps are office-doc *generation* (vendor on first need) and SAST (watch until a network-facing surface exists) — adopt nothing today, vendor-and-audit (never `npx skills add`) if a trigger fires.
