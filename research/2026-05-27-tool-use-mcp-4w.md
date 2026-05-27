---
date: 2026-05-27
topic: tool use, MCP protocol, function calling — 4-week delta
window: 2026-04-29 → 2026-05-27
tier: standard
baselines_refreshed:
  - research/agent-tools-mcp-landscape-2026-03.md
  - research/mcp-protocol-evolution.md
  - research/tool-use-mcp-reliability.md
  - research/2026-04-25-tool-attention-and-skill-bank.md
  - research/ecosystem-mcp-refresh-2026-04.md
  - research/fastmcp3-integration-plan.md
  - research/skill0-internalization-2026-04.md
---

# Tool Use / MCP / Function Calling — 4-Week Delta (2026-04-29 → 2026-05-27)

Headline: **MCP 2026-07-28 Release Candidate dropped May 21 — the largest revision since launch, goes stateless, deprecates the SSE-era session model**. Computer-use leaderboards consolidated on Claude Mythos Preview (79.6%), Google killed Project Mariner May 4, Anthropic shipped MCP Tunnels + self-hosted sandboxes May 19. On the research side, MCP-Atlas (220 tools / 36 servers) is the new credible MCP-native benchmark and a "Tool Descriptions Are Smelly" study landed with measurable lift.

---

## Section 1 — Research Findings

### 1.1 MCP-Atlas (Bandi et al., arXiv:2602.00933, 17 citations) — the MCP-native benchmark we were missing

1,000 expert-written tasks (500 public / 500 private hold-out), **220 tools across 36 real MCP servers**, multi-step + cross-server workflows where the agent picks tools without prompting hints. Claim-level rubric scoring (factual assertions extracted from tool outputs) lets credit be awarded for varied call orderings. Frontier ceiling: **82.2% pass at 0.75 claim coverage** across 20 models / 6 providers.

Most actionable diagnostic: **63.3% of failures are cognitive, not tool-invocation** — models stop prematurely after a successful tool call and never re-engage. This matches our internal session-analyst pattern ("stopped early with incomplete result") and is now externally measured. `[SOURCE: arxiv.org/abs/2602.00933]` `[CONFIDENCE: HIGH]`

### 1.2 MCP Tool Descriptions Are Smelly! (Hasan et al., arXiv:2602.14878, 4 citations)

