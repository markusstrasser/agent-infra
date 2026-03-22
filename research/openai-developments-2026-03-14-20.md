## OpenAI Developments -- March 14-20, 2026

**Question:** What are the latest OpenAI developments from mid-March 2026?
**Tier:** Standard | **Date:** 2026-03-20
**Ground truth:** Prior vendor sweep (anthropic-platform-sweep-2026-03-02.md) covered through early March. GPT-5.4 flagship launched March 5. Codex CLI known to be at ~0.114.x.

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | GPT-5.4 mini released March 17 at $0.75/$4.50 per 1M tokens | Official model card | HIGH | [developers.openai.com/api/docs/models/gpt-5.4-mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini) | VERIFIED |
| 2 | GPT-5.4 nano released March 17 at $0.20/$1.25 per 1M tokens | Official model card | HIGH | [developers.openai.com/api/docs/models/gpt-5.4-nano](https://developers.openai.com/api/docs/models/gpt-5.4-nano) | VERIFIED |
| 3 | GPT-5.4 mini scores 54.4% on SWE-Bench Pro (vs flagship 57.7%) | News aggregator citing OpenAI | MEDIUM | [resultsense.com](https://www.resultsense.com/news/2026-03-18-openai-launches-gpt-5-4-mini-and-nano) | SINGLE-SOURCE |
| 4 | GPT-5.4 nano scores 39.0% on OSWorld-Verified (human: 72.4%) | Blog citing OpenAI | MEDIUM | [buildfastwithai.com](https://www.buildfastwithai.com/blogs/gpt-5-4-mini-nano-explained) | SINGLE-SOURCE |
| 5 | OpenAI acquiring Astral (uv/ruff/ty) announced March 19 | Official announcement + wide coverage | HIGH | [openai.com](https://openai.com/index/openai-to-acquire-astral/) | VERIFIED |
| 6 | Codex CLI 0.115.0 released March 16 with image inspection, filesystem RPCs | GitHub release page | HIGH | [github.com/openai/codex/releases/tag/rust-v0.115.0](https://github.com/openai/codex/releases/tag/rust-v0.115.0) | VERIFIED |
| 7 | Codex CLI 0.116.0 released March 19 with device-code auth, plugin marketplace | Official Codex changelog | HIGH | [developers.openai.com/codex/changelog](https://developers.openai.com/codex/changelog) | VERIFIED |
| 8 | ChatGPT model picker redesigned to Instant/Thinking/Pro tiers, March 17 | Release aggregator | MEDIUM | [releasebot.io](https://releasebot.io/updates/openai/chatgpt) | VERIFIED |
| 9 | "Nerdy" personality preset sunset March 17 | Release aggregator | MEDIUM | [releasebot.io](https://releasebot.io/updates/openai/chatgpt) | SINGLE-SOURCE |
| 10 | Legacy deep research mode being removed March 26 | OpenAI help center | HIGH | [help.openai.com](https://help.openai.com/en/articles/6825453-chatgpt-release-notes) | VERIFIED |

---

### 1. New Model Releases

#### GPT-5.4 mini (March 17)

The headline release. A distilled version of GPT-5.4 optimized for coding, computer use, and subagent workloads.

**Technical specs:**
- **API ID:** `gpt-5.4-mini` / `gpt-5.4-mini-2026-03-17`
- **Context window:** 400,000 tokens
- **Max output:** 128,000 tokens
- **Knowledge cutoff:** August 31, 2025
- **Pricing:** $0.75 input / $4.50 output per 1M tokens (cached input: $0.075)
- **Modalities:** Text + image input, text output
- **Capabilities:** Streaming, function calling, structured outputs, MCP, computer use, web/file search, code interpreter

**Benchmarks (from OpenAI):**
- SWE-Bench Pro: 54.4% (flagship GPT-5.4: 57.7%) [SINGLE-SOURCE]
- OSWorld-Verified: 72.1% (human baseline: 72.4%, flagship: 75.0%) [SINGLE-SOURCE]
- Over 2x faster than GPT-5 mini

**ChatGPT availability (March 18 rollout):**
- Free/Go users: via "Thinking" feature in + menu
- Paid users: rate-limit fallback for GPT-5.4 Thinking
- Enterprise: configurable as Auto routing default
- GPT-5 Thinking mini: retired in 30 days

**Pricing discrepancy note:** Reddit users flagged openai.com/api/pricing showed mini at $0.250/$2.000, conflicting with the $0.75/$4.50 on the model card page. The pricing page mentions "standard processing rates for context lengths under 270K" -- the discrepancy may reflect a tiered pricing structure. Could not verify directly (pricing page returned 403). [UNVERIFIED]

#### GPT-5.4 nano (March 17)

The cheapest GPT-5.4-class model, designed for simple high-volume tasks.

**Technical specs:**
- **API ID:** `gpt-5.4-nano` / `gpt-5.4-nano-2026-03-17`
- **Context window:** 400,000 tokens
- **Max output:** 128,000 tokens
- **Knowledge cutoff:** August 31, 2025
- **Pricing:** $0.20 input / $1.25 output per 1M tokens (cached input: $0.02)
- **Batch API:** 50% discount for non-time-sensitive tasks
- **Modalities:** Text + image input, text output
- **Capabilities:** Streaming, function calling, structured outputs, MCP, web/file search, code interpreter
- **NOT supported:** Computer use, tool search

**Benchmarks:** OSWorld-Verified 39.0% [SINGLE-SOURCE]

**API-only** -- no ChatGPT consumer interface.

**Use cases:** Classification, data extraction, ranking, subagents, background batch processing.

**Cost comparison (per Awesome Agents):** Mini is ~70% cheaper than flagship GPT-5.4; nano is ~92% cheaper. [SOURCE: awesomeagents.ai]

---

### 2. Codex CLI Updates

#### Codex CLI 0.115.0 (March 16)

**New features:**
- Full-resolution image inspection via `view_image` and `codex.emitImage(..., detail: "original")`
- `js_repl` now exposes `codex.cwd` and `codex.homeDir` helpers with persistent tool/image references across cells
- Realtime websocket: dedicated transcription mode + v2 handoff via `codex` tool
- App-server filesystem RPCs: file reads/writes/copies/directory management/path watching + new Python SDK
- **Smart approvals:** Review requests route through guardian subagent (core, app-server, TUI)
- Integration improvements: Responses API tool-search flow with missing tool suggestions

**Bug fixes:**
- Subagents now inherit sandbox rules, network policies, project-profile layering, host approvals, symlinked writable roots
- `js_repl` hang on Unicode U+2028/U+2029 fixed
- TUI exit stall after subagent creation fixed
- `codex exec --profile` settings preservation restored
- MCP tool-name normalization improved

**Known issues (from GitHub):**
- Approval prompt regression: shown for almost every command, "don't ask again" ignored (issue #14936, labeled bug/sandbox/regression)
- MCP servers with hyphens in names stop showing tools via `/mcp` (issue #14927)
- `/compact` timeout errors on Linux (issue #14860)

#### Codex CLI 0.116.0 (March 19)

**New features:**
- Device-code ChatGPT sign-in during onboarding + token refresh
- Plugin marketplace: automatic install prompts, remote sync of install/uninstall states, curated discovery
- **`userpromptsubmit` hook:** Prompts can be blocked or augmented before execution and before entering history
- Realtime sessions now start with recent thread context, reducing self-interruptions during audio playback
- Plugin uninstall endpoint added

**Bug fixes:**
- First-turn websocket prewarming stall resolved
- Conversation history for remote resume/fork restored
- Linux sandbox startup with symlinked checkouts and AppArmor improved

---

### 3. API Changes

**March 16:** `gpt-5.3-chat-latest` slug updated to point to latest ChatGPT model
**March 13:** Image encoder bug fix for `input_image` in GPT-5.4 (v1/responses, v1/chat/completions)
**March 12 (pre-window):** Sora video API expansion -- `POST /v1/videos/edits` endpoint, character references, 20s generation, 1080p for sora-2-pro, Batch API for video

**Deprecation notice (ongoing):** Assistants API deprecated August 2025, removal August 2026. Responses API is the successor.

**Regional processing:** 10% uplift now applies to gpt-5.4, gpt-5.4-mini, gpt-5.4-nano, and gpt-5.4-pro data residency endpoints.

---

### 4. Acquisition: Astral (uv/ruff/ty) -- March 19

The most strategically significant development of the week.

**What:** OpenAI announced acquisition of Astral, maker of:
- **uv** -- Python environment/dependency manager (126M+ monthly downloads)
- **ruff** -- Extremely fast Python linter/formatter
- **ty** -- Python type checker
- **pyx** -- Private package registry (notably absent from announcements)

**Integration:** Astral team joins OpenAI's Codex team. Goal: accelerate Codex and "explore how tools can work more seamlessly with Codex."

**Open source commitments:**
- Astral: "Open source is at the heart of that impact" -- will "keep building in the open"
- OpenAI: "After closing OpenAI plans to support Astral's open source products"
- Simon Willison notes these statements have "slightly different focus" -- OpenAI emphasizes Codex acceleration, not community collaboration

**Risk factors:**
- uv is load-bearing infrastructure for the Python ecosystem
- OpenAI has no established track record maintaining acquired OSS projects
- Mitigation: permissive licensing (MIT/Apache 2.0) makes uv "very forkable and maintainable" per Astral engineer Douglas Creager

**Market context:**
- Parallels Anthropic's December 2025 acquisition of Bun (JavaScript runtime)
- Both acquisitions signal coding-tool vertical integration as competitive axis
- Promptfoo and OpenClaw are other recent OpenAI OSS acquisitions

**Direct impact on us:** We use `uv` as the primary Python tool across all projects. Short-term: no change expected. Medium-term: watch for vendor lock-in signals (Codex-exclusive features, license changes). The permissive licensing provides a fork safety net.

---

### 5. ChatGPT Product Changes

**Model picker redesign (March 17):**
- Simplified to three tiers: Instant (fast), Thinking (deeper reasoning), Pro (most advanced)
- New "Auto-switch to Thinking" setting: automatic escalation based on task complexity
- Advanced controls for legacy model access and thinking effort tuning
- Retry functionality streamlined

**Personality changes:**
- "Nerdy" base style preset sunset (March 17)
- GPT-5.3 Instant: follow-up tone improved, reduced "teaser-style phrasing" like "If you want..." and "You'll never believe..." (March 16)

**Upcoming:**
- Legacy deep research mode removal: March 26 (current deep research experience remains)
- GPT-5 Thinking mini retirement: ~30 days from March 18

---

### What's Uncertain

1. **GPT-5.4 mini pricing discrepancy** -- $0.75/$4.50 (model card) vs $0.250/$2.000 (pricing page per Reddit). May be tiered by context length. [UNVERIFIED]
2. **Astral deal terms** -- financial details not disclosed
3. **Benchmark numbers** -- SWE-Bench Pro and OSWorld scores are from secondary sources citing OpenAI; the official blog post (openai.com/index/introducing-gpt-5-4-mini-and-nano/) returned 403 for direct verification
4. **Cost creep claim** -- one source (adam.holter.com) claims mini/nano are 2.25x-3.5x more expensive than GPT-5 mini/nano predecessors. Not verified against historical pricing. [SINGLE-SOURCE]

### Sources Checked
- OpenAI official: model cards, API changelog, Codex changelog, help center (partial -- some 403s)
- News: TechCrunch, The Verge, ZDNET, Fortune, Ars Technica, CNBC, SiliconANGLE, The Register
- Aggregators: releasebot.io, llm-stats.com
- Community: Reddit r/OpenAI, Simon Willison's blog
- GitHub: openai/codex releases and issues

<!-- knowledge-index
generated: 2026-03-22T00:13:52Z
hash: 504be41645d6

table_claims: 10

end-knowledge-index -->
