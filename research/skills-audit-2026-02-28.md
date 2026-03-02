# Skills Library Review — 2026-02-28

**Mode:** Review (convergent)
**Models:** Gemini Flash (`gemini-3-flash-preview`), Gemini 3.1 Pro (`gemini-3.1-pro-preview`), GPT-5.2
**Constitutional anchoring:** Yes (CONSTITUTION.md, GOALS.md injected)
**Cost:** ~$4 total (Flash ~$0.05, Pro ~$2, GPT ~$2)
**Raw outputs:** `.model-review/2026-02-28/`

## Verified Findings (adopt)

| # | Finding | Source | Verified How | Priority |
|---|---------|--------|-------------|----------|
| 1 | **architect and code-research use stale model names** (`gemini-2.5-pro`, `gpt-5-pro`, `claude-sonnet-4-5`) | Flash + Gemini Pro | Grep confirmed: architect/SKILL.md:183, code-research/SKILL.md:34,80,98,182 | HIGH — causes 404s |
| 2 | **Gemini temperature contradiction:** model-review says `-t 0.3`, model-guide says "Keep at 1.0 — lowering causes looping" | GPT-5.2 | model-guide/SKILL.md:92 vs model-review `-t 0.3` | HIGH — conflicting instructions |
| 3 | **model-guide benchmark numbers are unsourced** (SimpleQA 72%, ARC-AGI-2 77.1%, etc.) — violates Principle #3 "Every Claim Sourced" | GPT-5.2 | Inspected model-guide/SKILL.md — no citations on any benchmark | MEDIUM — epistemically inconsistent |
| 4 | **Two competing provenance ontologies** (Admiralty vs researcher tags) with no deterministic mapping | GPT-5.2 | researcher uses `[SOURCE:]`/`[INFERENCE]`; constitution mandates Admiralty `[A1]`-`[F6]` | MEDIUM — confusion in mixed workflows |
| 5 | **Recitation protocol duplicated** in researcher, epistemics, investigate, competing-hypotheses | Flash + Gemini Pro | Grep confirmed: same Du et al. paragraph in 4 skills | LOW — duplication, not broken |
| 6 | **10 of 16 skills lack constitutional awareness** | Flash | Verified: only architect, constitution, goals, model-review, researcher reference constitution | MEDIUM — skills drift without anchoring |
| 7 | **Outbox pattern is "unfunded mandate"** — referenced in goals/constitution templates but not implemented anywhere | Gemini Pro | Grep: only appears in goal/constitution SKILL templates as questions | LOW — future work, not broken |
| 8 | **model-review fact-check gate is instruction-only**, not hook-enforced — contradicts "instructions alone = 0% reliable" | GPT-5.2 | Inspected model-review — no hook, just "MANDATORY" in text | MEDIUM — architectural gap |

## Where the Previous Review (2026-02-27) Was Wrong

| Claim from Previous Review | Problem | Who Caught It |
|---------------------------|---------|--------------|
| "15-turn cron MVP" for orchestrator | Investigate has 8 phases, researcher deep tier dispatches subagents — can't fit in 15 turns | Gemini Pro |
| "Use Haiku for entity refresh" | Haiku drops citations in long contexts — violates "Every Claim Sourced" | Gemini Pro |

## Gemini Pro Errors (distrust)

| Claim | Why Wrong/Suspect |
|-------|------------------|
| "researcher lost explicit instruction to manually traverse pagination" | No such instruction existed in deep-research — checked the original SKILL.md |
| "`researcher` forgets primary project goal is $500M-$5B" | The skill is domain-agnostic by design (open-source-ready); project-specific routing belongs in `.claude/rules/` |
| "Recitation should be a system-level hook with XML tags" | Over-engineered for a prompt pattern — the duplication IS the problem, not the mechanism |

## GPT-5.2 Errors (distrust)

| Claim | Why Wrong/Suspect |
|-------|------------------|
| "Portfolio linkage should be built into researcher/model-review" | Project-specific concern — these skills may be open-sourced; portfolio linkage belongs in project rules, not shared skills |
| Cost estimates presented as precise ($0.38 Gemini, $0.19 GPT) | Plausible order-of-magnitude but presented with false precision — token counts vary 3x depending on context |
| Trust calibration Bayesian model | Mathematically sound but practically useless — requires 200+ verified claims to calibrate, and independence assumption is known-false |

## Revised Action Items

### Immediate (do now)
1. ~~Fix model-review model names~~ DONE (Step 4)
2. ~~Fix llmx-guide model names~~ DONE (Step 6)
3. ~~Merge researcher/deep-research~~ DONE (Step 5)
4. **Fix architect model names** — update from `gemini-2.5-pro` → `gemini-3.1-pro-preview`, `gpt-5-pro` → `gpt-5.2`, `claude-sonnet-4-5` → `claude-sonnet-4-6`
5. **Fix code-research model names** — update from `gemini-2.5-pro` → `gemini-3-flash-preview` (cheap) or `gemini-3.1-pro-preview` (quality)

### Near-term (next session)
6. **Resolve temperature contradiction** — model-review `-t 0.3` vs model-guide "keep 1.0". The truth: thinking-mode Gemini locks temp server-side, so `-t 0.3` is a hint that may be ignored. Non-thinking mode respects it. Clarify in both skills.
7. **Add `[TRAINING-DATA]` tags to model-guide benchmarks** — or add citation URLs. Currently violates own epistemics.
8. **Define provenance mapping** — document when Admiralty grades apply vs researcher tags. The existing rule ("Admiralty during OSINT, tags otherwise") is clear but not consistently referenced.

### Deferred
9. Deduplicate recitation protocol across 4 skills (low priority — works fine, just verbose)
10. Constitutional awareness for remaining skills (most don't need it — diagnostics, debug-mcp-servers are tool-only)
11. Verification ledger for model-review outputs (GPT rec — worth trying but not blocking)

## Meta-Observations

**What improved since 2026-02-27:**
- model-review now has constitutional pre-flight, review/brainstorm modes, differentiated prompts, persistent outputs
- researcher absorbed deep-research cleanly
- Domain profiles extracted to companion file (DOMAINS.md)
- Project-specific content cleaned for open-source readiness

**What's still architecturally weak:**
- Fact-checking remains instruction-only (no hook enforcement)
- No token counting/truncation in context bundling
- Recursive subagent risk (investigate → researcher → competing-hypotheses) unmitigated
- Skills library has no version pinning — all skills mutate in place
