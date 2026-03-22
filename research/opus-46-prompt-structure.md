## Opus 4.6 Prompt Structure & Formatting — Research Memo

**Question:** Beyond XML tags, are there formatting or structure tricks specific to Opus 4.6 for system prompts, CLAUDE.md files, and skills?
**Tier:** Standard | **Date:** 2026-03-01
**Ground truth:** Prior session applied XML section tags to CLAUDE.md files across repos. Anthropic's prompting docs recommend XML for Claude. User's tournament-mcp empirical test found no position bias in frontier thinking models.

### Claims Table

| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | ~~Position ordering = up to 30% improvement~~ | Anthropic guide (non-thinking context) vs user's tournament-mcp (thinking models, no effect) | **RETRACTED** for thinking models | [SOURCE: platform.claude.com + user empirical data] | RETRACTED |
| 2 | ~~Stop using MUST/CRITICAL/NEVER~~ | testified.ai says stop; Anthropic's own production prompts (skills, cookbooks) use them heavily | **CONTRADICTED** by Anthropic's own code | [SOURCE: github.com/anthropics/skills, github.com/anthropics/claude-cookbooks] | CONTRADICTED |
| 3 | Anti-laziness prompts are harmful on Opus 4.6 | Anthropic guide + testified.ai; not contradicted by Anthropic's code | MEDIUM | [SOURCE: platform.claude.com, testified.ai] | VERIFIED |
| 4 | XML tags help for section boundaries in agentic prompts | Anthropic's own research_lead_agent.md uses 7 XML sections; Claude Code system prompt uses XML examples throughout | HIGH | [SOURCE: github.com/anthropics/claude-cookbooks, github.com/Piebald-AI] | VERIFIED |
| 5 | Subagent orchestration is native; Opus 4.6 can overuse subagents | Anthropic guide + Claude Code's own subagent guidance fragment | HIGH | [SOURCE: platform.claude.com, Piebald-AI extraction] | VERIFIED |
| 6 | Prefill is deprecated on Opus 4.6 (400 error) | What's New page | HIGH | [SOURCE: platform.claude.com] | VERIFIED |
| 7 | Adaptive thinking replaces budget_tokens; effort parameter controls depth | What's New + prompting guide | HIGH | [SOURCE: platform.claude.com] | VERIFIED |
| 8 | System prompt = operator = "relatively trusted employer" in Claude's trust model | Soul document | HIGH | [SOURCE: gist.github.com/Richard-Weiss] | VERIFIED |
| 9 | Claude Code's system prompt is 150+ composable fragments, not a monolith | Piebald-AI extraction (v2.1.63) | HIGH | [SOURCE: github.com/Piebald-AI/claude-code-system-prompts] | VERIFIED |
| 10 | Anthropic's skill architecture: 3-level progressive disclosure (metadata → body → resources) | skill-creator SKILL.md | HIGH | [SOURCE: github.com/anthropics/skills] | VERIFIED |
| 11 | Context awareness is promptable — tell Claude about compaction, don't stop early | Prompting guide, context windows section | HIGH | [SOURCE: platform.claude.com] | VERIFIED |
| 12 | "Ground quotes" technique — ask model to quote evidence before reasoning | Prompting guide | HIGH | [SOURCE: platform.claude.com] | VERIFIED |

### Key Findings

**1. Position bias is a non-issue for thinking models.**
Anthropic's 30% claim is under "Long context prompting" with no qualifier about thinking mode. The "lost in the middle" literature tests non-thinking retrieval. User's tournament-mcp tested frontier thinking models and found zero position effect. Thinking models reason about information location during their thinking phase, bypassing the attention mechanism failure that causes positional bias. `[INFERENCE from architecture + user empirical data]`

**Implication:** Don't reorganize files for position effects. Organize for human readability and logical grouping.

**2. MUST/CRITICAL/NEVER are fine in agentic prompts.**
testified.ai and Pantaleone.net recommend softening language. But Anthropic's own production prompts use exactly this language:
- `frontend-design/SKILL.md`: "**CRITICAL**: Choose a clear conceptual direction" and "NEVER use generic AI-generated aesthetics" `[SOURCE: github.com/anthropics/skills]`
- `research_lead_agent.md`: "**IMPORTANT**: Never create more than 20 subagents" and "you MUST use parallel tool calls" `[SOURCE: github.com/anthropics/claude-cookbooks]`