Catalogs "smells" in MCP tool descriptions — vague verbs, missing parameter semantics, redundant overlap — across the public ecosystem. Augmenting descriptions with structured examples + return-shape hints improves invocation accuracy. Direct relevance to our `~/Projects/skills/` and research-MCP tool docstrings: the codebase has tool descriptions written for humans, not for embedding-based retrieval (the Tool Attention paper's ISO score depends on this). **Liftable:** add a docstring linter that flags MCP tool descriptions failing on the Hasan smells. `[SOURCE: arxiv.org/abs/2602.14878]` `[CONFIDENCE: MEDIUM — paper measured lift on a curated corpus, not Claude Code production]`

### 1.3 Information Fidelity Martingale Analysis (Fan et al., arXiv:2602.13320)

First theoretical framework for error accumulation in MCP tool chains. Models the cascade as a martingale and shows error compounds super-linearly when tool outputs feed into subsequent tool inputs without intermediate verification. **Argues for a per-step "evidence pin" gate** (verification before the next call) — this is what our `prepare_evidence` step does for research-MCP, by accident more than design. Worth tagging as architectural confirmation of an existing pattern. `[SOURCE: arxiv.org/abs/2602.13320]` `[CONFIDENCE: MEDIUM — theory paper, 1 citation, not yet replicated]`

### 1.4 CUA-Gym (Wang et al., arXiv:2605.25624, May 27) — verifiable RL training environments for computer-use

Scales RLVR (RL with verifiable rewards) to CUAs by constructing deterministic-reward tasks at scale. Releases training infra rather than a new model. **Pertinent for us only if we ever train a CUA**; flagged as the canonical reference if we revisit the "should we train" question. No claimed SOTA. `[SOURCE: arxiv.org/abs/2605.25624]` `[CONFIDENCE: MEDIUM]`

### 1.5 Mobile-Agent-v3.5 / GUI-Owl-1.5 (Xu et al., arXiv:2602.16855, 17 citations)

Open-weight CUA at 2B/4B/8B/32B/235B sizes. **OSWorld 56.5, WebArena 48.4** — SOTA among open-source; ~23pp behind Claude Mythos Preview (79.6 OSWorld-Verified). Confirms the open/closed gap widened, not narrowed, in May. `[SOURCE: arxiv.org/abs/2602.16855]` `[CONFIDENCE: HIGH]`

### 1.6 OS-Symphony (Yang et al., arXiv:2601.07779, 11 citations)

Generalist CUA framework with granular historical visual context curation. Specifically addresses long-horizon workflow brittleness — the dominant failure mode we'd hit if we ever shipped a browser agent. Worth bookmarking; not actionable today. `[CONFIDENCE: HIGH]`

### 1.7 Internal Representations Indicate Tool-Selection Hallucinations (Healy et al., arXiv:2601.05214, 4 citations)

Demonstrates that the agent's hidden-state activations at the moment of tool selection correlate with subsequent invocation correctness. Frames a probe-based "should I trust this call?" gate. **Not directly liftable** without model-internals access (we run hosted Claude/GPT/Gemini), but matters if Anthropic exposes activations or logit data downstream. `[CONFIDENCE: MEDIUM]`

### 1.8 SkillRAE & SkillSeek & SkillsVote (May 2026 skill-bank cluster)

Three concurrent papers extend the skill-bank literature covered in `2026-04-25-tool-attention-and-skill-bank.md`:
- **SkillRAE (arXiv:2605.10114, May 11):** skill-based context compilation for retrieval-augmented execution — packs only the necessary skill snippets into context per step.
- **SkillSeek (OpenReview, May 15):** plug-and-play skill retrieval for *open-source* agentic workflows; framework-agnostic.
- **SkillsVote (arXiv:2605.18401, May 18):** lifecycle governance — collection → recommendation → evolution. Closest to our own `~/Projects/skills/` problem of figuring out which skills are pulling their weight.

None replace the Memento-Skills patterns already in `memento-skills-dive.md`, but **SkillsVote's "lifecycle governance" framing is novel** — formalizes what our `/observe sessions` already does informally. `[CONFIDENCE: MEDIUM — preprints, no replication]`

### 1.9 Function-calling reliability on Opus 4.7 / GPT-5.5 / Gemini 3.5 Flash — pertinent negative

**No credible benchmark-grade numbers for the May-2026 frontier triplet in this window.** Public leaderboards (LLM Stats, awesomeagents) cite mixed-generation results (Claude Sonnet 4.5 still topping τ-bench Airline at 70.0% in self-reported numbers; awesomeagents quotes Opus 4.6 at 84.8% τ-bench without a primary source). The Stanford AI Index 2026 reportedly cites WebArena 74.3% as the production "failure wall" (AgentMarketCap, May 24), but the primary report wasn't fetchable. Treat any cross-model τ-bench / BFCL number you see this month with extra skepticism — vendor-tested, model versioning drift, no third-party verification has caught up to the post-4.6 generation. **Action:** if a function-calling number matters for a decision, run our own probe; do not cite secondary aggregators.

---

## Section 2 — MCP Ecosystem Shifts

### 2.1 MCP 2026-07-28 Spec Release Candidate (announced 2026-05-21) — LARGEST REVISION SINCE LAUNCH

`[SOURCE: blog.modelcontextprotocol.io, PR #2750 in modelcontextprotocol/modelcontextprotocol]` `[CONFIDENCE: HIGH]`

**Headline:** Lead maintainers David Soria Parra and Den Delimarsky describe the RC as "the largest revision of the protocol since launch." Twenty-two scoped SEPs land together. Highlights:

- **Stateless core.** The session model from the SSE era is dropped. `tools/call` requests become self-contained — no sticky routing, no shared session store. Scales on ordinary HTTP infrastructure. Direct breaking change for any server that assumed in-memory session state between calls. (`dev.to/rabinarayanpatra` and `byteiota.com` both have May 23–26 explainers — multiple secondary sources confirm.)
- **Extensions framework formalized.** MCP Apps (server-rendered UIs in sandboxed iframes — already shipped as ext-apps v1.5.0 in April) and **Tasks** (long-running work, SEP-1686 from the March WG cycle) now land in-spec.
- **Authorization realigned with OAuth + OIDC.** Refines what OAuth 2.1 PKCE delivered in March 2025; tightens the conformance gate.
- **Formal deprecation policy.** New governance lifecycle so future SEPs don't break existing builds. Pair this with the extensions framework: core stays small, capabilities ride as extensions.

**Implications for our research-MCP / agent-infra-MCP:**
- Stateless transition is **breaking** for any code path that assumed session continuity. Both of our MCPs are FastMCP-based; the FastMCP 3 integration plan (`fastmcp3-integration-plan.md`) needs a re-read against the RC.
- Spec is RC, not final — finalization targeted for the 2026-07-28 date in the version string. Don't migrate today; **bookmark the SEP list and re-evaluate after final**.

### 2.2 Anthropic MCP Tunnels + Self-Hosted Sandboxes (2026-05-19)

`[SOURCE: claude.com/blog/claude-managed-agents-updates, VentureBeat, The New Stack]` `[CONFIDENCE: HIGH]`

Two paired enterprise features on Claude Managed Agents:

- **MCP Tunnels** (research preview): lightweight gateway opens a single outbound connection from the customer network; Claude agents reach private MCP servers (internal DBs, ticketing, knowledge bases) without exposing any public endpoint, with end-to-end encryption.
- **Self-Hosted Sandboxes** (public beta): tool execution moves to customer-controlled infra — Cloudflare, Daytona, Modal, Vercel are launch integrations. Anthropic keeps the orchestration loop, customer keeps the data plane.

**For us:** Modal is one of the launch sandbox targets. If our Modal-based genomics workers ever need to be Claude-orchestrated externally, this is the path. Not actionable today (we're orchestrating ourselves, not handing the loop to Anthropic), but worth knowing the boundary exists.

### 2.3 AWS MCP Server GA (2026-05-06) and GitHub MCP Server v1.0.5 (2026-05-18)

Big-vendor production MCPs continue landing. AWS MCP Server is now generally available (was preview); GitHub MCP Server is at v1.0.5 — both signal that enterprise MCP is past the "wait and see" phase. No immediate adoption action — neither displaces a tool we currently use — but track for the day we need an AWS-side workflow.

### 2.4 Google Project Mariner shut down (2026-05-04)

`[SOURCE: theverge.com/tech/925559, verified via verify_claim 0.95 confidence]`

Google killed the standalone Mariner browser agent; tech folded into Gemini Agent and AI Mode. **Three-way browser-agent race collapses to two visible frontiers** (Anthropic Computer Use / Claude Operator-style, OpenAI Operator). Per yage.ai's May 11 essay, "Google killed Mariner but Anthropic and OpenAI didn't succeed either" — production reliability is still the wall. Maps to the Stanford AI Index "1-in-3 failure wall" cited by AgentMarketCap.

### 2.5 Computer-use leaderboard state (OSWorld-Verified, May 7 snapshot)

Top of the leaderboard, all self-reported:
1. Claude Mythos Preview — 79.6%
2. GPT-5.5 — 78.7%
3. Gemini 3.5 Flash — 78.4%
4. Claude Opus 4.7 — 78.0%
5. GPT-5.4 — 75.0%

Four-way bunching inside 1.6pp at the top. Average across 13 models: 66.9%. **Open-source SOTA (GUI-Owl-1.5) sits at 56.5 — gap widened to ~23pp.** Note Mythos Preview leads despite Opus 4.7 being the production model; "Mythos" appears to be an Anthropic next-gen preview SKU surfacing only in benchmarks so far. Treat the 0.6pp gap between Mythos and GPT-5.5 as noise.

### 2.6 Pertinent negatives

- **No MCP SDK 2.0 GA yet.** The TypeScript SDK 2.0.0-alpha.1 from April hasn't moved to beta or GA in the window — alpha is still the headline; current production code paths remain on 1.x.
- **No new τ-bench / BFCL releases in the window.** τ-bench remains at v2 (Aug 2024); the agentic-benchmarking literature is shifting to MCP-Atlas (real servers) and CUA evals (visual grounding) rather than text-tool calling.
- **No movement on A2A (agent-to-agent) standardization** beyond Microsoft Agent Framework's April GA — A2A is still "complementary to MCP" in marketing language without an interop spec landing.
- **MCP Skills extension still experimental.** No promotion to "standard" status; our `~/Projects/skills/` flat-markdown format remains compatible.

---

## Liftable / Actionable Summary

| # | Finding | Action | Priority |
|---|---|---|---|
| 1 | MCP 2026-07-28 RC drops sessions, goes stateless | Re-read `fastmcp3-integration-plan.md` against the RC after spec finalizes (target date in the version string) | Defer to July |
| 2 | MCP-Atlas — 63.3% of MCP failures are cognitive (premature stop), not invocation | Confirms session-analyst's "stopped early" pattern is the right detector; consider adding a Stop-hook prompt asking "did you complete the actual ask?" beyond what we have | Medium |
| 3 | Tool Descriptions Are Smelly — augmented descriptions lift invocation accuracy | Audit research-MCP + agent-infra-MCP tool docstrings for the Hasan smells | Low (single-session task) |
| 4 | Martingale error analysis confirms per-step evidence-pin pattern | Architectural validation only; nothing to change | Noop |
| 5 | Function-calling numbers for Opus 4.7 / GPT-5.5 / Gemini 3.5 are NOT credibly benchmarked yet | When such a number matters, run our own probe; do not cite secondary aggregators | Policy |
| 6 | MCP Tunnels + self-hosted sandboxes via Modal (launch partner) | Bookmark for the day we hand orchestration to Anthropic | Defer |
| 7 | SkillsVote lifecycle governance framing | Cross-reference next time we touch `~/Projects/skills/` governance | Defer |

**Memo file path:** `/Users/alien/Projects/agent-infra/research/2026-05-27-tool-use-mcp-4w.md`

<!-- knowledge-index
generated: 2026-05-27T09:19:18Z
hash: e8ad06c534db

cross_refs: research/2026-04-25-tool-attention-and-skill-bank.md, research/2026-05-27-tool-use-mcp-4w.md, research/agent-tools-mcp-landscape-2026-03.md, research/ecosystem-mcp-refresh-2026-04.md, research/fastmcp3-integration-plan.md, research/mcp-protocol-evolution.md, research/skill0-internalization-2026-04.md, research/tool-use-mcp-reliability.md

end-knowledge-index -->