The "dial back" advice likely applies to simple API calls where overtriggering is the failure mode. In agentic system prompts, emphasis markers guard against observed failure modes and are used by Anthropic themselves.

**3. Anti-laziness prompts genuinely are harmful.**
Anthropic's guide: "If your prompts previously encouraged the model to be more thorough, you should tune that guidance for Claude Opus 4.6." Specifically: replace "Default to using [tool]" with "Use [tool] when it would enhance your understanding." Remove "If in doubt, use [tool]." This is not contradicted by their code — none of their production prompts contain anti-laziness language. `[SOURCE: platform.claude.com]`

**4. Anthropic uses heavy XML in their own agentic prompts.**
`research_lead_agent.md` (747 lines) wraps every functional section: `<research_process>`, `<subagent_count_guidelines>`, `<delegation_instructions>`, `<answer_formatting>`, `<use_available_internal_tools>`, `<use_parallel_tool_calls>`, `<important_guidelines>`. Each tag delineates a different behavioral mode. `[SOURCE: github.com/anthropics/claude-cookbooks]`

**5. Claude Code's prompt architecture is maximally granular.**
150+ fragments, each 50-500 tokens, conditionally included. Flat imperative sentences. No hedging. Examples: "Avoid over-engineering. Only make changes that are directly requested or clearly necessary." (31 tokens, one concern). `[SOURCE: github.com/Piebald-AI]`

**6. Soul document trust model: we're the operator.**
System prompt content is treated as operator instructions — "messages from a relatively (but not unconditionally) trusted employer." Claude follows without justification "unless those instructions crossed ethical bright lines." We don't need to explain why rules exist — just be clear about what we want. `[SOURCE: gist.github.com]`

**7. Context-save before compaction is a recommended pattern.**
Anthropic's guide includes a sample prompt: "As you approach your token budget limit, save your current progress and state to memory before the context window refreshes. Always be as persistent and autonomous as possible and complete tasks fully." We have precompact-log.sh but don't prompt Claude to save state. `[SOURCE: platform.claude.com]`

### What's Uncertain

- Effect size of XML tags at our file sizes (2-8K tokens). Anthropic's examples are for much larger prompts (20K+). Marginal benefit at our scale is unmeasured. `[INFERENCE]`
- Whether the remaining unread Anthropic pages (migration guide, adaptive thinking deep-dive, effort parameter, 1M context beta) contain additional structural guidance. `[UNKNOWN]`
- Whether Anthropic's own skills/cookbooks represent their best practices or just one team's conventions. `[UNKNOWN]`

### Disconfirmation

- **Position bias retracted** based on user's empirical data contradicting Anthropic's generic claim
- **MUST/CRITICAL language softening contradicted** by Anthropic's own code
- **No contradictory evidence found** for: anti-laziness removal, XML utility, subagent overuse, context-save pattern

### Sources

| Source | Type | Key contribution |
|--------|------|-----------------|
| platform.claude.com prompting guide | Official docs (fetched) | Core recommendations for Opus 4.6 |
| platform.claude.com what's new | Official docs (fetched) | Behavioral changes, deprecations |
| Soul document (gist) | Leaked training doc (crawled) | Trust model, principal hierarchy |
| github.com/anthropics/skills | Official repo (read) | Skill architecture, production prompt patterns |
| github.com/anthropics/claude-cookbooks | Official repo (read) | Agent prompt structure, XML usage |
| github.com/Piebald-AI/claude-code-system-prompts | Third-party extraction (read) | Claude Code prompt decomposition |
| testified.ai | Blog (fetched) | Practitioner claims (partially contradicted) |
| pantaleone.net | Blog (fetched) | Practitioner claims (single-source) |
| User tournament-mcp | Primary empirical data | No position bias in thinking models |

<!-- knowledge-index
generated: 2026-03-22T00:13:52Z
hash: e2d250a9812e

sources: 1
  INFERENCE: from architecture + user empirical data
table_claims: 12

end-knowledge-index -->
