# SKILLS AUDIT CONTEXT — All 16 Skills
Date: 2026-02-28

---
# SKILL: architect

---
name: Architect
description: Architectural decision-making workflow using tournament-based proposal generation and ranking. Generates proposals from multiple LLM providers (google, openai, xai) via llmx unified CLI, ranks them via tournament evaluation, optionally refines with feedback loops, and records decisions as ADRs. Use when exploring architectural alternatives, comparing implementation approaches, or making significant design decisions. Requires API keys, Python 3.10+.
---

# Architect Skill

Minimal-linear review workflow for architectural decision-making: **proposals → tournament → ADR**

## Quick Start

```bash
# Full cycle (generate → rank → optionally decide)
skills/architect/run.sh review "How should we implement event sourcing?"

# Step-by-step workflow with source context (RECOMMENDED)
cat proposal.md src/core/*.cljc | \
  skills/architect/run.sh propose "Should we add fourth kernel operation?"

skills/architect/run.sh rank <run-id>
skills/architect/run.sh decide <run-id> approve <proposal-id> "Best approach"
```

## Critical: Provide Full Context

**Lesson learned:** LLMs need complete context to understand architectural decisions correctly.

**Best prompt (95% success) - Include vision, overview, AND source:**

```bash
cat VISION.md \
    dev/overviews/AUTO-SOURCE-OVERVIEW.md \
    src/core/*.cljc | \
  skills/architect/run.sh propose "Review this architecture from first principles. \
  If the current design is already solid and elegant, say so - we don't want to \
  change unnecessarily."
```

**Good prompt (80% success):**

```bash
cat .architect/analysis/proposal.md \
    src/core/ops.cljc \
    src/plugins/selection/core.cljc | \
  skills/architect/run.sh propose "Evaluate this specific proposal"
```

**Bad prompt (0% success):**

```bash
skills/architect/run.sh propose "Should we add a fourth operation?"
# → LLMs guess what you mean, usually incorrectly
```

**Why this matters:**

- Generic descriptions → misunderstanding
- Source code context → accurate evaluation
- Vision/overview docs → understanding project goals and philosophy
- Explicit "if current is good, say so" → prevents unnecessary spiraling
- Explicit framing → focused analysis

**Context checklist:**

- [ ] Project vision/philosophy (VISION.md, CLAUDE.md, etc.)
- [ ] Architecture overview (AUTO-SOURCE-OVERVIEW.md, etc.)
- [ ] Relevant source code (use repomix for full context)
- [ ] Explicit evaluation criteria in prompt
- [ ] Permission to recommend "keep as-is"

## Commands

### `review` - Full Cycle

One-shot review: generate proposals → rank → present results

```bash
skills/architect/run.sh review "problem description"
```

**Options:**

- `--auto-decide` - Automatically approve if confidence > threshold
- `--confidence 0.85` - Confidence threshold for auto-decision (default: 0.85)
- `--constraints-file <path>` - Project constraints file (default: `.architect/project-constraints.md`)

### `propose` - Generate Proposals

Generate proposals from multiple LLM providers in parallel via llmx

```bash
skills/architect/run.sh propose "problem description"
```

**Options:**

- `--providers gemini,codex,grok,kimi2` - Specify providers (default: gemini,codex,grok)
- `--constraints-file <path>` - Project constraints file

Providers: `gemini`, `codex` (with reasoning-effort high), `grok`, `kimi2`

**Output:**

- `.architect/review-runs/{run-id}/run.json` - Run metadata
- `.architect/review-runs/{run-id}/proposal-{provider}.json` - Individual proposals
- Returns `run_id` for next steps

### `rank` - Rank Proposals

**NOTE:** Ranking uses simple fallback heuristic because tournament CLI is not available.

```bash
skills/architect/run.sh rank <run-id>
```

**Options:**

- `--auto-decide` - Auto-approve if confidence > threshold
- `--confidence 0.8` - Confidence threshold (default: 0.8)
- `--constraints-file <path>` - Project constraints file

**Output:**

- `.architect/review-runs/{run-id}/ranking.json` - Rankings with winner
- Shows next actions: approve, revise, or reject_all

**Limitation:** The Python script runs in subprocess and cannot access MCP tools.

**Better approach:** Use tournament MCP from Claude Code directly:

```bash
# After propose finishes, ask Claude Code to rank via tournament MCP
# Example: "Use tournament MCP to rank proposals from run <run-id>"
```

**Important distinction:**

- **Validation use case:** Same prompt → multiple providers → check consensus
  - If tournament returns INVALID (all theta=1.0), proposals are identical = validation success!
- **Comparison use case:** Different architectures → rank by quality
  - Requires semantically different proposals to compare

See `IMPROVEMENTS.md` for details on tournament integration and use cases.

### `refine` - Refine Proposal

Refine a proposal with feedback loops (max 5 rounds)

```bash
skills/architect/run.sh refine <run-id> <proposal-id> "feedback message"
```

**Options:**

- `--max-rounds 5` - Maximum refinement rounds (default: 5)

**Output:**

- `.architect/review-runs/{run-id}/spec.json` - Refined specification
- Validation results for each round

### `decide` - Record Decision

Record final decision as ADR (Architectural Decision Record)

```bash
skills/architect/run.sh decide <run-id> approve <proposal-id> "rationale"
skills/architect/run.sh decide <run-id> reject <proposal-id> "reason"
skills/architect/run.sh decide <run-id> defer "" "needs more research"
```

**Output:**

- `.architect/review-runs/{run-id}/adr-{run-id}.md` - Decision record
- Logs to `.architect/review-ledger.jsonl`

## Configuration

### LLM Providers

**Working models (2025-11-07):**

- `gemini-3.1-pro-preview`, `gpt-5-pro`, `grok-4-latest`, `kimi-k2-thinking`, `claude-sonnet-4-5`

**Gotchas:**

- `--reasoning-effort high` only works with OpenAI (gpt-5-pro)
- Model names: hyphens not dots (`claude-sonnet-4-5` not `4.5`)
- subprocess: Use `input=prompt`, NOT `shell=True` (breaks with parentheses)
- gpt-5-pro requires `--temperature 1`

### Tournament Settings

**Gotcha:** Judge names ≠ llmx model names

- llmx: `gemini-3.1-pro-preview` (hyphens, dots)
- tournament judges: `gemini25-pro` (no dots, compact)

**Available judges:** `gpt5-pro`, `gemini25-pro`, `grok-4`, `claude-4.5`, `kimi-k2-thinking`

Default: `["gemini25-pro", "claude-4.5"]`, max_rounds=3

### Workflow Settings

| Setting           | Default | Description                       |
| ----------------- | ------- | --------------------------------- |
| Proposal Count    | 3       | Generate from 3 providers         |
| Auto-decide       | false   | Require human approval by default |
| Refine Max Rounds | 5       | Maximum refinement iterations     |

## Evaluation Criteria

Rankings prioritize (in order):

1. **Simplicity** (HIGHEST) - Solo dev can understand/debug easily
2. **Debuggability** - Observable state, clear errors, REPL-friendly
3. **Flexibility** - Can skip stages, run tools independently
4. **Provenance** - Trace proposal → spec → implementation
5. **Quality gates** - Catch bad specs before implementation

Red flags:

- Infinite refinement loops
- Hidden automation
- Complex orchestration (hard to debug when stuck)
- Tight coupling (can't run stages independently)
- Over-engineering (10+ agents, dynamic planning)

## File Structure

All outputs go to `.architect/`:

```
.architect/
├── review-runs/{run-id}/      # Architect workflows
│   ├── run.json              # Metadata
│   ├── proposal-google.json  # Proposals from each provider
│   ├── proposal-openai.json
│   ├── proposal-xai.json
│   ├── ranking.json          # Tournament results
│   ├── spec.json            # Refined spec (if refined)
│   └── adr-{run-id}.md      # Decision record
├── reports/{research-id}/     # Research reports
├── review-ledger.jsonl        # Append-only provenance log
└── project-constraints.md     # Project-specific constraints
```

## Requirements

**CLI Tools:**

- `llmx` - Unified LLM CLI for all providers (google, openai, xai)
- `tournament-mcp` - Tournament evaluation (optional, uses fallback if unavailable)

**API Keys:**

- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `XAI_API_KEY`

**Python:**

- Python 3.10+
- No external dependencies (uses stdlib only)

## Examples

### Explore Multiple Approaches

```bash
# Generate proposals from all providers
skills/architect/run.sh propose "How should we implement undo/redo?"

# Review proposals (stored in .architect/review-runs/{run-id}/)
cat .architect/review-runs/{run-id}/proposal-*.json

# Rank them
skills/architect/run.sh rank {run-id}

# Decide
skills/architect/run.sh decide {run-id} approve {winner-id} "Clear and simple"
```

### Quick Decision

```bash
# Full cycle with auto-decision if confidence > 85%
skills/architect/run.sh review "State management approach" --auto-decide --confidence 0.85
```

### Refine Before Deciding

```bash
# Generate and rank
skills/architect/run.sh propose "API design patterns"
skills/architect/run.sh rank {run-id}

# Refine winner with feedback
skills/architect/run.sh refine {run-id} {winner-id} "Add error handling examples"

# Then decide
skills/architect/run.sh decide {run-id} approve {winner-id} "Complete after refinement"
```

### With Project Constraints

```bash
# Create constraints file
cat > .architect/project-constraints.md <<EOF
# Project Constraints

## Hard Requirements
- ClojureScript only
- REPL-friendly (no hidden state)
- Event sourcing architecture

## Soft Preferences
- Prefer core.async over callbacks
- Minimize dependencies
EOF

# Use constraints in review
skills/architect/run.sh review "How to handle async operations?" \
  --constraints-file .architect/project-constraints.md
```

## Integration

### With Tournament-MCP

The skill can use tournament-mcp for ranking when called from Claude Code:

```bash
# Generate proposals
skills/architect/run.sh propose "problem description"

# Then ask Claude Code to rank them
# "Use tournament MCP to rank proposals from run <run-id>"
```

**Two use cases:**

1. **Validation:** Same prompt, multiple providers → check consensus (INVALID = good!)
2. **Comparison:** Different architectures → rank by quality

### With Research Skill

Combine with research for comprehensive analysis:

```bash
# Research existing approaches
skills/research/run.sh explore re-frame "state management patterns"

# Generate proposals informed by research
skills/architect/run.sh propose "State management: re-frame vs reagent"
```

### Utility Commands

```bash
# List all review runs
skills/architect/run.sh list

# Show run details
skills/architect/run.sh show <run-id>

# View provenance ledger
skills/architect/run.sh ledger
```

## Storage Paths

| Path                             | Contents                       |
| -------------------------------- | ------------------------------ |
| `.architect/review-runs/`        | Individual review workflows    |
| `.architect/adr/`                | Architectural Decision Records |
| `.architect/review-ledger.jsonl` | Append-only provenance log     |
| `.architect/specs/`              | Refined specifications         |

## Templates

| Template | Path                              | Use                    |
| -------- | --------------------------------- | ---------------------- |
| ADR      | `data/templates/adr-template.md`  | Decision records       |
| Spec     | `data/templates/spec-template.md` | Refined specifications |

## Troubleshooting

**No API keys:**

- Set `GEMINI_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY` in `.env`
- Or export in shell: `export GEMINI_API_KEY="your-key"`

**Tournament-mcp not found:**

- Ranking will use simplified comparison mode
- Install tournament-mcp for full tournament evaluation

**Empty proposals:**

- Check API key validity
- Check CLI tool is in PATH: `which llmx`
- Check `.env` is sourced

**Run not found:**

- Verify run ID: `ls .architect/review-runs/`
- Check file exists: `cat .architect/review-runs/{run-id}/run.json`

**Python command not found:**

- Install Python 3.10+ or uv
- Skill auto-detects: uv > python3 > python

## Resources (Level 3)

- `run.sh` - Main CLI wrapper
- `lib/architect.py` - Python implementation
- `data/templates/` - ADR and spec templates
- `.architect/` - All outputs and logs
- `test-variant-a.sh` - Test script for variant-a prompts
- `GPT5_IMPROVEMENTS.md` - GPT-5 integration notes

## See Also

- Project docs: `../../CLAUDE.md#agent-skills-overview`
- GPT-5 prompting: `../gpt5-prompting/SKILL.md`
- Research skill: `../research/SKILL.md`
- Tournament MCP: `~/Projects/tournament-mcp/`


## Companion: GPT5_IMPROVEMENTS.md
# GPT-5 Prompting Improvements for Architect Skill

Based on `skills/gpt5-prompting/SKILL.md` best practices.

## Summary

The architect skill currently works well but could benefit from GPT-5 prompting best practices:

1. **API-first integration** (instead of CLI)
2. **Clearer instruction hierarchy** (MUST vs SHOULD)
3. **Better evaluation prompts** (explicit scoring, no contradictions)

## Changes Recommended

### 1. Migrate to API-first (providers.py)

**Current:** Uses `codex exec` CLI for all calls
**Issue:** CLI is slower, less reliable, harder to test
**Fix:** Use OpenAI SDK with CLI fallback

**See:** `skills/architect/lib/providers_api.py` for implementation

**Benefits:**

- Type-safe structured outputs (can use PydanticAI)
- Better error handling
- Faster (no subprocess overhead)
- Easier to test

**Migration path:**

```python
# Option 1: Drop-in replacement (try API, fall back to CLI)
import providers_api as providers

# Option 2: Gradual migration
from providers_api import call_codex  # Uses API
from providers import call_gemini, call_grok  # Keep CLI for now
```

### 2. Improve Proposal Generation Prompts

**Current issues:**

- All instructions sound equally important
- No clear MUST vs SHOULD hierarchy
- Missing explicit requirements

**Fixed in `providers_api.py`:**

```python
system_prompt = """You are an architectural advisor for solo developers.

MUST (hard requirements):
- Focus on simplicity over cleverness
- Debuggability is critical (observable state, clear errors)
- Solutions must be REPL-friendly (easy to test interactively)
- Avoid hidden automation or complex orchestration

SHOULD (preferences):
- Prefer explicit over implicit
- Minimize dependencies
- Document tradeoffs clearly
"""

user_prompt = f"""Generate an implementation proposal for: {description}

REQUIRED sections:
1. Core approach (2-3 sentences explaining fundamental strategy)
2. Key components and their responsibilities
3. Data structures and storage choices
4. Pros and cons (be honest about tradeoffs)
5. Red flags to watch for during implementation
"""
```

**Key improvements:**

- Clear MUST vs SHOULD separation
- REQUIRED sections (not optional)
- Explicit about what's needed

### 3. Improve Evaluation Prompt (architect.py)

**Current (lines 173-192):**

- Good priorities listed
- Red flags identified
- But: No explicit scoring instructions
- But: No tie-breaking rules
- But: Vague "judge which is best"

**Improved version in `evaluation_prompt.md`:**

```python
eval_prompt = f"""You are evaluating proposals for a solo developer.

Problem: {run_data.get('description')}

## MUST prioritize (in order):

1. **Simplicity** (HIGHEST) - Solo dev can understand/debug easily
2. **Debuggability** - Observable state, clear errors, REPL-friendly
3. **Flexibility** - Can skip stages, run tools independently
4. **Provenance** - Trace proposal → spec → implementation
5. **Quality gates** - Catch bad specs before implementation

## MUST reject if any:

- Infinite refinement loops
- Hidden automation
- Complex orchestration
- Tight coupling
- Over-engineering (10+ agents)

## Scoring instructions:

For EACH criterion (1-5):
- Score both proposals: 0.0 (terrible) to 10.0 (excellent)
- Use FULL range - don't cluster around 5.0
- Justify with specific evidence

Verdict MUST be consistent with scores:
- Calculate average across all 5 criteria
- Choose higher average
- If tie (< 0.5 difference), choose SIMPLER

Judge which proposal best fits these priorities.
"""
```

**Key improvements:**

- Explicit 0-10 scoring per criterion
- "Use FULL range" (GPT-5 tends to cluster without this)
- Clear tie-breaking rule
- Verdict must match scores (no contradictions)

## Implementation Plan

### Phase 1: Improve Prompts (Low Risk)

1. Update `providers.py` with MUST/SHOULD hierarchy
2. Update evaluation prompt in `architect.py`
3. Test with a few proposal runs
4. Compare quality before/after

**Effort:** ~30 minutes
**Risk:** Low (just prompt changes)
**Impact:** Better proposal quality, clearer evaluation

### Phase 2: Add API Integration (Medium Risk)

1. Install OpenAI SDK: `pip install openai`
2. Rename `providers.py` → `providers_cli.py`
3. Rename `providers_api.py` → `providers.py`
4. Test end-to-end workflow
5. Keep CLI fallback for when API unavailable

**Effort:** ~1 hour (includes testing)
**Risk:** Medium (code changes, new dependency)
**Impact:** Faster, more reliable, type-safe

### Phase 3: Structured Outputs (Optional)

Once API integrated, can use PydanticAI for structured proposals:

```python
from pydantic import BaseModel, Field
from pydantic_ai import Agent

class Proposal(BaseModel):
    approach: str = Field(description="Core approach (2-3 sentences)")
    components: list[str]
    data_structures: str
    pros: list[str]
    cons: list[str]
    red_flags: list[str]

agent = Agent(
    "openai:gpt-5-codex",
    output_type=Proposal,
    system_prompt="..."
)

result = await agent.run(description)
# result.output is validated Proposal object
```

**Effort:** ~2 hours
**Risk:** Medium (architectural change)
**Impact:** Type safety, validation, better error handling

## Testing Checklist

Before deploying changes:

- [ ] Run `skills/architect/run.sh propose "test problem"`
- [ ] Verify all 3 providers (gemini, codex, grok) work
- [ ] Run `skills/architect/run.sh review "test problem"`
- [ ] Check proposal quality (MUST/SHOULD followed?)
- [ ] Check ranking makes sense (scores use full range?)
- [ ] Test fallback (rename `openai` to break API, verify CLI works)

## References

- **GPT-5 Prompting Skill:** `skills/gpt5-prompting/SKILL.md`
- **API Examples:** `skills/gpt5-prompting/examples/api-integration.py`
- **Pitfalls Catalog:** `skills/gpt5-prompting/data/common-pitfalls.edn`

## Questions?

- **Why API over CLI?** More reliable, type-safe, faster, easier to test. CLI is legacy.
- **Why MUST vs SHOULD?** GPT-5 wastes reasoning tokens on contradictions. Clear hierarchy prevents this.
- **Why explicit scoring?** GPT-5 clusters scores around 5.0 without guidance. "Use FULL range" fixes this.
- **Do we lose anything?** No - CLI fallback kept. Only gains in reliability and quality.


## Companion: IMPROVEMENTS.md
# Architect Skill Improvements

**Date:** 2025-10-24
**Based on:** Real usage during plugin architecture evaluation

## Summary of Issues Found

### 1. Tournament Integration is Broken

**Problem:** Uses subprocess call to `tournament` CLI which fails every time

```python
subprocess.run(["tournament", "compare", ...])  # Always exits with status 1
```

**Solution:** Use tournament MCP server instead (already configured in `.mcp.json`)

```python
# Should use Claude Code's MCP tool:
mcp__tournament__compare_items(left=prop1, right=prop2, evaluation_prompt=...)
```

**Impact:** All ranking fell back to simple heuristic instead of proper tournament evaluation

**Update (2025-10-24):** Tournament MCP testing revealed an important distinction:

- **Validation use case:** Same prompt → multiple instances → check consensus (what we did)
  - Result: All 5 agreed on dual-multimethod design (INVALID status = unanimous agreement)
  - Tournament correctly returned INVALID because proposals were semantically identical
- **Comparison use case:** Different architectures → rank by quality (what tournament is for)
  - Requires: Proposals with meaningful architectural differences
  - Example: Compare dual-multimethod vs single-multimethod vs direct dispatch

**Lesson:** When proposals come from same prompt, tournament will (correctly) show no difference. Use tournament to compare DIFFERENT architectural approaches, not to validate consensus.

### 2. Prompt Construction Needs Improvement

**What I learned:**

- LLMs need VERY explicit context about what they're evaluating
- First attempts confused `:update-meta` with ClojureScript's metadata system
- Needed to pipe full source code to get correct understanding
- Name "update-meta" triggered wrong associations

**Improvements:**

1. **Always provide source code context** when evaluating architectural decisions
2. **Name operations carefully** - avoid terms with existing language meanings
3. **Be explicit about "ANALYZE THIS vs DESIGN NEW"** - LLMs default to proposing solutions
4. **Front-load constraints** - mention "event sourcing", "3-op kernel", etc. early

**Example of what works:**

```markdown
# YOU ARE EVALUATING AN EXISTING SYSTEM (not designing new)

## Current 3-Operation Kernel

[source code here]

## The Proposal: Add :assoc-path (not :update-meta)

[explicit description]

## Your Task: Honest Evaluation

[specific questions]
```

### 3. Insufficient Context on First Attempts

**Iterations required:**

1. First try: Generic proposal → LLMs misunderstood completely
2. Second try: Better prompt → Still misunderstood (wrong problem space)
3. Third try: Full source code piped → FINALLY understood

**Lesson:** Don't be stingy with context. Pipe relevant source files directly.

### 4. Multiple Provider Instances Not Supported

**Issue:** Original code created ID collisions when running 5x codex

```python
proposal_id = f"{run_id}-{provider_name}"  # Collision!
```

**Fixed:** Added instance numbering

```python
provider_counts[name] = provider_counts.get(name, 0) + 1
proposal_id = f"{run_id}-{provider_name}-{instance}"
```

**Now works:** `--providers codex,codex,codex,codex,codex`

## Recommended Changes

### Priority 1: Fix Tournament Integration

**File:** `skills/architect/lib/architect.py`

**Current (broken):**

```python
# Check if tournament CLI is available
TOURNAMENT_AVAILABLE = shutil.which("tournament") is not None

# ... later ...
result = subprocess.run(["tournament", "compare", ...])
```

**Proposed:**

```python
# NO subprocess calls - use MCP tool from Claude Code context
def rank_via_tournament_mcp(proposals, evaluation_prompt):
    """
    Rank proposals using tournament MCP server.
    NOTE: This function is called FROM Claude Code, which has mcp__tournament__ tools.
    """
    # Build items dict
    items = {p["id"]: p["content"] for p in proposals}

    # NOTE: This would need to be called from Claude Code context, not subprocess
    # The architect.py script runs via llmx/subprocess, so it CAN'T call MCP tools
    #
    # SOLUTION: Return a signal that Claude Code should handle ranking
    return {"status": "needs_mcp_ranking", "items": items, "prompt": evaluation_prompt}
```

**BETTER SOLUTION:** Architect skill should OUTPUT ranking request, Claude Code calls MCP:

```python
# In architect.py
def rank_proposals(run_id, ...):
    # Don't try to rank here - return data for Claude Code to rank
    return {
        "needs_ranking": True,
        "items": {p["id"]: p["content"] for p in proposals},
        "evaluation_prompt": eval_prompt
    }
```

```python
# In skills/architect/run.sh
# After Python returns, check if needs_ranking
if result.get("needs_ranking"):
    echo "Rankings requires MCP tournament tool..."
    echo "Run this from Claude Code:"
    echo "  mcp__tournament__compare_multiple(...)"
fi
```

**Actually:** Since architect runs in subprocess, it CAN'T access MCP tools. Options:

1. **Keep fallback heuristic** (current, works but suboptimal)
2. **Have Claude Code call tournament MCP separately** after architect finishes
3. **Rewrite architect as Claude Code native tool** (big refactor)

**Recommended:** Option 2 - Document that ranking is separate step

### Priority 2: Improve Prompt Template

**File:** `skills/architect/lib/providers.py`

**Add source code inclusion helper:**

````python
def format_proposal_prompt(description, constraints, source_files=None):
    """
    Build proposal prompt with optional source code context.

    Args:
        description: Problem description
        constraints: Project constraints
        source_files: Optional dict of {filename: content}
    """
    prompt_parts = [
        f"<role>{role_text}</role>",
        format_constraints_prompt(constraints),
        f"<task>{description}</task>"
    ]

    if source_files:
        context = "\n\n".join(
            f"## {filename}\n```clojure\n{content}\n```"
            for filename, content in source_files.items()
        )
        prompt_parts.insert(1, f"<source_context>\n{context}\n</source_context>")

    return "\n\n".join(prompt_parts)
````

**Add explicit framing:**

```python
EVALUATION_FRAME = """
YOU ARE EVALUATING AN EXISTING SYSTEM.

This is NOT a greenfield design. You have a working system and are evaluating
a specific proposal for modification.

Your task: Provide honest assessment of tradeoffs, NOT propose alternatives.
"""
```

### Priority 3: Update Documentation

**File:** `skills/architect/SKILL.md`

**Add section on context:**

````markdown
## Providing Context

Architect skill works best with FULL context. Options:

### Pipe Source Files

```bash
cat proposal.md src/core/*.cljc | skills/architect/run.sh propose "..."
```
````

### Use --source-dir (TODO: not implemented yet)

```bash
skills/architect/run.sh propose "..." --source-dir src/
```

### Learnings:

- **Generic prompts → generic/wrong answers**
- **Pipe relevant source code → accurate understanding**
- **Name operations carefully** (avoid language keyword collisions)

````

**Add section on ranking:**
```markdown
## Ranking Limitations

The `rank` command tries to use tournament evaluation but falls back to
simple heuristics because:
- Architect runs in subprocess (no MCP access)
- Tournament CLI not available

**Workaround:**
After `propose`, manually call tournament MCP from Claude Code:
```clojure
(mcp__tournament__compare_multiple
  items {"prop-1" "content..." "prop-2" "..."}
  evaluation_prompt "...")
````

Then use ranking to make `decide` call.

````

### Priority 4: Phase Out Outdated Instructions

**Files to update:**

1. **`skills/architect/SKILL.md`** - Main docs
   - Remove references to features not implemented
   - Add learnings from real usage
   - Document MCP ranking limitation

2. **`skills/architect/run.sh`** - Help text
   - Update examples to show source piping
   - Note ranking limitations
   - Add troubleshooting section

3. **`.architect/project-constraints.md`** - Constraints file
   - Update with learnings (pipe source, name carefully)
   - Add examples of good vs bad prompts

4. **`dev/claude-skills-howto.md`** - If exists
   - Update architect skill usage examples
   - Show real session from today

### Priority 5: Add Post-Session Analysis

**New file:** `skills/architect/lib/analyze_run.py`

```python
def analyze_run(run_id):
    """
    Analyze a completed architect run for quality/learnings.

    Reports:
    - Were proposals diverse or repetitive?
    - Did they understand the problem correctly?
    - Quality metrics (length, specificity, etc.)
    - Suggested improvements for next run
    """
    run_data = storage.load_run(run_id)
    proposals = run_data["proposals"]

    # Simple heuristics
    lengths = [len(p["content"]) for p in proposals]
    similarities = compute_jaccard_similarities(proposals)

    return {
        "diversity": 1.0 - avg(similarities),
        "avg_length": avg(lengths),
        "understood_correctly": detect_misunderstandings(proposals),
        "recommendations": generate_recommendations(run_data)
    }
````

## Implementation Plan

1. ✅ **Document issues** (this file)
2. **Fix provider instances** (already done in session)
3. **Update SKILL.md** with learnings
4. **Add source piping docs**
5. **Note tournament MCP limitation**
6. **Create improved prompt template**
7. **Add troubleshooting guide**

## Learnings for Future Skills

### What Worked

- **Iterative refinement** - Run, analyze, improve prompt, run again
- **Full source code context** - Piping actual code files was critical
- **Explicit framing** - "YOU ARE EVALUATING" vs "DESIGN"
- **Multiple providers** - 5 independent opinions better than 1

### What Didn't Work

- **Generic prompts** - Led to misunderstanding
- **Assuming LLMs infer correctly** - They don't, be explicit
- **Tournament CLI fallback** - Subprocess can't access MCP tools
- **Stingy with context** - Give them everything relevant

### Patterns to Reuse

- **Three-iteration pattern**: Generic → Better prompt → Full context
- **Unanimous agreement = validated** - When all 5 agree, trust it
- **Misunderstanding = prompt problem** - Not model stupidity
- **Name collision detection** - Check for language keyword conflicts

## Questions for Future

1. **Should architect be native Claude Code tool?** (vs subprocess)
   - Pro: Could use MCP tournament directly
   - Con: Loses independence from Claude Code

2. **Should we cache source context?**
   - Large source files repeated across providers
   - Could template with references

3. **Should we add auto-context detection?**
   - Detect mentioned files (src/core/ops.cljc)
   - Auto-include in prompt

4. **Should proposals be shorter?**
   - Current: 3-5k chars each
   - Could ask for structured bullets instead

## References

**Runs completed today:**

- `7102cb63-7401-4b80-ba86-83abb519b54b` - Plugin expressivity (misunderstood)
- `0d7ea747-2898-4e65-b910-749f96661e2e` - :update-meta op (misunderstood)
- `6c6159a7-ca25-4f4c-90cb-9da1acd89711` - :assoc-path op (understood!)
- `7fd9ac2a-7bfe-4e1a-9037-39b6d177f888` - Intent router (understood + approved!)

**Success rate:**

- First 2 runs: Completely misunderstood (0%)
- Last 2 runs: Perfectly understood (100%)
- Difference: Full source code + explicit framing

**Key insight:** Context quality matters more than model choice.

---
# SKILL: code-research

---
name: Research Best-Of Repositories
description: Query 40+ Clojure/ClojureScript reference projects from ~/Projects/best/* using repomix + llmx. Find patterns, idioms, architectural examples, and code comparisons. Triggers on research, best-of, patterns, inspiration, code examples. Requires llmx CLI, repomix, and API keys (GEMINI_API_KEY, OPENAI_API_KEY, XAI_API_KEY).
---

# Research Workflow

## Prerequisites

**Tools:**

- `repomix` - Repository bundling (must be in PATH)
- `llmx` - Unified LLM CLI (100+ providers)

**Environment:**

```bash
# Required API keys in .env
GEMINI_API_KEY=your-key
OPENAI_API_KEY=your-key
XAI_API_KEY=your-key
```

**Data:**

- 40+ curated projects in `~/Projects/best/`
- See `data/repos.edn` for complete list with metadata

## Quick Start

```bash
# Query a small repo
repomix ~/Projects/best/malli --copy --output /dev/null | \\
  llmx --provider google --model gemini-3.1-pro-preview "How does schema composition work?"

# Query large repo (focused)
repomix ~/Projects/best/clojurescript/src/main/clojure/cljs \\
  --include "compiler.clj,analyzer.cljc" --copy --output /dev/null | \\
  llmx --provider openai --model gpt-5-codex "Explain macro expansion"

# Compare projects
repomix ~/Projects/best/re-frame/src --include "**/subs.cljs" --copy && \\
repomix ~/Projects/best/electric/src --include "**/reactive.clj*" --copy | \\
  llmx --provider openai --model gpt-5-codex "Compare reactive patterns"
```

## When to Use

Use this skill when you need to:

- Find idiomatic Clojure patterns
- Research architectural approaches
- Understand library usage patterns
- Compare implementations across projects
- Validate design decisions against production code

## Available Projects

**Core Clojure:**
clojure, clojurescript, core.async, core.logic, core.typed

**Data & State:**
datascript, datalevin, re-frame, specter, meander

**UI & Reactive:**
replicant, electric, javelin, reagent

**Web & API:**
ring, compojure, reitit, pathom3

**Build & Dev:**
shadow-cljs, clerk, portal, component

See `data/repos.edn` for complete list (LOC, languages, descriptions).

## Model Selection

| Provider | Model          | Use For                                   | Cost   | Speed  |
| -------- | -------------- | ----------------------------------------- | ------ | ------ |
| google   | gemini-3.1-pro-preview | High-token queries, large repos, sessions | Medium | Medium |
| openai   | gpt-5-codex    | Code review, architecture, taste          | High   | Slow   |
| xai      | grok-4-latest  | Quick queries, fallback                   | Medium | Medium |

**Critical Policy:** Never use gemini-flash, gpt-4o, or gpt-4-turbo for Skills work. Token savings from progressive disclosure outweigh model costs.

## Query Patterns

### Pattern 1: Small Repo (<10MB)

For projects like `aero`, `environ`, `malli`:

```bash
# 1. Extract full src + README
repomix ~/Projects/best/malli --copy --output /dev/null \\
  --include "src/**,README.md"

# 2. Query with gemini
pbpaste | llmx --provider google --model gemini-3.1-pro-preview \\
  "YOUR_QUESTION"
```

### Pattern 2: Large Repo (>50MB) Focused Query

For projects like `clojurescript`, `athens`, `logseq`:

```bash
# 1. Explore structure first
tree -L 3 -d ~/Projects/best/clojurescript
tokei ~/Projects/best/clojurescript

# 2. Zoom into specific subdirectories
repomix ~/Projects/best/clojurescript/src/main/clojure/cljs \\
  --include "compiler.clj,analyzer.cljc" --copy --output /dev/null

# 3. Query with codex (high reasoning)
pbpaste | llmx --provider openai --model gpt-5-codex \\
  "YOUR_QUESTION"
```

### Pattern 3: Multi-Project Comparison

```bash
# Extract from multiple projects
repomix ~/Projects/best/re-frame/src --include "**/subs.cljs" \\
  --copy --output /tmp/re-frame.txt

repomix ~/Projects/best/electric/src --include "**/reactive.clj*" \\
  --copy --output /tmp/electric.txt

# Compare patterns
cat /tmp/re-frame.txt /tmp/electric.txt | \\
  llmx --provider openai --model gpt-5-codex \\
  "Compare reactive state patterns"
```

## Common Query Templates

### Event Sourcing

**Question:** "How is event sourcing implemented? Show event log structure, transaction handling, and replay mechanisms."
**Relevant projects:** datascript, datalevin, electric

### Reactive State

**Question:** "How is reactive state managed? Show subscription patterns, state propagation, and performance optimizations."
**Relevant projects:** re-frame, electric, javelin, reagent

### Macro Patterns

**Question:** "What are common macro patterns? Show code generation, compile-time optimization, and DSL implementation."
**Relevant projects:** clojurescript, core.async, specter

### API Design

**Question:** "How are APIs designed for composability? Show function composition, middleware patterns, and extension points."
**Relevant projects:** ring, compojure, reitit, pathom3

### Testing Patterns

**Question:** "What testing patterns are used? Show test organization, fixture management, and property-based testing."
**Relevant projects:** clojure, datascript, malli

### Build Workflow

**Question:** "How is the build workflow organized? Show compilation, optimization, and hot-reload setup."
**Relevant projects:** shadow-cljs, clerk, clojurescript

## Repository Size Thresholds

- **< 10 MB:** Extract full src/ directory
- **50-200 MB:** Use focused paths (specific subdirs/files)
- **> 200 MB:** Multiple focused queries recommended

Check size with: `du -sh ~/Projects/best/{project}`

## Environment Variables

**Optional configuration:**

```bash
# Override default model
export RESEARCH_DEFAULT_MODEL="gemini-3.1-pro-preview"

# Set timeouts (seconds)
export REPOMIX_TIMEOUT=30
export LLM_TIMEOUT=120
```

## Tips & Best Practices

1. **Start with structure exploration** - Use `tree` and `tokei` before extracting
2. **Be specific with includes** - `--include "pattern"` reduces tokens
3. **Choose the right model** - gemini for breadth, codex for depth
4. **Validate outputs** - Check file sizes (`wc -l`, `du -h`)
5. **Handle errors gracefully** - Check stderr for repomix failures

## Common Pitfalls

- **Empty output:** repomix failed silently, check stderr
- **Token limits:** Query too large, use focused includes
- **API timeouts:** Use faster model or retry
- **Stale data:** Regenerate repos.edn with `docs/research/sources/update-repos.sh`

## Troubleshooting

**"No such file or directory"**

- Verify: `ls ~/Projects/best/{project}`
- Check `data/repos.edn` for correct path

**"Command timed out"**

- Use faster model: `--model gemini-3-flash-preview`
- Break query into smaller parts

**"Empty response"**

- Check API keys: `env | grep -E "(GEMINI|OPENAI|XAI)_API_KEY"`
- Source .env: `source .env`

## Resources (Level 3)

- `data/repos.edn` - Project metadata (names, LOC, languages, trees)
- `run.sh` - CLI wrapper for common workflows (optional)
- `examples/` - Usage examples:
  - `example-quick-query.sh` - Fast single-project lookup
  - `example-comparison.sh` - Cross-project pattern analysis

## See Also

- Project docs: `../../CLAUDE.md#research-workflow`
- LLM CLI guide: `../../CLAUDE.md#llm-provider-clis`
- Repomix docs: `~/Projects/best/repomix/README.md`

---
# SKILL: competing-hypotheses

---
name: competing-hypotheses
description: Analysis of Competing Hypotheses (ACH). Use when investigating any entity, anomaly, root cause, or claim that could have multiple explanations — fraud vs error, bug vs design, correlation vs causation. Dispatches parallel agents with opposing hypotheses, then synthesizes the surviving explanation. Based on Richards Heuer's CIA methodology.
argument-hint: [entity, anomaly, or claim to evaluate]
---

# Analysis of Competing Hypotheses (ACH)

You are evaluating a claim, entity, or anomaly. Your job is NOT to confirm the most likely explanation. Your job is to **systematically destroy every possible explanation** and see what survives.

## Core Principle

> "Truth is whatever is left standing after you have relentlessly tried to destroy every possible explanation." — Richards Heuer, *Psychology of Intelligence Analysis*

Evidence consistent with multiple hypotheses is **diagnostically useless**. Only evidence that **eliminates** a hypothesis has value.

## The Process

### Step 1: Generate Hypotheses

For the target `$ARGUMENTS`, generate at minimum THREE competing hypotheses:

| Hypothesis | Description |
|------------|-------------|
| **H1: Wrongdoing** | The anomaly reflects intentional fraud, abuse, or corruption |
| **H2: Legitimate** | There is a lawful, non-fraudulent explanation |
| **H3: Artifact** | The anomaly is a data error, reporting change, or measurement artifact |

Add domain-specific sub-hypotheses as needed.

### Step 1.5: Complexity Gate

Before dispatching agents, assess: can a single agent resolve this with A1/A2-rated sources? If yes, skip ACH — just answer directly. ACH is for genuinely ambiguous cases where the single-agent success rate is below ~45%. Don't use a cannon for a nail.

### Step 2: Dispatch Competing Agents

Launch **three parallel agents** (Task tool with subagent_type="general-purpose"). **Use different models when available** — same-model debate is a martingale for correctness (ACL 2025, arXiv:2508.17536). Different models have different failure modes, biases, and blind spots:

- **Agent A — Prosecution** (prefer Gemini — different training biases): Search for enforcement history, ownership anomalies, financial pressure, fraud signatures. Tag all claims [SOURCE: url] or [INFERENCE].
- **Agent B — Defense** (prefer GPT — different blind spots): Search for policy changes, industry trends, M&A, comparable clean entities. Find the BEST innocent explanation.
- **Agent C — Artifact Investigator** (Claude — strong at structured analysis): Search for data reporting changes, known data issues, system migrations, whether anomaly appears in multiple independent sources.

If multi-model dispatch isn't available, same-model agents still have value via the diagnosticity matrix — but the adversarial pressure is weaker.

### Step 3: Build the Diagnosticity Matrix

```
| Evidence                  | H1 | H2 | H3 |
|---------------------------|:--:|:--:|:--:|
| [evidence item]           | C  | I  | N  |

C = Consistent, I = Inconsistent, N = Neutral
```

**Key rule:** Evidence that is C/C/C has **zero diagnostic value**. Focus on evidence that eliminates hypotheses.

### Step 4: Score and Synthesize

**Recitation first:** Before scoring, each agent restates its top 3 most diagnostic evidence items verbatim. This combats lost-in-the-middle effects when synthesizing across agents (Du et al., EMNLP 2025: +4% on RULER, training-free, model-agnostic).

Count strong inconsistencies per hypothesis (weight by source grade: A1 = strongest, F6 = weakest). The surviving hypothesis has the fewest strong inconsistencies.

```markdown
## ACH Result: [Entity/Anomaly]

**Surviving Hypothesis:** [H1/H2/H3 + description]
**Confidence:** [0-100]%
**Key Discriminating Evidence:**
- [Most diagnostic item] — eliminates [H2/H3] because [reason]

**Residual Uncertainty:**
- [What evidence would flip the conclusion]
- [What data we don't have]
```

### Step 5: Red Team (recommended for high stakes)

Dispatch a fourth agent to ATTACK the surviving conclusion: find missed evidence, alternative explanations, source quality weaknesses, what a defense attorney would argue.

## When NOT to Use

- Simple factual lookups
- Clearly confirmed findings with A1-rated sources
- Time-critical situations where speed > rigor

$ARGUMENTS

---
# SKILL: constitution

---
name: constitution
description: Elicit project goals, constitutional principles, and autonomy boundaries through structured questionnaire. Produces CONSTITUTION.md (operational principles) and GOALS.md (personal objectives). Use for any new project or to revisit existing constitutional decisions.
user-invocable: true
disable-model-invocation: true
---

# Constitutional Elicitation

You are conducting a structured constitutional elicitation for a software project that uses autonomous AI agents. Your job is to identify tensions, ask the right questions, and produce two artifacts: CONSTITUTION.md (how agents operate) and GOALS.md (what the human wants).

## Phase 1: Reconnaissance

Before asking any questions, explore the project thoroughly. Read every instruction file, rule, and configuration:

<exploration_checklist>
- CLAUDE.md (root + any subdirectories)
- .claude/rules/ (all files)
- .claude/settings.json (hooks)
- .claude/skills/ (skill definitions)
- .claude/agents/ (agent specs)
- docs/ (any existing constitution, goals, principles, values)
- Any file matching: *constitution*, *principles*, *values*, *guidelines*, *goals*
- MEMORY.md or any persistent memory files
</exploration_checklist>

Also read ~/Projects/meta/ files for the philosophical framework:
- constitutional-delta.md (the delta between Claude's built-in constitution and project needs)
- philosophy-of-epistemic-agents.md (epistemic foundations)
- frontier-agentic-models.md (what research says about agent reliability)
- agent-failure-modes.md (documented failure modes)

## Phase 2: Contradiction Detection

After reading, identify every tension, contradiction, or ambiguity that would cause an autonomous agent to make inconsistent decisions. Common tensions:

<tension_categories>
1. **Identity/Scope** — Is the project trying to be multiple things? Which identity wins when resources are scarce?
2. **Autonomy** — What can the agent do without asking? Where are the hard limits vs guidelines?
3. **Epistemics** — How are claims verified? What standard of evidence? When is multi-model review worth the cost?
4. **Adversarial stance** — How skeptical should the default be? Domain-dependent?
5. **Session architecture** — How are long tasks managed? Context decay? Document & Clear vs continuity?
6. **Self-improvement** — Can agents update their own rules? Which rules? What evidence standard?
7. **Feedback mechanisms** — How does the system know if it's getting better? What's the measurement?
8. **Cross-project** — Does this project share principles with other projects? How much divergence?
9. **Human-in-loop** — What exactly requires human approval vs auto-commit?
10. **Success criteria** — What does "working" look like in 12 months?
</tension_categories>

## Phase 3: Questionnaire

Generate a questionnaire with 12-16 questions, grouped by theme. Each question must:
- Identify a specific tension found in Phase 2 (not generic)
- Offer 3-4 concrete options (letter-coded for quick answers)
- Include "Something else: ___" as the last option
- Be answerable in one sentence

Question design principles:
- Reference specific files/lines where you found the contradiction
- Make options mutually exclusive and cover the realistic design space
- Front-load the most consequential questions (identity, scope, autonomy)
- End with "hard questions" that determine everything else (success criteria, enforcement priority)

## Phase 4: Synthesis

After the human answers, produce two documents:

### GOALS.md
<goals_template>
# Goals: What This System Is For

**Owner:** Human. Agent must not modify without explicit approval.

## Primary Mission
[What the system exists to do — one paragraph]

## Why This Domain
[Why this domain was chosen — fast feedback, falsifiability, personal interest]

## Target Domain
[Specific scope — market cap range, geography, sector, whatever constrains the search space]

## Success Metrics (12-Month)
[3-5 measurable outcomes]

## What's Explicitly Deferred
[Things the human decided NOT to do yet]

## Capital/Resource Deployment Philosophy
[How decisions become actions — outbox pattern, graduated autonomy, human gates]

*This document defines WHAT the system optimizes for. See CONSTITUTION.md for HOW it operates.*
</goals_template>

### CONSTITUTION.md
<constitution_template>
# Constitution: Operational Principles

**Human-protected.** Agent may propose changes but must not modify without explicit approval.

## The Generative Principle
[One sentence that derives all other principles. Must be falsifiable and measurable.]

## Constitutional Principles
[7-12 numbered principles. Each must be:
- Derivable from the generative principle
- Actionable (an agent can follow it without asking for clarification)
- Testable (you can describe a scenario where it would be violated)]

## Autonomy Boundaries
### Hard Limits (agent must not, without exception)
### Autonomous (agent should do without asking)
### Auto-Commit Standard
[When can the agent commit knowledge without human review?]

## Self-Improvement Governance
### What the Agent Can Change
### What Requires Human Approval
### Rules of Change
[Evidence standard for modifying rules]
### Rules of Adjudication
[How to determine if the system is working — metrics, review cadence]

## Self-Prompting Priorities (When Human Is Away)
[Ordered list of autonomous task priorities]

## Session Architecture
[Document & Clear, fresh context per task, turn limits, multi-model validation triggers]

*This document defines HOW the system operates. See GOALS.md for WHAT it optimizes toward.*
</constitution_template>

## Key Research Constraints

These are empirically validated — apply to every constitution:

1. **Instructions alone = 0% reliable** (EoG, arXiv:2601.17915). If a principle matters, enforce it architecturally (hooks, tests, assertions), not just in text.
2. **Documentation helps +19 pts for novel knowledge, +3.4 for known APIs** (Agent-Diff, arXiv:2602.11224). Only document what the model doesn't already know.
3. **Consistency is flat over 18 months** (Princeton, r=0.02). Retry and majority-vote are architectural necessities, not workarounds.
4. **Simpler beats complex under stress** (ReliabilityBench, arXiv:2601.06112). ReAct > Reflexion under perturbations.
5. **Context degrades with length even with perfect retrieval** (Du et al., arXiv:2510.05381). 15-turn sessions with Document & Clear > 40-turn marathons.
6. **Text alignment =/= action alignment** (Mind the GAP, arXiv:2602.16943). Models refuse in text but execute via tools. Hooks are the enforcement mechanism.
7. **The generative principle concept** (Askell, arXiv:2310.13798): A single well-internalized principle derives all behavior better than 50 pages of rules.

## Prompting Notes (Model-Agnostic)

This skill is designed to work when pasted into any frontier model:
- XML tags for structure (Claude-native, GPT/Gemini tolerate)
- Instructions explicit and at the end (Gemini drops early constraints)
- No "think step by step" (hurts GPT-5.2 thinking mode)
- Options are letter-coded for quick human response
- Templates use concrete field names, not vague categories

---
# SKILL: debug-mcp-servers

---
name: debug-mcp-servers
description: Debug why MCP servers aren't loading in Claude Code. Use this when user reports MCPs not appearing in /mcp list despite being configured.
---

# Debug MCP Servers Not Loading

When MCP servers are configured but don't appear in `/mcp`, follow this systematic debugging process.

## Step 1: Check Current MCP Configuration

```bash
claude mcp list
```

This shows which MCPs are actually loaded and their connection status.

## Step 2: Verify MCP Configuration Files

Check both scopes where MCPs can be configured:

### User Scope (global, all projects)
```bash
cat ~/.claude.json | jq '.mcpServers'
```

### Project Scope (current project only)
```bash
cat .mcp.json
```

**Key insight**: Project-scoped MCPs in `.mcp.json` require approval or explicit enabling.

## Step 3: Check Local Settings Override

**THIS IS THE MOST COMMON ISSUE:**

```bash
cat .claude/settings.local.json
```

If this file contains:
```json
{
  "enableAllProjectMcpServers": false
}
```

**This blocks ALL .mcp.json servers from loading!**

**Fix:**
```bash
# Edit the file to set it to true, or remove the file entirely
```

Alternative locations to check:
- `.claude/settings.json` (project settings)
- User-level settings that might override

## Step 4: Verify Claude Code State

```bash
cat ~/.claude.json | jq '.projects["'$(pwd)'"]'
```

Look for:
- `enabledMcpjsonServers` - should be `null` or contain your server names
- `disabledMcpjsonServers` - should not contain your servers
- `disabledMcpServers` - should not contain your servers

## Step 5: Test MCP Prerequisites

For each MCP that's not loading:

### HTTP/SSE MCPs
```bash
curl -I <mcp-url>
```

Should return a valid HTTP response (405 is fine for MCP endpoints).

### Stdio MCPs
Check the command exists:
```bash
which <command>
# Example: which uv, which npx, etc.
```

Check any required directories:
```bash
ls -la /path/to/mcp/directory
```

Verify environment variables are set:
```bash
echo $REQUIRED_ENV_VAR
```

## Step 6: Check Environment Variable Expansion

If `.mcp.json` uses `${VARIABLE}` syntax:

```bash
# Verify variables are loaded in your shell
env | grep -E 'OPENAI_API_KEY|ANTHROPIC_API_KEY|GOOGLE_API_KEY'
```

**Common issue**: Environment variables need to be loaded BEFORE Claude Code starts.

Check shell config files:
- `~/.zshenv` (loaded first, best for env vars)
- `~/.zshrc` (loaded for interactive shells)
- `~/.bashrc` / `~/.bash_profile` (for bash)

## Step 7: Reset Project Approvals

If project-scoped MCPs need re-approval:

```bash
claude mcp reset-project-choices
```

Then restart Claude Code and approve the servers when prompted.

## Step 8: Verify Specific MCP Config

```bash
claude mcp get <server-name>
```

Shows:
- Scope (user, project, local)
- Connection status
- Configuration details
- Command/URL being used

## Common Issues & Solutions

### Issue: MCPs in .mcp.json don't load
**Root cause**: `.claude/settings.local.json` has `"enableAllProjectMcpServers": false`
**Solution**: Change to `true` or remove the file

### Issue: Environment variables not expanding
**Root cause**: Variables not set when Claude Code launches
**Solution**: Add variables to `~/.zshenv`, restart terminal AND Claude Code

### Issue: Duplicate MCP in user + project scope
**Root cause**: Same MCP name in both `~/.claude.json` and `.mcp.json`
**Solution**: Remove from one scope:
```bash
claude mcp remove <name> --scope user
# or
claude mcp remove <name> --scope project
```

### Issue: MCP shows as configured but "connecting..." forever
**Root cause**:
- Command doesn't exist or can't execute
- Network issues (for remote MCPs)
- Missing environment variables
- Incorrect command syntax

**Solution**: Test the command manually:
```bash
# For stdio MCP
<command> <args>

# For HTTP MCP
curl -I <url>
```

## MCP Configuration Hierarchy

1. **Enterprise/Managed** (highest priority, if configured)
2. **User scope** (`~/.claude.json`) - available in all projects
3. **Project scope** (`.mcp.json`) - requires approval/enablement
4. **Local scope** (user settings for specific project)

Settings at more specific levels override broader ones.

## Key Learnings

1. **Always check `.claude/settings.local.json` first** - this is the #1 blocker
2. **Project-scope MCPs require explicit enabling** - not automatic
3. **Environment variables must be loaded before Claude Code starts**
4. **Use `claude mcp list` and `claude mcp get` to verify** - don't trust files alone
5. **Test prerequisites independently** - verify commands exist, URLs respond, env vars are set

## Testing Checklist

Before declaring MCPs "should work":

- [ ] Run `claude mcp list` to see actual state
- [ ] Run `claude mcp get <name>` for each MCP
- [ ] Check `.claude/settings.local.json` for blocking settings
- [ ] Test HTTP endpoints with `curl -I`
- [ ] Test commands exist with `which`
- [ ] Verify env vars with `echo $VAR`
- [ ] Check directories exist with `ls -la`
- [ ] Test command execution manually

## References

- [MCP Documentation](https://docs.claude.com/en/docs/claude-code/mcp)
- Use `claude mcp --help` for all available commands
- Check logs in Claude Code with `--debug` flag if needed


## Companion: REFERENCE.md
# MCP Debugging Reference - Key Learnings

## The One Thing That Broke Everything

**`.claude/settings.local.json`** with `"enableAllProjectMcpServers": false`

This single setting blocks ALL `.mcp.json` servers from loading, regardless of any other configuration.

## Why This Was Hard to Find

1. **Hidden location**: Not in the obvious places (`.mcp.json`, `~/.claude.json`)
2. **Non-obvious name**: "settings.local.json" vs "local-settings.json"
3. **Boolean default**: Setting exists but defaults to false when present
4. **No clear error**: MCPs just silently don't load
5. **CLI commands lie**: `claude mcp get` shows "Connected" but `/mcp` doesn't list them

## The Debugging Journey

### What Didn't Work
- ❌ Checking `.mcp.json` - it was correct
- ❌ Restarting Claude Code - didn't help
- ❌ Resetting project choices - wasn't the issue
- ❌ Checking environment variables - they were loaded
- ❌ Testing prerequisites - everything was installed
- ❌ Checking JSON syntax - was valid

### What Finally Worked
- ✅ Actually running `claude mcp get <name>` - showed MCPs were configured
- ✅ Checking `~/.claude.json` project-specific settings
- ✅ Finding `.claude/settings.local.json`
- ✅ Discovering `"enableAllProjectMcpServers": false`

## MCP Scope Confusion

### Three Different Scopes
1. **User scope** (`~/.claude.json` → `mcpServers`)
   - Available in ALL projects
   - No approval needed
   - Shows up immediately

2. **Project scope** (`.mcp.json` at project root)
   - Shared with team (version controlled)
   - Requires approval OR `enableAllProjectMcpServers: true`
   - Can be blocked by local settings

3. **Local scope** (`.claude/settings.local.json`)
   - Personal overrides for specific project
   - NOT version controlled
   - Highest priority for this project

## The Type Field Gotcha

In `.mcp.json`, the `type` field must be:
- `"stdio"` - for local commands (NOT "local")
- `"http"` - for remote HTTP servers
- `"sse"` - for Server-Sent Events (deprecated)

## Environment Variable Expansion

```json
{
  "env": {
    "KEY": "${VAR_NAME}"           // Expands VAR_NAME
    "KEY": "${VAR_NAME:-default}"  // With fallback
  }
}
```

**Critical**: Variables must be set BEFORE Claude Code starts.

Best practice: Add to `~/.zshenv` (not `~/.zshrc`) because `.zshenv` is loaded for all shells, including non-interactive ones.

## Testing Commands

```bash
# See what's actually loaded
claude mcp list

# Get details for specific MCP
claude mcp get <name>

# Check project settings
cat .claude/settings.local.json

# Check user MCPs
cat ~/.claude.json | jq '.mcpServers'

# Check project MCPs
cat .mcp.json

# Check project-specific config in user file
cat ~/.claude.json | jq '.projects["'$(pwd)'"]'

# Reset approvals
claude mcp reset-project-choices
```

## The Complete Fix

1. Edit `.claude/settings.local.json`:
   ```json
   {
     "enableAllProjectMcpServers": true
   }
   ```

2. Restart Claude Code

3. (Optional) Remove duplicate MCPs from user scope if they exist in project scope

## Lessons Learned

1. **CLI truth vs UI truth**: `claude mcp get` shows configuration, `/mcp` shows what's actually loaded
2. **Local settings override everything**: `.claude/settings.local.json` has final say
3. **Test prerequisites independently**: Don't assume, verify each component
4. **Hidden gotchas in obvious places**: The answer was in plain sight but easy to miss
5. **Environment variables are tricky**: Must be loaded in the right shell config file at the right time

## Future Self Reminder

When MCPs don't load:
1. Check `.claude/settings.local.json` FIRST
2. Run `claude mcp get <name>` to verify config
3. Compare with `/mcp` output to see what's actually loaded
4. Check project-specific settings in `~/.claude.json`
5. Only then check the other stuff

---
# SKILL: deep-research

---
name: deep-research
description: "[REDIRECTED] Use `/researcher` instead. This skill has been merged into the researcher skill, which is a strict superset with effort-adaptive tiers (quick/standard/deep), domain profiles, and better tool routing."
argument-hint: [research question or topic]
---

# Deep Research → Researcher

This skill has been merged into **`/researcher`**. The researcher skill includes everything deep-research had, plus:

- Effort-adaptive tiers (quick/standard/deep) — deep-research was always "deep" tier
- Domain-specific profiles (see `researcher/DOMAINS.md`)
- Better tool routing (selve, DuckDB, intelligence MCPs)
- Recitation-before-conclusion protocol
- Diminishing returns gate
- Corpus building workflow

**Use `/researcher` for all research tasks.** It auto-selects the appropriate tier. To force deep tier: `/researcher --deep [question]`.

$ARGUMENTS

---
# SKILL: diagnostics

---
name: Dev Environment Diagnostics
description: Environment validation, health checks, cache management, error diagnosis for Clojure/ClojureScript development. Triggers on health, preflight, cache, diagnose, validate environment. Includes API key checks, dependency verification, cache clearing. No network required except for API validation.
---

# Dev Environment Diagnostics

## Prerequisites

**Required Tools:**

- `java` - JVM for Clojure
- `clojure` - Clojure CLI
- `node` - Node.js runtime
- `npm` - Package manager
- `shadow-cljs` - ClojureScript compiler

**Optional Tools:**

- `git` - Version control
- `rlwrap` - REPL line editing

**API Keys (optional):**

```bash
# In .env file
GEMINI_API_KEY=your-key
OPENAI_API_KEY=your-key
XAI_API_KEY=your-key
```

## Quick Start

```bash
# Quick health check
./run.sh health

# Pre-flight before starting work
./run.sh preflight

# Clear all caches
./run.sh cache clear

# Diagnose specific error
./run.sh diagnose "Cannot resolve symbol"

# Check API keys
./run.sh api-keys check
```

## When to Use

Use this skill when:

- Starting a new development session
- Troubleshooting build issues
- Environment problems (missing dependencies, stale cache)
- Diagnosing common errors
- Pre-commit validation
- CI/CD health checks

## Available Commands

### health - Quick Health Check

```bash
./run.sh health
```

Checks:

- ✅ Java version
- ✅ Clojure CLI
- ✅ Node.js & npm
- ✅ Shadow-CLJS
- ✅ Git status
- ✅ API keys (if .env exists)

### preflight - Pre-Flight Checks

```bash
./run.sh preflight
```

More thorough checks before starting work:

- Environment health (all above)
- Cache status
- Dependency freshness
- REPL connectivity (if server running)
- Workspace cleanliness

Use before:

- Starting new feature
- After pulling changes
- When switching branches

### cache - Cache Management

```bash
# Show cache status
./run.sh cache status

# Clear all caches
./run.sh cache clear

# Clear specific cache
./run.sh cache clear shadow      # .shadow-cljs/
./run.sh cache clear clj-kondo   # .clj-kondo/.cache/
./run.sh cache clear clojure     # .cpcache/
./run.sh cache clear npm         # node_modules/.cache/
```

**Cache locations:**
| Cache | Path | When to Clear |
|-------|------|---------------|
| Shadow-CLJS | `.shadow-cljs/` | Weird compilation errors, stale code |
| Clj-kondo | `.clj-kondo/.cache/` | Linter not finding symbols, false warnings |
| Clojure | `.cpcache/` | Dependency resolution issues |
| npm | `node_modules/.cache/` | After package.json changes |
| Skills | `.cache/` | Research or visual cache issues |

### diagnose - Error Diagnosis

```bash
# Diagnose specific error
./run.sh diagnose "error message"

# Interactive diagnosis
./run.sh diagnose --interactive
```

Uses `skills/diagnostics/data/error-catalog.edn` to:

- Match error patterns
- Suggest fixes
- Provide auto-fix commands

**Example:**

```bash
$ ./run.sh diagnose "Cannot resolve symbol"

Found match: :unresolved-symbol
Category: compilation
Likely causes:
  - Missing require
  - Typo in name
  - Wrong alias
Fixes:
  - Add (require '[namespace :as alias])
  - Check spelling
  - Verify namespace exists
```

### api-keys - API Key Validation

```bash
# Check which keys are set
./run.sh api-keys check

# Validate keys work (makes test API calls)
./run.sh api-keys validate

# Show required keys
./run.sh api-keys required
```

**Required keys:** GEMINI_API_KEY, OPENAI_API_KEY, XAI_API_KEY
**Optional keys:** ANTHROPIC_API_KEY, GROQ_API_KEY

## NPM Commands Integration

The skill wraps existing npm commands:

| NPM Command               | Skill Command                |
| ------------------------- | ---------------------------- |
| `npm run agent:health`    | `./run.sh health`            |
| `npm run agent:preflight` | `./run.sh preflight`         |
| `npm run fix:cache`       | `./run.sh cache clear`       |
| `npm run repl:health`     | Part of `./run.sh preflight` |

## Error Catalog

Maintains `skills/diagnostics/data/error-catalog.edn` with common errors and fixes:

### Common Errors

**Unresolved Symbol**

- Pattern: `Cannot resolve symbol`
- Category: compilation
- Fix: Add `(require '[namespace :as alias])`

**Stale Cache**

- Pattern: `Unexpected error` / Strange behavior
- Category: cache
- Fix: `./run.sh cache clear`

**Port In Use**

- Pattern: `port.*in use` / `address.*in use`
- Category: runtime
- Fix: `pkill -f shadow-cljs`

**API Key Missing**

- Pattern: `api.*key` / `authentication`
- Category: configuration
- Fix: Check `.env` file and `source .env`

## Common Diagnostics Scenarios

### Scenario 1: "Build is broken"

```bash
# 1. Check environment
./run.sh health

# 2. Clear caches
./run.sh cache clear

# 3. Rebuild
npm run dev
```

### Scenario 2: "Linter is confused"

```bash
# 1. Clear linter cache
./run.sh cache clear clj-kondo

# 2. Re-run linter
npm run lint
```

### Scenario 3: "API calls failing"

```bash
# 1. Check keys present
./run.sh api-keys check

# 2. Validate keys work
./run.sh api-keys validate

# 3. Source .env if needed
source .env
```

### Scenario 4: "Strange runtime behavior"

```bash
# Diagnose automatically
./run.sh diagnose "describe the behavior"

# Often: stale cache
./run.sh cache clear
```

## Cache Management Patterns

### Safe Clear Order

```bash
# 1. Try selective clear first
./run.sh cache clear shadow

# 2. If still broken, clear all
./run.sh cache clear

# 3. Rebuild
npm run dev
```

### When to Clear Cache

**Clear Shadow-CLJS cache:**

- Weird compilation errors
- Stale code loading
- After dependency changes

**Clear Clj-kondo cache:**

- Linter not finding new symbols
- False positive warnings

**Clear NPM cache:**

- Dependency resolution issues
- After package.json changes

**Clear all caches:**

- "Turn it off and on again" moment
- Before important demo
- After major refactor

## Integration with CI/CD

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

./skills/diagnostics/run.sh health || exit 1
npm run lint || exit 1
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
- name: Environment Check
  run: ./skills/diagnostics/run.sh health

- name: Cache Status
  run: ./skills/diagnostics/run.sh cache status
```

## Configuration Options

**Health check thresholds:**

- Required tools must be present
- Optional tools warn if missing
- API keys checked if .env exists

**Cache management:**

- Auto-clear threshold: 500 MB
- Warn size: 200 MB
- Clear on error: disabled by default

**Error diagnosis:**

- Uses `skills/diagnostics/data/error-catalog.edn`
- Verbose output: disabled
- Suggest fixes: enabled

## Tips & Best Practices

1. **Run health check at session start** - Catch problems early
2. **Clear cache when in doubt** - Shadow-CLJS cache is safe to delete
3. **Keep error catalog updated** - Add new patterns as encountered
4. **Use preflight before commits** - Catch issues before pushing
5. **Monitor cache sizes** - Large caches may indicate issues

## Common Pitfalls

- **Forgetting to source .env** - API keys won't be available
- **Partial cache clear** - Sometimes need to clear all
- **Skipping preflight** - Issues found late in development
- **Stale node_modules** - Occasional `rm -rf node_modules && npm install` needed

## Troubleshooting

**"Health check fails"**

- Install missing tools
- Check PATH includes tool directories
- Verify versions compatible

**"Cache clear doesn't help"**

- Try clearing all caches
- Check for permission issues
- Verify disk space available

**"API keys not found"**

- Verify .env exists in project root
- Check keys not commented out
- Source .env: `source .env`

**"Diagnose finds no match"**

- Error might be new
- Add to error catalog manually
- Use interactive mode

## Resources (Level 3)

- `run.sh` - Main CLI wrapper
- `dev/health.clj` - Clojure health check functions
- `skills/diagnostics/data/error-catalog.edn` - Error pattern database
- `dev/bin/health-check.sh` - Standalone health check
- `dev/bin/preflight.sh` - Preflight validation script

## See Also

- Project docs: `../../CLAUDE.md#dev-tooling`
- NPM commands: `../../package.json`
- Pre-commit hook: `../../.pre-commit-check.sh`

---
# SKILL: entity-management

---
name: entity-management
description: Versioned knowledge management for entities (people, companies, genes, drugs, stocks). Use when the user wants to profile, track, build a dossier on, or save structured notes about a specific entity. One file per entity, git-versioned, every claim sourced.
user-invocable: true
argument-hint: [entity name — person, company, gene, drug, stock]
---

# Entity Management

Track knowledge about individual entities with full provenance. Every edit is a git commit so you can see reasoning evolution, belief updates, and corrections over time.

## File Structure

```
docs/entities/
├── self/           # User's own profile, cognitive traits
├── companies/      # Companies under investigation or research
├── genes/          # Individual genes (g6pd.md, ebf3.md)
├── drugs/          # Medications, supplements
├── people/         # Named individuals
└── <category>/     # Any domain-specific category
```

One file per entity at `docs/entities/<category>/<entity-name>.md`.

## Provenance Rules

Every claim must cite a ground-truth source or explicit derivation chain:

### Primary Sources (highest reliability)
- Paper DOIs, PMIDs
- Database IDs: ClinVar, gnomAD, OMIM, PharmGKB
- Official URLs: FDA labels, CPIC guidelines, SEC filings
- API responses: with timestamp and query parameters
- Court records, government reports

### Derived Claims
State the inputs + transformation:
> "PRS percentile computed from `prs_results.tsv` using EUR reference panel"

### Inferred Claims
Explicitly mark as `[INFERRED]` with reasoning chain:
> "[INFERRED] Likely reduced enzyme activity based on MAVE score 0.023 + structural homology to known loss-of-function variants"

### Unverified Claims
Mark as `[UNVERIFIED]` with the source of the claim:
> "[UNVERIFIED] Reported in a blog post but no primary source found"

### Corrected Claims
When updating a previous claim, mark as `[CORRECTED]`:
> "[CORRECTED] Previously stated OR=2.3; actual OR=1.3 per gnomAD v4.1"

## Cross-References (Zettelkasten Pattern)

Entity files should link to related entities. When a gene is a drug target, the gene file links to the drug file and vice versa. When a person is an officer of a company, both files cross-reference.

Format: `→ see [entity-name](../category/entity-name.md)` in the relevant Key Facts row.

This enables traversal: starting from one entity, you can follow links to build a complete picture without relying on search. Based on A-MEM's Zettelkasten-inspired memory architecture (ICLR 2026, arXiv:2502.12110) — structured connections between memories improve retrieval over flat storage.

## Staleness Detection

Every claim in the Key Facts table has a `Date Verified` column. Claims older than 6 months should be flagged for re-verification when the entity file is loaded:

> **STALE:** [N] claims last verified >6 months ago. Re-verify before relying on them.

This is especially critical for: stock prices, company officers, clinical trial status, drug approval status, regulatory filings.

## Progressive Disclosure Within Entity Files

When an entity file exceeds ~200 lines, add a `## Summary` section at the top (after the one-liner) containing ONLY the Key Facts table. This lets agents load the summary without reading the full narrative — reducing context cost when the entity is referenced but not the focus.

## Never Do This

- State conclusions without provenance
- Use "I read it somewhere" or "an AI said it" as a source — find the primary reference or mark `[UNVERIFIED]`
- Copy claims from one entity file to another without re-verifying
- Delete incorrect claims — correct them with `[CORRECTED]` so the git history shows the evolution

## Template

```markdown
# Entity Name

> One-line description. Category: <type>.

## Key Facts

| Fact | Source | Date Verified |
|------|--------|---------------|
| ... | DOI/URL/database ID | YYYY-MM-DD |

## Narrative Summary

[Sourced prose. Every paragraph ends with citations.]

## Open Questions

- [What's unresolved]
- [What would change the assessment]

## Changelog

- YYYY-MM-DD: Created with initial findings from [source]
- YYYY-MM-DD: [CORRECTED] claim X based on [new source]
```

## Git Conventions

- Every edit is a separate commit
- Commit message format: `entities/<category>/<name>: <what changed>`
- Example: `entities/genes/g6pd: correct enzyme activity from MAVE data`
- Don't batch entity updates with unrelated changes

## When to Create an Entity File

Create one when:
- Knowledge will accumulate over multiple sessions
- Multiple sources contribute to understanding the entity
- Corrections or belief updates are likely
- The entity appears in multiple contexts (research memos, protocols, analyses)

Don't create one for:
- Entities mentioned once in passing
- Entities fully described in a single research memo
- Generic categories (create a research memo instead)

---
# SKILL: epistemics

---
name: epistemics
description: Bio/medical/scientific evidence hierarchy and anti-hallucination rules. Use when conducting claim-heavy medical research, genomics interpretation, supplement evaluation, pharmacogenomics, or clinical evidence synthesis. NOT for casual health questions, software engineering, or physics. Companion to deep-research skill.
user-invocable: false
---

# Bio/Medical Research Epistemics

Domain-specific guardrails for scientific research. Use alongside `deep-research` for the workflow; this skill provides the evidence hierarchy, anti-hallucination rules, and bio-specific failure modes.

## Anti-Hallucination Rules (non-negotiable)

1. **Citation requirement:** Every non-trivial factual claim needs a resolvable citation (DOI, PMID, ClinicalTrials.gov ID, or official URL). If you can't cite it, label "UNCITED."

2. **No fake citations:** Never invent paper titles, authors, journals, or numbers. If you can't find the paper, say so.

3. **Separate evidence layers:** Keep strictly distinct:
   - (a) In vitro / cell culture
   - (b) Animal model (species, dose, route)
   - (c) Human observational / GWAS association
   - (d) Human RCT — surrogate endpoint (biomarker)
   - (e) Human RCT — clinical outcome (patient-important)
   - (f) Systematic review / meta-analysis
   - (g) Clinical guideline / consensus statement

   NEVER let (a-c) substitute for (d-g). Say explicitly: "Mechanistic evidence only; no human clinical trial confirms this."

4. **Quantify uncertainty:** Effect sizes need CIs or ranges. State population, comparator, timeframe. For genetic associations: OR + CI + population + MAF.

5. **Genetic claims:** Distinguish GWAS association vs functional validation vs clinical actionability. State penetrance. "Associated with" ≠ "causes." Single-SNP interpretation of polygenic traits is usually misleading. PGx claims need CPIC/DPWG level.

6. **Dosing guardrails:** Rx = guideline ranges only ("discuss with prescriber"). OTC/supplements = evidence-based ranges if cited. Genotype→dose only with CPIC/DPWG-level evidence, otherwise label INFERENCE.

## Evidence Hierarchy

Grade every claim:

| Grade | Type | Notes |
|-------|------|-------|
| 1 | Clinical guideline / consensus | NICE, WHO, AAD, CPIC, DPWG |
| 2 | Systematic review / meta-analysis | Cochrane, PRISMA-compliant |
| 3 | Well-powered RCT | Pre-registered, independent, adequate N |
| 4 | Small / pilot RCT | Underpowered, often industry-funded |
| 5 | Large observational / cohort | Adjusted, replicated |
| 6 | GWAS / genetic association | Report OR, CI, population, replication |
| 7 | Animal model | Species, dose, route — note translatability |
| 8 | In vitro / cell culture | Note concentration vs physiological |
| 9 | Case report / expert opinion | Lowest weight |

Always note: COI, replication status, sample size, population match, effect size (NNT, ARR, or Cohen's d when available).

## Inference Rules

You may reason from first principles, but MUST label it INFERENCE.

Any INFERENCE must include:
- Assumptions stated explicitly
- A minimal derivation (with units)
- Sensitivity: what if the key assumption is 2x off?

Three buckets in every output:
1. **EVIDENCE** — cited, graded
2. **INFERENCE** — derived from evidence + assumptions, labeled
3. **PRACTICAL** — availability, cost, formulation; never upgraded to efficacy claims

## Bio-Specific Failure Modes

Check yourself against each before outputting:

- **Genotype→phenotype leap:** Treating GWAS association (OR 1.1-1.5) as deterministic prediction. Fix: state OR, CI, population, penetrance.
- **Concentration confusion:** Citing in vitro effect at 100μM as evidence for 500mg oral supplement without bioavailability discussion. Fix: check if effective concentration is physiologically achievable.
- **Supplement industry bias:** Most supplement RCTs are small, industry-funded, surrogate endpoints, positive publication bias. Fix: flag funding, N, endpoint type.
- **Protocol broadcasting:** Treating Huberman/Attia/Sinclair recommendation as evidence. Fix: trace to primary study and grade independently.
- **N=1 extrapolation:** "Bryan Johnson does X" = anecdote, not evidence.
- **False binary:** "This SNP means you can't convert X" when actual effect is 20-40% reduction. Fix: quantified ranges, not categorical language.
- **Directionality error:** Citing real study but inverting the sign. Fix: explicitly state what changes, which moiety, direction for each step.
- **Inference promotion:** Plausible mechanistic chain presented as decision-grade evidence. Fix: put in explicit INFERENCE section with assumptions + failure modes.
- **Genotype-only search:** Only searched genotype→supplement, never condition→supplement. Fix: ALWAYS run condition-anchored search axis in parallel.

## LLM-Specific Failure Modes (updated Feb 2026)

| Model | Failure Mode | Severity | Notes |
|-------|-------------|----------|-------|
| Claude (Opus 4.6) | Sycophantic hedging; agrees then qualifies until useless | Medium | Improved from 4.5 but still present |
| Claude | Citation-shaped bullshit; plausible references that don't exist | High | CoT unfaithfulness baseline: 7-13% on clean prompts (ICLR 2026) |
| Claude | Genotype determinism; treats associations as deterministic | High | |
| GPT (5.2/5.3) | Confident fabrication; invents complete fake studies with authors and N | Critical | Worse with extended thinking enabled |
| GPT | Overcitation; cites 20+ papers, many tangential or unverifiable | Medium | |
| Gemini (3.1 Pro) | Google-source bias; over-relies on Scholar snippets without reading papers | High | 1M context invites dumping entire papers without processing |
| Gemini | Length inflation; massive outputs that bury the signal | Medium | |
| All models | Implicit post-hoc rationalization; unfaithful CoT on clean prompts | Medium | 7-13% baseline rate (arXiv, ICLR 2026 submission). Not adversarial — happens on normal prompts |

**Cross-model validation:** For high-stakes bio claims (Grade 1-3 evidence affecting clinical decisions), route the same evidence through a second model as independent assessor. Different models have different fabrication patterns — Claude invents plausible-but-wrong citations, GPT invents complete fake studies. Cross-checking catches both.

## Recitation Before Synthesis

Before grading evidence or writing conclusions, **recite the key evidence items verbatim** — restate the study name, N, effect size, and population for each Grade 1-5 source you're relying on. This combats lost-in-the-middle effects when working with many sources (Du et al., EMNLP 2025: +4% accuracy, training-free).

Don't summarize — recite. The act of restating forces attention back to the actual data before the synthesis step where hallucination risk is highest.

## Self-Audit Checklist

After any bio research output:
- [ ] Every number has a source (DOI/PMID/URL)
- [ ] No study cited that you haven't verified exists
- [ ] In vitro/animal evidence NOT used to justify clinical recommendations
- [ ] Genetic associations include OR, CI, population, penetrance
- [ ] "Cannot/always/never" replaced with quantified ranges
- [ ] Industry-funded studies flagged
- [ ] Supplement doses cite the study they come from
- [ ] Genotype→dosing claims have CPIC/DPWG level or labeled INFERENCE
- [ ] Confidence ratings are honest
- [ ] Counterarguments section exists and is substantive

## PGx Quick Reference

**Justified:** CPIC Level A/B, PharmGKB Level 1A/1B.
**Not justified (but LLMs do it):** Single GWAS hit OR<2.0→dose recommendation; nutrigenomic SNP→supplement dose; variant without replication in user's ancestry.

**Key databases:** CPIC (cpicpgx.org), PharmGKB, ClinVar, DPWG, gnomAD.

## Non-Paper Evidence (acceptable, labeled)

- Regulatory: FDA/EMA monographs, drug labels, safety communications
- Grey literature: ClinicalTrials.gov entries, conference posters, preprints [PREPRINT]
- Independent testing: ConsumerLab, Labdoor, third-party CoAs
- PGx databases: PharmGKB, ClinVar, CPIC guidelines
- Operational: formulation stability, supply chain, product CoAs

---
# SKILL: goals

---
name: goals
description: Elicit, clarify, or revise project goals through structured questioning. Produces or updates GOALS.md — the human's personal objectives, strategy, success metrics, and deployment philosophy. Separate from constitution (operational principles). Use when starting a new project, pivoting strategy, or when goals feel unclear.
user-invocable: true
disable-model-invocation: true
---

# Goals Elicitation

You are helping the human clarify what they actually want from this project. Goals are personal — they define WHAT to optimize for. They are distinct from the constitution (HOW agents operate).

## When to Use

- New project without a GOALS.md
- Existing project where strategy has drifted or goals feel stale
- After a significant pivot or new capability
- When the human says things like "I'm not sure what I'm optimizing for" or "let's refocus"

## Phase 1: Understand Current State

<exploration>
Read everything that reveals intent:
- GOALS.md (if it exists — this is a revision, not creation)
- CONSTITUTION.md or docs/CONSTITUTION.md (for the generative principle and operational context)
- CLAUDE.md (stated purpose, project description)
- MEMORY.md or persistent memory (prior decisions, constitutional questionnaire results)
- Any README, docs/, or project description files
- Recent git log (what has the human actually been working on vs. what they say they want?)
- ~/Projects/meta/memory/MEMORY.md (cross-project decisions if they exist)
</exploration>

Pay attention to the gap between stated goals and revealed preferences. If GOALS.md says "investment research" but the last 20 commits are fraud investigation, that's a tension worth surfacing.

## Phase 2: Goal Decomposition

Every project goal has these layers. Identify which are clear and which are ambiguous:

<goal_layers>
1. **Mission** — Why does this project exist? One sentence.
2. **Domain** — What specific slice of the world does it operate in? (market cap range, geography, sector, organism, condition)
3. **Strategy** — How does the mission get accomplished? (alpha strategies, research methods, data pipeline)
4. **Success metrics** — How do you know it's working? Must be measurable. (returns, Brier score, entity count, prediction accuracy)
5. **Time horizon** — When should these metrics show results? (3 months, 12 months, 3 years)
6. **Resource constraints** — Budget, time, compute, attention. What's scarce?
7. **Deployment philosophy** — How do decisions become actions? (manual, semi-auto, fully autonomous, outbox pattern)
8. **Deferred scope** — What is explicitly NOT being done yet? (prevents scope creep)
9. **Secondary capabilities** — What else does the infrastructure enable, even if it's not the primary goal?
10. **Exit/pivot conditions** — Under what circumstances would the human abandon or radically change this project?
</goal_layers>

## Phase 3: Questionnaire

Generate 8-12 questions targeting the ambiguous layers. Only ask about what's unclear — skip layers that are already well-defined.

Question design:
- Start with the most consequential ambiguity (mission > domain > strategy > metrics)
- Offer 3-4 concrete options, letter-coded
- Include "Something else: ___" as last option
- Reference specific things you found in Phase 1 ("Your GOALS.md says X but your recent work is Y — which is the real priority?")
- For revision sessions: focus on what changed, not what's stable

<example_questions>
**If mission is unclear:**
"This project currently does X, Y, and Z. When you have time for only one, which wins?"
- (a) X — it's the core, everything else is secondary
- (b) Y — X was the starting point but Y is where the value is
- (c) They're inseparable — the value comes from doing all three
- (d) Something else: ___

**If success metrics are vague:**
"How will you know this is working in 6 months?"
- (a) Measurable financial returns (P&L, Sharpe ratio)
- (b) Growing knowledge base (entity count, prediction accuracy, data coverage)
- (c) Reduced manual effort (agent handles X% of tasks autonomously)
- (d) Something else: ___

**If scope is creeping:**
"You said [deferred item] was future work, but you've spent significant time on it. Should it be promoted to an active goal?"
- (a) Yes, it's become important enough to be a primary goal
- (b) No, I got distracted — refocus on the original goals
- (c) Keep it as secondary — work on it when the primary goals are blocked
- (d) Something else: ___
</example_questions>

## Phase 4: Produce GOALS.md

After the human answers, write or update `docs/GOALS.md` (or `GOALS.md` at root if no docs/ directory).

<template>
# Goals: What This System Is For

**Owner:** Human. Agent must not modify without explicit approval.

---

## Primary Mission
[One paragraph. Why this project exists.]

## Why This Domain
[Why this specific domain was chosen. What makes it the right training ground, the right market, the right problem.]

## Target Domain
[Specific constraints that bound the search space. Market cap, geography, sector, organism — whatever applies.]

## Strategy
[How the mission gets accomplished. Key approaches, ranked by expected value if applicable.]

## Success Metrics ([Time Horizon])
[3-5 measurable outcomes. Each must have a number or threshold attached.]

## Resource Constraints
[Budget, compute, time, attention. What's scarce and how does that shape priorities.]

## Deployment Philosophy
[How decisions become actions. Manual, semi-auto, outbox pattern, graduated autonomy.]

## Secondary Capabilities
[What else the infrastructure enables, even if it's not the primary goal right now.]

## What's Explicitly Deferred
[Things deliberately NOT being done yet. Prevents scope creep. Include conditions under which they'd be promoted.]

## Exit Conditions
[Under what circumstances would the strategy fundamentally change? Not failure scenarios — pivot triggers.]

---

*This document defines WHAT the system optimizes for. See CONSTITUTION.md for HOW it operates. The agent may propose changes but must not modify without human approval.*
</template>

## Revision Mode

When GOALS.md already exists:
1. Read it fully
2. Compare stated goals against recent activity (git log, entity files, analysis output)
3. Identify drift: where reality diverged from the plan
4. Ask targeted questions about the drift (not the whole questionnaire again)
5. Update only the sections that changed
6. Note what was revised and why at the bottom of the commit message

## Cross-Project Awareness

If ~/Projects/meta/memory/MEMORY.md exists, read it for cross-project decisions. Goals in one project may constrain goals in another:
- Shared entity graph means shared data investments
- Shared epistemics means compatible evidence standards
- Time/attention is zero-sum across projects

Surface these constraints when relevant. "You allocated X to intel and Y to selve — is that still the right split?"

---
# SKILL: investigate

---
name: investigate
description: Deep forensic investigation methodology for datasets, entities, or systems. Use when the user wants to find fraud, corruption, audit billing, follow the money, OSINT a company, or investigate shell companies. Adversarial, cross-domain, honest about provenance.
argument-hint: [topic or entity to investigate]
---

# Investigation Methodology

You are conducting a forensic investigation. Your job is to find what's wrong, not explain why things look fine.

## Linked Skills

- **`competing-hypotheses`** — Use for any lead before handoff
- **`source-grading`** (auto-applied) — Grade every claim on A1-F6 matrix
- **`deep-research`** — Use for external validation

## Core Principles

1. **Adversarial stance:** Do NOT explain away anomalies. Quantify how wrong things look.
2. **Source grading:** Every claim graded on two axes (see `source-grading` skill).
3. **Cross-domain triangulation:** Seek 2+ independent confirmations from different domains: financial, enforcement, political, labor, corporate, market, journalism.
4. **Follow money to physical reality:** Does the entity exist? Who owns it? Who works there? Where does money go? Who protects the status quo?
5. **Name names:** Name entities, people, dollar amounts, dates. Vague findings are useless.

## Pattern Recognition

Known fraud/abuse patterns:
- **Self-attestation:** Entity verifies its own work
- **PE playbook:** Acquire → load debt → extract → bill at max → flip
- **Regulatory capture:** Lobbyists write legislation, revolving door
- **Growth anomalies:** >100%/yr in industries where 5-15% is normal
- **Zombie entities:** Deactivated/excluded entities still billing

## Investigation Workflow

### Phase 1: Ground Truth Audit
Row counts, column types, date ranges, distributions. What CAN'T this data tell you?

### Phase 2: Structural Analysis
Concentration, variation, fastest growth, self-attestation patterns.

### Phase 3: Anomaly Hunting
Who bills the most? Who grew impossibly fast? Who charges 10x median? Who has 40%+ denial rates but keeps billing?

### Phase 4: Competing Hypotheses (ACH)
Invoke `competing-hypotheses` for significant anomalies. Do not skip for leads above $10M.

### Phase 5: OSINT Layer
- **Officer/ownership spider:** Extract officers → find all entities they control
- **Address clustering:** Find all entities at same address
- **Corporate DNA:** Where did sanctioned entity officers go next?
- **Fraud triangle signals:** Financial pressure on officers (lawsuits, liens, bankruptcy)

### Phase 6: External Validation
Journalism, government reports, enforcement actions, academic studies. Search for symptoms, not diagnoses.

### Phase 7: Cross-Domain Deep Dive
SEC filings, PE ownership chains, campaign finance, labor economics, physical verification, credit/bankruptcy.

### Phase 7b: Recitation Before Conclusion
Before writing synthesis, **restate the specific evidence** — concrete data points, dollar amounts, dates, source grades. Then derive the conclusion. This prevents narrative from burying contradictions. (Du et al., EMNLP 2025: +4% accuracy on long-context tasks, training-free.)

### Phase 8: Synthesis
For each lead: ACH result, estimated exposure, EV score, network findings, recommended channel, key uncertainties.

## Memory-Efficient Data Analysis

For datasets >1GB, use DuckDB, not pandas:
```bash
uvx --with duckdb python3 << 'PYEOF'
import duckdb
con = duckdb.connect()
con.execute("COPY (SELECT ... FROM read_parquet('...')) TO '...' (HEADER, DELIMITER ',')")
con.close()
PYEOF
```

## Output

- One "what is wrong" document (adversarial, no hedging)
- One "external confirmation" document (sourced validation)
- One "cross-domain" document (SEC, PE, political, labor)
- One "new leads" document (uninvestigated anomalies with ACH scores)
- CSV intermediates for reproducibility

$ARGUMENTS

---
# SKILL: llmx-guide

---
name: llmx Guide
description: Critical gotchas when calling llmx from Python. Non-obvious bugs and incompatibilities.
---

# llmx CLI Gotchas

## GPT-5.2 Timeouts (the #1 issue)

GPT-5.2 with reasoning burns time BEFORE producing output. Default 120s timeout is too low.

**Auto-scaling (v0.4.0+):** When `--timeout` is not explicitly set, llmx auto-scales:

| `--reasoning-effort` | Auto timeout | Typical response time |
| -------------------- | ------------ | --------------------- |
| none / low           | 120s         | 1-15s                 |
| medium               | 300s (5 min) | 30-90s                |
| high                 | 600s (10 min)| 3-10 min              |
| xhigh                | 900s (15 min)| 10-30+ min            |

**If you explicitly pass `--timeout N`, auto-scaling is disabled.** Max allowed: 900s.

**Streaming avoids most timeouts:** Non-streaming holds the connection idle during reasoning. Proxies and HTTP clients kill idle connections. `--stream` sends keepalive chunks.

```bash
# WILL timeout with default settings:
llmx -m gpt-5.2 --reasoning-effort high --no-stream "complex query"

# WORKS — auto-timeout 600s:
llmx -m gpt-5.2 --reasoning-effort high "complex query"

# BEST for high/xhigh — streaming avoids idle-connection kills:
llmx -m gpt-5.2 --reasoning-effort high --stream "complex query"

# For very long tasks, use deep research (background mode, no timeout):
llmx research "complex multi-source analysis"
```

**When calling from Python/subprocess:**
```python
# Set timeout high for reasoning models
subprocess.run(
    ['llmx', '-m', 'gpt-5.2', '--reasoning-effort', 'high', '--stream'],
    input=prompt, capture_output=True, text=True,
    timeout=900  # subprocess timeout must also be high
)
```

## Bug: shell=True breaks with parentheses

**Wrong:**

```python
subprocess.run(f'echo {repr(prompt)} | llmx ...', shell=True)  # BREAKS if prompt has ()
```

**Right:**

```python
subprocess.run(['llmx', '--provider', 'google'], input=prompt, ...)
```

## --reasoning-effort works with OpenAI AND Gemini (v0.4.0+)

```python
# GPT-5 -- defaults to high automatically, override to lower:
['llmx', '-m', 'gpt-5-pro', '--reasoning-effort', 'low']

# Gemini 3.x -- maps to thinkingConfig via LiteLLM:
['llmx', '-m', 'gemini-3-pro-preview', '--reasoning-effort', 'low']

# Still ignored for Kimi -- use --no-thinking instead:
['llmx', '-m', 'kimi-k2-thinking', '--no-thinking']  # Switches to instruct model
```

**Defaults:** GPT-5 models auto-default to `--reasoning-effort high`. Gemini defaults to `high` server-side (no client default needed). Temperature locked to 1.0 for both GPT-5 and Gemini 3.x thinking models.

## Model names: hyphens not dots

| Right               | Wrong               |
| ------------------- | ------------------- |
| `claude-sonnet-4-6` | `claude-sonnet-4.6` |
| `kimi-k2.5`         | `kimi-k2-thinking`  |

## Verified Gemini Model Names (tested Feb 28, 2026)

Gemini naming is inconsistent. These are confirmed working:

| Model Name | Status | Use for |
|------------|--------|---------|
| `gemini-3-flash-preview` | Works | Cheap pattern extraction, fact-checking (Flash 3 text) |
| `gemini-3.1-flash-image-preview` | Works | Flash 3.1 with image (no text-only 3.1 Flash yet) |
| `gemini-3.1-pro-preview` | Works | Architectural review, cross-referencing, large context |
| `gemini-3-pro-preview` | Works | Older Pro 3.0 |
| `gemini-3-flash-preview` | Works (warns "Lite") | Only for file/semantic search, not chat |
| `gpt-5.2` | Works | Quantitative/formal analysis |

**404 — DO NOT USE:**

| Wrong Name | Why |
|------------|-----|
| `gemini-3-flash` | Missing `-preview` suffix |
| `gemini-flash-3` | Wrong word order + missing `-preview` |

The `-preview` suffix is required for all Gemini 3.x models. This is a Google naming convention, not an llmx issue.

## Testing: test small before full pipeline

```bash
# Don't wait for full pipeline to discover API key is wrong
llmx --provider google <<< "2+2?"
```

## Judge names ≠ model names

| Context               | Name             |
| --------------------- | ---------------- |
| llmx CLI              | `gemini-3.1-pro-preview` |
| tournament MCP judges | `gemini25-pro`   |

## Deep Research (v0.4.0+)

Background-mode research using OpenAI o3/o4-mini. No timeout issues — runs asynchronously.

```bash
# Full research report with citations (2-10 min, background mode)
llmx research "economic impact of semaglutide"

# Faster/cheaper with o4-mini
llmx research --mini "compare React vs Svelte"

# Save output
llmx research "CRISPR patent landscape" -o report.md

# With code interpreter for data analysis
llmx research --code-interpreter "global EV trends with data"
```

## Image Generation (v0.3.0+)

Generate images with Gemini 3 Pro Image:

```bash
# Generate PNG
llmx image "pixel art robot" -o robot.png

# With options
llmx image "game sprite" -r 2K -a 16:9 -o sprite.png

# Generate SVG
llmx svg "arrow icon" -o arrow.svg
```

**Options:**
- `-o` output path
- `-r` resolution: `1K`, `2K`, `4K`
- `-a` aspect ratio: `1:1`, `16:9`, `4:3`, etc.

**Note:** No Gemini 3 Flash Image model exists - both `flash` and `pro` use `gemini-3-pro-image-preview`.

## Vision Analysis (v0.4.0+)

Analyze images/videos with Gemini 3 Flash/Pro:

```bash
# Single image
llmx vision screenshot.png -p "What UI issues do you see?"

# Multiple images with sampling
llmx vision "frames/*.png" -p "Summarize gameplay" --sample 5

# Video analysis (uploads to Gemini Files API)
llmx vision gameplay.mp4 -p "List all UI elements"

# Compare images
llmx vision img1.png img2.png -p "Compare these two"
```

**Options:**
- `-p` prompt (required)
- `-m` model: `flash` (default, fast) or `pro` (better)
- `--sample N` sample N frames evenly from many images
- `--json` request structured JSON output

**Size limits:**
- Inline: < 20MB images, < 100MB videos
- Larger files auto-upload via Files API

---
# SKILL: model-guide

---
name: model-guide
description: Frontier model selection and prompting guide. Which model for which task, how to prompt each one, known pitfalls, validation checklists. Use when choosing between Claude/GPT/Gemini/Kimi, routing tasks to models, writing prompts for non-Claude models, debugging model-specific issues, or optimizing multi-model workflows. Triggers on "which model", "how to prompt", "model comparison", "model selection", "prompting guide", "GPT tips", "Gemini tips", "Kimi tips".
---

# Model Guide

Select the right frontier model for a task and prompt it correctly.

**Models covered:** Claude Opus 4.6, Claude Sonnet 4.6, GPT-5.2, Gemini 3.1 Pro, Kimi K2.5.
**Last updated:** 2026-02-27. See CHANGELOG.md for update history.

## Quick Selection Matrix

| Task | Best Model | Why | Runner-up |
|------|-----------|-----|-----------|
| **Agentic coding** | Claude Opus 4.6 | SWE-bench 80.8%, Arena coding #1 | Sonnet 4.6 (79.6%, 1/5 cost) |
| **Fact-sensitive work** | Claude Opus 4.6 / Gemini 3.1 | SimpleQA 72% (tied best) | NOT GPT-5.2 (58%), NOT Kimi (37%) |
| **Legal reasoning** | Claude Opus 4.6 | BigLaw 90.2% | -- |
| **Professional analysis** | Claude Opus 4.6 | GDPval-AA Elo 1606 (expert preference) | Sonnet 4.6 (GDPval 1633) |
| **Computer use / browsing** | Claude Opus 4.6 | OSWorld 72.7% | -- |
| **Hard math** | GPT-5.2 | MATH 98%, AIME 100% | Kimi K2.5 (MATH 98%, AIME 96%) |
| **Precise structured output** | GPT-5.2 | IFEval 95%, native Structured Outputs | Claude (94%), Kimi (94%) |
| **Vision / document OCR** | GPT-5.2 | DocVQA 95%, ScreenSpot 86.3% | Kimi K2.5 (MMMU-Pro 78.5%) |
| **Science reasoning** | Gemini 3.1 Pro | GPQA Diamond 94.3% | GPT-5.2 (93.2%) |
| **Abstract pattern recognition** | Gemini 3.1 Pro | ARC-AGI-2 77.1% | Claude (68.8%) |
| **Long document ingestion** (>200K) | Gemini 3.1 Pro | Native 1M context | GPT-5.2 (400K) |
| **Subagent coding** | Claude Sonnet 4.6 | 79.6% SWE-bench at $3/$15 | Kimi K2.5 (76.8%, much cheaper) |
| **Bulk cheap analysis** | Kimi K2.5 | $0.60/$2.50, strong reasoning | Gemini 3.1 ($2/$12) |
| **Multi-agent swarm tasks** | Kimi K2.5 | Native Agent Swarm (100 sub-agents) | -- |
| **Video understanding** | Kimi K2.5 | VideoMMMU 86.6%, native multimodal | Gemini 3.1 (native video) |

For full benchmark tables, read `BENCHMARKS.md`.

## Model Profiles

### Claude Opus 4.6 -- "The Investigator"

**Strengths:** Agentic coding, professional analysis, legal reasoning, factual accuracy, computer use, long-form expert work.
**Weaknesses:** Most expensive ($5/$25), 200K context (1M beta), weaker abstract reasoning than Gemini, weaker raw math than GPT.

**Quick prompting tips:**
- Use **XML tags** for structure -- Claude was trained on this: `<instructions>`, `<context>`, `<documents>`
- Use **adaptive thinking** (`effort: high/medium/low`) -- better than manual extended thinking on Opus 4.6
- Put **long documents at the TOP**, query at the BOTTOM (30% improvement measured)
- Explain the **why** behind constraints -- Claude generalizes from explanations
- Soften forceful instructions -- 4.6 overtriggers on "CRITICAL: You MUST..."
- Prefilling is **deprecated** on 4.6 -- use system prompt instructions instead
- Add `"Avoid over-engineering"` for coding tasks -- Opus tends to over-abstract

For complete guide, read `PROMPTING_CLAUDE.md`.

### Claude Sonnet 4.6 -- "The Workhorse"

**Strengths:** Near-Opus coding (79.6% SWE-bench) at 1/5 cost, GDPval 1633 (actually *beats* Opus on expert preference), best speed/intelligence ratio.
**Weaknesses:** May guess tool parameters instead of asking, 64K max output (vs Opus 128K).

**Quick prompting tips:**
- Same XML tag patterns as Opus
- Use **manual extended thinking** with `budget_tokens` (adaptive thinking also works)
- For interleaved thinking (between tool calls): use `interleaved-thinking-2025-05-14` beta header
- Add parameter validation instruction: `"If a required parameter is missing, ask instead of guessing"`
- Set `max_tokens` to 64K at medium/high effort to give room for thinking
- Best at `medium` effort for most applications; `low` for high-volume

For complete guide, read `PROMPTING_CLAUDE.md`.

### GPT-5.2 -- "The Mathematician"

**Strengths:** Math (MATH 98%, AIME 100%), vision (DocVQA 95%), precise instruction compliance (IFEval 95%), structured outputs, 400K context, 90% prompt cache discount.
**Weaknesses:** Highest hallucination (SimpleQA 58%), weakest abstract reasoning (ARC-AGI-2 52.9%), robotic tone.

**Quick prompting tips (thinking mode, high effort):**
- Do **NOT** use "think step by step" -- hurts performance when thinking is on
- Keep prompts **simple and direct** -- the model does heavy reasoning internally
- Use **`strict: true`** on all function definitions -- guaranteed schema conformance
- Use **XML format** for documents: `<doc id='1' title='Title'>Content</doc>` (JSON performs poorly)
- Add `Formatting re-enabled` as first line of developer message (markdown off by default in thinking)
- Enable **web search** for fact-sensitive queries (drops hallucination from 42% to ~5%)
- Use Responses API with `previous_response_id` for **reasoning persistence** across tool calls
- **STATIC prefix (top) + DYNAMIC content (bottom)** for 90% cache discount
- **llmx defaults to `--reasoning-effort high`** for GPT-5 models automatically

For complete guide, read `PROMPTING_GPT.md`.

### Gemini 3.1 Pro -- "The Polymath"

**Strengths:** Science reasoning (GPQA 94.3%), abstract reasoning (ARC-AGI-2 77.1%), 1M native context, cheapest closed frontier ($2/$12), grounding with Google Search.
**Weaknesses:** Worst instruction following (IFEval 89.2%), lower expert preference (GDPval 1317), 64K max output.

**Quick prompting tips:**
- **Keep temperature at 1.0** -- lowering causes looping and degraded reasoning (opposite of Claude/GPT)
- Put **query at the END** after all context -- critical for Gemini
- Place **critical constraints at the END** too -- Gemini 3 drops early constraints
- **Defaults to `thinkingLevel: high`** server-side; thinking **cannot be disabled** on Pro (lowest is `low`)
- Use **`thinkingLevel`**: low/medium/high for Pro (not `thinkingBudget` -- that's Gemini 2.5)
- Default `maxOutputTokens` is only **8,192** -- you must explicitly raise it
- **Grounding with Google Search** reduces hallucination ~40% -- unique capability
- Use **few-shot examples always** -- matters more for Gemini than other models
- Add `"Remember it is 2026"` -- Gemini benefits from explicit date anchoring
- **llmx supports `--reasoning-effort`** for Gemini (maps to thinkingLevel via LiteLLM)

For complete guide, read `PROMPTING_GEMINI.md`.

### Kimi K2.5 -- "The Budget Polymath"

**Strengths:** Exceptional cost efficiency ($0.60/$2.50), strong math (MATH 98%, AIME 96.1%), native multimodal (vision + video), Agent Swarm (100 parallel sub-agents), open weights (modified MIT), LiveCodeBench 85%.
**Weaknesses:** Worst factual accuracy (SimpleQA 37%), verbose outputs inflate real costs, slower (~42 tok/s), weaker writing quality, limited production track record.

**Quick prompting tips:**
- **Thinking mode** (default): use `temperature=1.0`, `top_p=0.95` -- budget 2-4x tokens for reasoning
- **Instant mode** (for speed): `temperature=0.6`, disable thinking with `extra_body={'thinking': {'type': 'disabled'}}`
- **Non-thinking mode is often better for code** -- Moonshot's own guidance says this
- Reasoning traces appear in `response.choices[0].message.reasoning_content`
- OpenAI-compatible API format (`chat.completions`)
- **Agent Swarm** for long-horizon tasks: up to 1,500 tool calls per session
- For vision: set `max_tokens=64k`, average over multiple runs
- **ALWAYS fact-check** -- SimpleQA 37% means 63% factual error rate without tools

For complete guide, read `PROMPTING_KIMI.md`.

## Validation Checklists

Run these when using outputs from each model:

### After Claude Opus/Sonnet 4.6
- [ ] Cross-check mathematical derivations (MATH 93% < GPT's 98%)
- [ ] For novel abstract patterns, consider Gemini second opinion
- [ ] On documents >200K tokens, check for context-edge information loss

### After GPT-5.2
- [ ] **ALWAYS fact-check** (SimpleQA 58% -- hallucinates 42% of factual questions)
- [ ] Don't trust unsourced claims -- demand citations
- [ ] Abstract reasoning may miss non-obvious patterns (ARC-AGI-2 52.9%)

### After Gemini 3.1 Pro
- [ ] Verify it followed instructions precisely (IFEval 89.2% -- misses ~11%)
- [ ] Expert-quality writing may need editing (GDPval 1317 vs Claude 1606)
- [ ] Check output wasn't silently truncated (64K max, 8K default)

### After Kimi K2.5
- [ ] **ALWAYS fact-check** (SimpleQA 37% -- hallucinates 63% of factual questions)
- [ ] Check output length vs. value -- verbose outputs inflate costs 2-4x
- [ ] Writing quality may need significant editing for professional use
- [ ] Verify tool-augmented results independently -- limited production track record

## Cost Comparison

| Model | Input/MTok | Output/MTok | Cache Discount | Context | Max Output |
|-------|:----------:|:-----------:|:--------------:|:-------:|:----------:|
| Claude Opus 4.6 | $5 | $25 | -- | 200K (1M beta) | 128K |
| Claude Sonnet 4.6 | $3 | $15 | -- | 200K (1M beta) | 64K |
| GPT-5.2 | $1.75 | $14 | 90% input | 400K | 100-128K |
| Gemini 3.1 Pro | $2 | $12 | 75% | 1M | 64K |
| Kimi K2.5 | $0.60 | $2.50 | -- | 256K | 96K (thinking) |

**Cost optimization:** Default to Sonnet 4.6 for subagents. Reserve Opus for synthesis, narratives, and orchestration. Use Kimi for bulk work that doesn't need factual precision. This cuts costs 60-80%.

## Multi-Model Architecture Pattern

```
Claude (orchestrator -- best professional judgment)
  ├── Data tools (DuckDB, CLI tools -- ground truth)
  └── Multi-model validation
        ├── pattern   → Gemini 3.1 Pro  [1M context, ARC-AGI-2 77.1%]
        ├── verify    → Gemini 3.1 Pro  [SimpleQA 72.1%, cheap]
        ├── math      → GPT-5.2         [MATH 98%, AIME 100%]
        ├── review    → Gemini 3.1 Pro  [1M context, full-doc review]
        ├── bulk      → Kimi K2.5       [$0.60/$2.50, strong reasoning]
        └── compare   → Multiple        [side-by-side for high-stakes]
```

## The Hallucination Problem

| Model | SimpleQA | Error Rate |
|-------|:--------:|:----------:|
| Claude Opus 4.6 | 72% | 28% wrong |
| Gemini 3.1 Pro | 72.1% | 28% wrong |
| GPT-5.2 | 58% | 42% wrong |
| GPT-5.2 + web search | 95.1% | 5% wrong |
| Kimi K2.5 | 37% | **63% wrong** |

**Key insight:** Reasoning/thinking modes hallucinate MORE on factual questions. Thinking harder helps reasoning over facts, not recall of facts. Always query data sources for dollar amounts, dates, entity names, and legal claims. Kimi is especially dangerous for unsourced factual claims.

## When to Update This Skill

Update after any frontier model release:
1. Update `BENCHMARKS.md` with new scores
2. Update relevant `PROMPTING_*.md` with API/behavior changes
3. Update selection matrix if rankings change
4. Add entry to `CHANGELOG.md`


## Companion: BENCHMARKS.md
# Frontier Model Benchmarks

**Last updated:** 2026-02-27
**Sources:** Artificial Analysis, LLM Stats, SWE-bench.com, LMSYS Chatbot Arena, official docs (Anthropic, OpenAI, Google DeepMind, Moonshot AI).

## Head-to-Head: Current Frontier

| Benchmark | Claude Opus 4.6 | Claude Sonnet 4.6 | GPT-5.2 | Gemini 3.1 Pro | Kimi K2.5 | Measures |
|-----------|:---:|:---:|:---:|:---:|:---:|----------|
| **SWE-bench Verified** | **80.8%** | 79.6% | 80.0% | 80.6% | 76.8% | Real-world coding |
| **GPQA Diamond** | 91.3% | -- | 93.2% | **94.3%** | 87.6% | Graduate science reasoning |
| **AIME 2025** | ~95% | -- | **100%** | ~95% | 96.1% | Competition math |
| **MATH-500** | 93% | -- | **98%** | 91.1% | **98%** | Math problem solving |
| **MMLU** | **92%** | -- | 88% | 85.9% | **92%** | Broad knowledge |
| **MMLU-Pro** | 82% | -- | 83% | **89.5%** | 87.1% | Hard multi-domain reasoning |
| **HumanEval** | **95%** | -- | **95%** | 84.1% | **99%** | Code generation |
| **LiveCodeBench** | 76% | -- | 80% | 73% | **85%** | Up-to-date coding |
| **IFEval** | 94% | -- | **95%** | 89.2% | 94% | Instruction following |
| **SimpleQA** | **72%** | -- | 58% | **72.1%** | 36.9% | Factual accuracy |
| **ARC-AGI-2** | 68.8% | -- | 52.9% | **77.1%** | ~52 | Novel abstract reasoning |
| **Terminal-Bench 2.0** | 65.4% | -- | 60% | **68.5%** | 50.8% | Terminal/CLI tasks |
| **GDPval-AA Elo** | 1606 | **1633** | -- | 1317 | -- | Expert preference |
| **BigLaw Bench** | **90.2%** | -- | -- | -- | -- | Legal reasoning |
| **OSWorld** | **72.7%** | -- | -- | -- | -- | Computer use |
| **BrowseComp** | 84.0% | -- | -- | **85.9%** | 78.4% | Web browsing |
| **HLE (with tools)** | **53.1%** | -- | 45% | 51.4% | 50.2% | Humanity's Last Exam |
| **Chatbot Arena** | #4-8 | -- | #5-6 | **#1** | ~#5 | User preference |
| **Arena: Coding** | **#1** | -- | #3 | #4 | -- | Coding preference |
| **MMMU-Pro (Vision)** | -- | -- | -- | -- | **78.5%** | Multimodal understanding |
| **VideoMMMU** | -- | -- | -- | -- | **86.6%** | Video understanding |

## Pricing

| Model | Input/MTok | Output/MTok | Cache Discount | Context | Max Output |
|-------|:----------:|:-----------:|:--------------:|:-------:|:----------:|
| Claude Opus 4.6 | $5.00 | $25.00 | -- | 200K (1M beta) | 128K |
| Claude Sonnet 4.6 | $3.00 | $15.00 | -- | 200K (1M beta) | 64K |
| GPT-5.2 | $1.75 | $14.00 | 90% input | 400K | 100-128K |
| Gemini 3.1 Pro | $2.00 | $12.00 | 75% | 1M | 64K |
| Kimi K2.5 | $0.60 | $2.50 | -- | 256K | 96K (thinking) |

**Effective cost note:** Kimi K2.5's verbose output style means real-world costs are often 2-4x the per-token price. Budget accordingly.

## Category Winners

| Category | Winner | Score | Key Gap |
|----------|--------|:-----:|---------|
| Agentic coding | Claude Opus 4.6 | 80.8% SWE-bench | +0.2pp over Gemini |
| Expert preference | Claude Sonnet 4.6 | 1633 GDPval | +27 over Opus, +316 over Gemini |
| Factual accuracy | Tie: Claude / Gemini | 72% SimpleQA | +14pp over GPT, +35pp over Kimi |
| Math | GPT-5.2 / Kimi K2.5 | 98% MATH | +5pp over Claude |
| Science reasoning | Gemini 3.1 Pro | 94.3% GPQA | +1.1pp over GPT |
| Abstract reasoning | Gemini 3.1 Pro | 77.1% ARC-AGI-2 | +8.3pp over Claude |
| Instruction following | GPT-5.2 | 95% IFEval | +1pp over Claude/Kimi |
| Legal reasoning | Claude Opus 4.6 | 90.2% BigLaw | No competition |
| Computer use | Claude Opus 4.6 | 72.7% OSWorld | No competition |
| Long context | Gemini 3.1 Pro | 1M native | 5x Claude standard |
| Cost efficiency | Kimi K2.5 | $0.60/$2.50 | 8x cheaper than Opus |
| Code generation | Kimi K2.5 | 99% HumanEval | +4pp over Claude/GPT |
| Video understanding | Kimi K2.5 | 86.6% VideoMMMU | Unique benchmark |
| Multi-agent swarm | Kimi K2.5 | 100 sub-agents | Unique capability |


## Companion: CHANGELOG.md
# Model Guide Changelog

Track what changes with each model release so you know what to update.

## 2026-02-27 -- Initial Creation

**Models covered:** Claude Opus 4.6, Claude Sonnet 4.6, GPT-5.2, Gemini 3.1 Pro, Kimi K2.5.

- Benchmarks sourced from official docs + Artificial Analysis, LLM Stats, SWE-bench.com, LMSYS
- Prompting guides sourced from official docs (Anthropic, OpenAI, Google DeepMind, Moonshot AI)
- Selection matrix, validation checklists, cost comparison, multi-model architecture pattern

### Key data points at creation
- Claude Opus 4.6: released Feb 5, 2026. Prefill deprecated. Adaptive thinking recommended over manual.
- Claude Sonnet 4.6: released Feb 5, 2026. GDPval 1633 (beats Opus). Interleaved thinking via beta header.
- GPT-5.2: released Dec 11, 2025. MATH 98%, SimpleQA 58%. Web search drops errors to 5%.
- Gemini 3.1 Pro: released Feb 19, 2026. Uses `thinkingLevel` not `thinkingBudget`. Temperature must stay 1.0.
- Kimi K2.5: released Jan 26, 2026. Open-weight MoE (1T/32B active). SimpleQA 37% (worst). Agent Swarm unique.

### Design decisions
- Focused on current frontier only (no legacy models like GPT-4.1, Gemini 2.5, DeepSeek)
- One prompting guide per model family for easy updates
- BENCHMARKS.md is the most frequently updated file

## Update Checklist

When a new frontier model releases:

1. [ ] Update `BENCHMARKS.md` -- new scores, pricing, context limits
2. [ ] Update relevant `PROMPTING_*.md` -- API changes, new features, deprecated features
3. [ ] Update `SKILL.md` selection matrix if rankings change
4. [ ] Update `SKILL.md` cost table
5. [ ] Add changelog entry with date and key changes
6. [ ] Consider whether any model should be added or removed from coverage


## Companion: PROMPTING_CLAUDE.md
# Claude Prompting Guide

Specific to Claude Opus 4.6 and Sonnet 4.6. Updated 2026-02-27.

**Sources:** Anthropic official docs (platform.claude.com/docs), Claude Code system prompt analysis.

---

## 1. XML Tags -- Claude's Signature Technique

Claude was specifically trained to parse and respect XML structure. This is the single most important Claude-specific technique.

```xml
<documents>
  <document index="1">
    <source>filename.pdf</source>
    <document_content>{{CONTENT}}</document_content>
  </document>
</documents>

<instructions>
Your task is to analyze the documents above.
</instructions>
```

**Patterns that work:**
- `<instructions>`, `<context>`, `<input>`, `<example>`, `<documents>` for content types
- `<thinking>` and `<answer>` to separate reasoning from output
- `<example>` / `<examples>` to distinguish examples from instructions
- Nested tags for hierarchy: `<documents>` > `<document index="1">` > `<source>` + `<document_content>`
- Steering formatting: `"Write in <smoothly_flowing_prose> tags"` works better than `"Don't use markdown"`

---

## 2. Thinking & Reasoning Modes

### Adaptive Thinking (Recommended for Opus 4.6)

```python
client.messages.create(
    model="claude-opus-4-6",
    max_tokens=64000,
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},  # max, high, medium, low
    messages=[...]
)
```

| Effort | Behavior |
|--------|----------|
| `max` | Opus 4.6 only. Always thinks, no constraints |
| `high` | Always thinks, deep reasoning (default) |
| `medium` | Moderate thinking, may skip on simple queries |
| `low` | Minimizes thinking, skips on simple tasks |

Adaptive mode automatically enables **interleaved thinking** (thinking between tool calls). Manual extended thinking on Opus 4.6 does NOT support interleaved thinking -- always use adaptive for agentic workflows.

### Manual Extended Thinking (Sonnet 4.6 only)

```python
client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=16384,
    thinking={"type": "enabled", "budget_tokens": 16384},
    messages=[...]
)
```

For Sonnet 4.6 interleaved thinking, use the `interleaved-thinking-2025-05-14` beta header.

### Prompt-Level Chain-of-Thought (when thinking is off)

- Use `<thinking>` and `<answer>` tags
- Say "think thoroughly" rather than prescribing steps -- Claude's reasoning often exceeds prescriptions
- Include `<thinking>` tags in few-shot examples -- Claude generalizes the pattern
- Add self-check: `"Before finishing, verify your answer against [criteria]"`

### Controlling Overthinking

Opus 4.6 does significantly more upfront exploration than previous models. Counter with:

```
When deciding how to approach a problem, choose an approach and commit to it.
Avoid revisiting decisions unless you encounter new information that directly
contradicts your reasoning.
```

---

## 3. System Prompts & Role Setting

- Set roles in the **system prompt**, not user message
- Claude 4.6 is **more responsive to system prompts** than older models -- soften forceful language:
  - Bad: `"CRITICAL: You MUST use this tool when..."`
  - Good: `"Use this tool when..."`
- **Explain the why** behind constraints:
  - Bad: `"Never use ellipses"`
  - Good: `"Your response will be read aloud by TTS, so never use ellipses since the engine can't pronounce them"`
  - Claude generalizes from explanations better than from bare rules

---

## 4. Long Context Best Practices

200K standard, 1M beta for Opus/Sonnet 4.6.

**Critical rule:** Put **long documents at the TOP**, query/instructions at the **BOTTOM**. Measured 30% improvement.

```xml
<documents>
  <!-- Long content here -->
</documents>

<!-- Query and instructions at the end -->
Based on the documents above, analyze...
```

**Ground responses in quotes:** For long docs, ask Claude to extract relevant quotes first:

```
Find relevant quotes from the documents. Place these in <quotes> tags.
Then, based on these quotes, provide your analysis in <info> tags.
```

---

## 5. Prefilling -- DEPRECATED on 4.6

Starting with Claude 4.6, prefilled responses on the last assistant turn are no longer supported.

**Migration paths:**
- Format control: Use system prompt instructions or structured output via tool schemas
- Eliminating preambles: `"Respond directly without preamble. Do not start with 'Here is...', 'Based on...'"`
- Continuations: Move to user message: `"Your previous response ended with [text]. Continue from where you left off."`

---

## 6. Tool Use

### Description Quality
Write **detailed, specific descriptions** for each tool and parameter. Short descriptions reduce accuracy. Include examples in parameter descriptions.

### Model-Tier Differences
- **Opus** asks for missing required parameters
- **Sonnet/Haiku** may **guess** values -- add this for Sonnet/Haiku:
  ```
  Before calling a tool, think about whether the user has provided enough
  information for all required parameters. If missing, ask instead of guessing.
  ```

### Parallel Tool Calls
Claude 4.6 excels at parallel execution. Boost to ~100% with:
```xml
<use_parallel_tool_calls>
If you intend to call multiple tools and there are no dependencies between
the calls, make all independent calls in parallel.
</use_parallel_tool_calls>
```

### Action vs. Suggestion
Claude interprets "Can you suggest changes?" as a request for suggestions, not action.
- For action: use imperative language: `"Change this function to improve performance"`
- For proactive tool use: `"By default, implement changes rather than only suggesting them"`
- For conservative behavior: `"Do not jump into implementation unless clearly instructed"`

---

## 7. Output Formatting

- Tell Claude what **TO do**, not what **NOT to do**:
  - Bad: `"Do not use markdown"`
  - Good: `"Compose your response in smoothly flowing prose paragraphs"`
- Match your prompt style to desired output -- if your prompt has no markdown, Claude produces less
- **Opus 4.6 defaults to LaTeX** for math. Prevent with: `"Format in plain text only. Do not use LaTeX."`
- **4.6 is more concise** than previous models. May skip summaries after tool calls. For verbosity: `"After completing tool use, provide a quick summary"`

---

## 8. Known Pitfalls

| Pitfall | Solution |
|---------|----------|
| Overtriggering on tools/skills | Soften forceful instructions -- 4.6 is more responsive |
| Overengineering code | `"Only make changes that are directly requested. Don't add features beyond what was asked."` |
| Hallucinating about unread code | `"Never speculate about code you have not opened. Read the file before answering."` |
| Hard-coding test values | `"Implement a solution that works for all valid inputs, not just test cases."` |
| Excessive subagent spawning (Opus 4.6) | `"For simple tasks, single-file edits, or sequential operations, work directly."` |
| Excessive file creation | `"If you create temporary files, clean them up at the end."` |
| Opus 4.5 sensitivity to "think" | Use "consider", "evaluate", "reason through" when thinking is disabled (4.5 only) |

---

## 9. Opus vs. Sonnet Selection

| Model | Best For | Effort Setting |
|-------|----------|---------------|
| **Opus 4.6** | Large-scale migrations, deep research, extended autonomous work, highest reasoning, 128K output | `max` or `high` |
| **Sonnet 4.6** | Agentic coding, tool-heavy workflows, most applications (best speed/intelligence ratio) | `medium` for most; `low` for high-volume |

**Upgrade to Opus when:** large-scale code migrations, deep research, extended autonomous work, problems requiring highest reasoning quality, or when you need >64K output.

**Sonnet tip:** Set max_tokens to 64K at medium/high effort to give room for thinking. Sonnet's GDPval (1633) actually beats Opus (1606) on expert preference -- it's not always a downgrade.

---

## 10. Agentic Patterns

### Context Awareness
Claude 4.5+ tracks remaining context. Tell it about infrastructure:
```
Your context window will be automatically compacted as it approaches its limit.
Do not stop tasks early due to token budget concerns. Save progress to memory
before context refreshes.
```

### Multi-Context-Window Workflows
1. First window: set up framework (write tests, setup scripts)
2. Subsequent windows: iterate on todo-list
3. Write tests in structured format before starting work
4. Use git for state tracking across sessions
5. Starting fresh often beats compacting -- 4.6 rediscovers state from filesystem

### Safety Guardrails
Opus 4.6 may take irreversible actions without asking:
```
For actions that are hard to reverse, affect shared systems, or could be
destructive, ask the user before proceeding.
```

### Prompt Chaining
Most useful pattern: **generate -> review against criteria -> refine**. Each step as a separate API call lets you inspect, log, or branch.

---

## 11. Vision

- 4.5+ and 4.6 have improved multi-image processing
- Give Claude a "crop tool" to zoom into image regions -- consistent uplift measured
- Analyze videos by breaking into frames

---

## 12. Frontend Design

Claude defaults to generic aesthetics. Counter with:
```xml
<frontend_aesthetics>
Avoid generic fonts (Inter, Roboto, Arial). Choose distinctive typography.
Commit to a cohesive color palette. Use CSS animations for micro-interactions.
Avoid purple gradients on white backgrounds.
</frontend_aesthetics>
```


## Companion: PROMPTING_GEMINI.md
# Gemini 3.1 Pro Prompting Guide

Specific to Gemini 3.1 Pro (and Gemini 3 Flash where noted). Updated 2026-02-27.

**Sources:** Google AI official docs (ai.google.dev, cloud.google.com/vertex-ai).

---

## 1. Temperature -- DO NOT LOWER IT

The single biggest behavioral difference from every other frontier model:

> **Keep temperature at the default value of 1.0.**

Lowering temperature on Gemini causes **looping, degraded performance, and broken reasoning** -- especially on math and complex tasks. This is the opposite of Claude/GPT convention.

If you need deterministic output, use structured output with response schemas instead.

---

## 2. Query and Constraint Placement

Two critical rules that differ from other models:

1. **Put your query at the END** of the prompt, after all context. Use transition phrases: `"Based on the information above..."`
2. **Put critical constraints at the END** too -- Gemini 3 may drop early constraints in complex prompts

This is the opposite of Claude (where instructions can go at top) and matters more for Gemini than any other model.

---

## 3. Output Token Pitfall

**The default `maxOutputTokens` is only 8,192.** You must explicitly raise it:

```python
generation_config = {"max_output_tokens": 65536}
```

Without this, responses **silently truncate** at ~8K tokens. Check `finishReason`:
- `STOP` = model decided it was done
- `MAX_TOKENS` = hit the limit (increase maxOutputTokens)
- `SAFETY` = content filtered

**Thinking tokens consume your output budget.** At `thinkingLevel: "high"`, 18,000-30,000 tokens go to internal reasoning, leaving only ~35,000-47,000 for visible output. Use `thinkingLevel: "low"` if you need maximum visible output.

---

## 4. Thinking Mode

### Default Behavior (Confirmed from API)

**Gemini 3.1 Pro defaults to `thinkingLevel: high` when not specified.** Thinking **cannot be disabled** on Pro -- the lowest available is `low`. The `minimal` level is Flash-only.

### `thinkingLevel` (Gemini 3 series)

| Level | Gemini 3.1 Pro | Gemini 3 Flash | Use Case |
|-------|:-:|:-:|----------|
| `minimal` | Not supported | Supported | Approximates no thinking (Flash only) |
| `low` | **Supported** | Supported | Minimize latency/cost for straightforward tasks |
| `medium` | **Supported** | Supported | Balanced reasoning |
| `high` | **Default** | **Default** | Complex math, multi-step coding, advanced reasoning |

### API Parameter

```python
# Google SDK
config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_level="low")
)

# Via llmx (maps --reasoning-effort to thinkingConfig via LiteLLM)
llmx -m gemini-3-pro-preview --reasoning-effort low "simple query"
llmx -m gemini-3-pro-preview "complex query"  # Defaults to high server-side
```

### Best Practices
- **Replace explicit chain-of-thought prompting** with `thinkingLevel: "high"` -- model handles decomposition internally
- For lengthy outputs, use `thinkingLevel: "low"` to reserve tokens for visible output
- Include verification: `"Verify your sources, review your reasoning, identify errors, check your final answer"`
- Access thought summaries with `includeThoughts: true`
- **Thought signatures** (Gemini 3): encrypted tokens that must be passed back in multi-turn conversations to maintain reasoning context
- **Do NOT use `thinkingBudget`** (Gemini 2.5 parameter) with Gemini 3.x -- use `thinkingLevel` instead. Mixing them returns a 400 error.

---

## 5. System Instructions

Gemini 3 favors structured system instructions. XML tags work well:

```xml
<role>
You are a specialized assistant for [Domain].
</role>

<instructions>
1. Plan: Break tasks into sub-tasks
2. Execute: Carry out plans, reflecting before tool calls
3. Validate: Review output against requirements
</instructions>

<constraints>
- Verbosity: [Low/Medium/High]
- Tone: [Formal/Casual/Technical]
</constraints>
```

### Gemini-Specific Tips
- Add: `"Remember it is 2026 this year"` -- Gemini benefits from explicit date anchoring
- Add: `"Your knowledge cutoff date is [date]"` to prevent hallucination
- For grounded responses: `"The provided context is the only source of truth for this session"`
- **Gemini 3 is less verbose by default** -- explicitly request chattier tone if needed

---

## 6. Grounding with Google Search

Unique Gemini capability -- no equivalent in Claude, GPT, or Kimi APIs.

```python
grounding_tool = types.Tool(google_search=types.GoogleSearch())
config = types.GenerateContentConfig(tools=[grounding_tool])
```

- Model auto-generates and executes search queries
- Returns `groundingMetadata` with `webSearchQueries`, `groundingChunks` (sources), `groundingSupports` (inline citations)
- Reduces hallucinations by ~40%
- Use temperature 1.0 with grounding
- Gemini 3: billed per search query executed
- **Cannot combine built-in tools (Google Search, Code Execution) with custom function calling in the same request**

---

## 7. Function Calling / Tool Use

### Tool Configuration Modes

| Mode | Behavior |
|------|----------|
| `AUTO` (default) | Model decides between text or function calls |
| `ANY` | Always generates function calls; restrict with `allowed_function_names` |
| `NONE` | Disables function calling |
| `VALIDATED` (Preview) | Ensures schema adherence |

### Best Practices
- Description quality is paramount -- model relies on descriptions to choose functions
- Use `enum` for fixed value sets (dramatically improves accuracy)
- **10-20 tools maximum** -- more causes confusion
- Parallel and chained calling both supported
- Pass thought signatures back in multi-turn function calling
- MCP support built into Python and JavaScript SDKs

---

## 8. Long Context (1M Tokens Native)

Gemini's biggest advantage -- 5x Claude standard, 2.5x GPT-5.2.

### Structure
- **Query at the END** after all context (critical for Gemini)
- Use transition: `"Based on the information above..."`
- **Favor direct inclusion over RAG** -- Gemini's in-context learning is powerful with complete materials
- Place instructions at both **beginning and end** (boundary effect)

### Performance
- ~99% accuracy on single needle-in-haystack retrieval
- Accuracy degrades when searching for **multiple** pieces simultaneously
- Use structured formats (JSON, XML, Markdown headers) to organize large contexts
- Explicitly name the document or section when asking about specific content

---

## 9. Context Caching (75% Discount)

### Two Types

| Type | Setup | Savings |
|------|-------|---------|
| **Implicit** (automatic) | Enabled by default | Automatic, no guarantees |
| **Explicit** (manual) | Developer creates and references caches | Guaranteed reduced rate |

### Minimum Tokens
- Gemini 3.1 Pro: 4,096 tokens
- Gemini 3 Flash: 1,024 tokens

### Structure for Maximum Savings
- Cached content works as a **prompt prefix** -- stable content at front
- Variable content (user query) goes after cached prefix
- Default TTL: 1 hour; customizable
- Cacheable: system instructions, video/PDF/text files, tool definitions

---

## 10. Structured Output / JSON

```python
config = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_json_schema=your_schema
)
```

### Key Rules
- Use clear `description` fields for every property -- guides model output
- Use `enum` for any field with fixed values
- **Syntactic correctness is guaranteed; semantic correctness is NOT** -- validate in app code
- Can combine with Google Search, URL Context, Code Execution, Function Calling

---

## 11. Multimodal

### Media Ordering
- Place media (images, video, audio) **before** text instructions
- Reference specific modalities explicitly

### Capacity
- Up to 8.4 hours of audio per prompt (~1M tokens)
- Up to 3,600 images per prompt (~1M tokens)

### Media Resolution Control
`media_resolution` parameter: `low`, `medium`, `high`, `ultra_high`
- Use `high` for document parsing
- Ask model to describe the image first, then perform analysis (pre-analysis step)

---

## 12. Few-Shot Examples

Official Gemini guidance emphasizes few-shot more strongly than other models:
- **Always include few-shot examples** for complex tasks
- 3-5 diverse, relevant examples
- Show both input and expected output format
- Include edge cases in examples

---

## 13. Key Differences from Claude/GPT/Kimi

| Aspect | Gemini 3.1 | Claude 4.6 | GPT-5.2 | Kimi K2.5 |
|--------|-----------|-----------|---------|-----------|
| Temperature | Keep at 1.0 (lowering degrades) | Lower OK | Lower OK | 1.0 thinking, 0.6 instant |
| Query placement | END (critical) | Bottom (30% better) | End preferred | Flexible |
| Output default | 8,192 (must raise!) | Higher | Higher | 4,096 (must raise) |
| Grounding | Native Google Search | Not available | Web search available | Not available |
| Context | **1M native** | 200K (1M beta) | 400K | 256K |
| Instruction following | Weakest (89.2%) | Strong (94%) | Best (95%) | Strong (94%) |
| Expert preference | Lower (1317) | Highest (1606) | Middle | -- |
| Constraint placement | END of prompt | Flexible | Both beginning and end | Flexible |
| Few-shot importance | Strongly recommended | Helpful | Helpful | Helpful |


## Companion: PROMPTING_GPT.md
# GPT-5.2 Prompting Guide

Specific to GPT-5.2 with thinking (high effort). Updated 2026-02-27.

**Sources:** OpenAI official docs (developers.openai.com).

---

## 1. Thinking Mode -- The Default

GPT-5.2 with thinking enabled at high effort is the version that hits the frontier benchmarks (MATH 98%, AIME 100%, DocVQA 95%). Always use thinking mode for non-trivial work.

### Critical Rules

**Do NOT use chain-of-thought prompting** ("think step by step") -- the model reasons internally. Explicit CoT scaffolding **hurts performance** when thinking is on.

**DO:**
- Keep prompts simple and direct -- the model does the heavy reasoning internally
- Use delimiters (markdown, XML) for structure
- Start with zero-shot; add few-shot only if needed
- Let the model allocate its own reasoning budget

**DO NOT:**
- Ask it to "explain your reasoning" or "show your work"
- Prescribe step-by-step plans -- the model's internal reasoning exceeds what you'd prescribe
- Over-engineer prompts with CoT scaffolding or "think carefully" instructions

### Effort Levels

```python
# Direct API
response = client.responses.create(
    model="gpt-5.2",
    reasoning={"effort": "high"},  # minimal, low, medium, high
    input=[...]
)
```

```bash
# Via llmx (our unified CLI) -- defaults to high effort for GPT-5 models
llmx -m gpt-5-pro "complex query"                                  # Defaults to --reasoning-effort high
llmx -m gpt-5-pro --reasoning-effort high --stream "complex query"  # Explicit (same result)
llmx -m gpt-5-pro --reasoning-effort low "simple query"             # Override for speed/cost
```

| Effort | Use When | llmx auto-timeout |
|--------|----------|:-:|
| `high` | Complex reasoning, math, analysis, coding -- **use this for serious work** | 600s (10 min) |
| `medium` | Balanced cost/quality for moderate tasks | 300s (5 min) |
| `low` | Moderate queries, cost-sensitive | 120s |
| `minimal` | Simple queries, high-volume, latency-sensitive | 120s |

### Reasoning Persistence

Use the Responses API with `store: true` and pass `previous_response_id`. This preserves internal reasoning state across tool calls, directly improving accuracy on multi-step tasks. The Chat Completions API does NOT preserve reasoning items, increasing token usage and reducing quality.

### Markdown in Thinking Mode

Thinking mode **disables markdown by default**. To re-enable, add as the first line of your developer message:

```
Formatting re-enabled
```

---

## 2. Message Roles

OpenAI defines a strict authority chain: `developer` > `user` > `assistant`.

- The `developer` message (formerly "system message") carries highest priority
- Do NOT use both `developer` and `system` in the same request
- Think of developer and user messages like a function and its arguments

**Recommended developer message structure:**
1. Identity and communication style
2. Instructions, rules, function-calling guidance
3. Examples (input/output pairs)
4. Context and reference data (near end)

---

## 3. Structured Outputs & JSON

GPT-5.2 has the best native structured output support of any frontier model.

### The Hierarchy

| Method | Schema Enforced | Use When |
|--------|:-:|----------|
| **Structured Outputs** (`response_format`) | Guaranteed | Final-step extraction, no back-and-forth |
| **Function Calling** (`strict: true`) | Guaranteed | External API calls, model chooses among tools |
| **JSON Mode** | Valid JSON only | **Not recommended** -- always prefer Structured Outputs |

### Key Rules

- **Always enable `strict: true`** -- requires `additionalProperties: false`
- **Structured Outputs is incompatible with parallel function calls.** Set `parallel_tool_calls: false`
- Use Pydantic (Python) or Zod (JavaScript) for schema definitions
- Prevents schema violations but NOT value errors -- add examples for semantic correctness
- Use `anyOf` for union types; all fields must be required (use nullable instead of optional)

---

## 4. Long Context (400K tokens)

### Document Formatting

Use **XML format** for multiple documents (best performing with GPT-5.2 thinking):
```xml
<doc id='1' title='Annual Report'>Content here</doc>
<doc id='2' title='Competitor Analysis'>Content here</doc>
```

- JSON performs **poorly** for large document sets
- Pipe-delimited (`ID|TITLE|CONTENT`) is a solid alternative
- For maximum thoroughness, place key instructions at **both beginning and end** of the prompt

---

## 5. Hallucination -- The #1 Risk

GPT-5.2 has **58% SimpleQA** -- it hallucinates 42% of factual questions. Even with thinking enabled, factual recall is its weakest category among frontier models.

**The core problem:** GPT almost never refuses to answer (2% not-attempted rate on SimpleQA). It will **confidently fabricate** rather than say "I don't know." Thinking mode improves reasoning but does NOT fix factual recall.

### With Thinking Enabled
- Medical cases (HealthBench): 1.6% error rate vs GPT-4o's 15.8% -- thinking helps enormously for *reasoning over* provided facts
- But SimpleQA factual recall is still 58% -- thinking doesn't help *remembering* facts
- GPT-5.2 is ~80% less likely to have reasoning errors than o3 -- but factual errors persist

### Mitigation Techniques

1. **Enable web search** for fact-sensitive queries -- drops error to ~5% (SimpleQA 95.1%). This is the single most impactful mitigation.
2. **Ask for citations inline** -- forces two errors to hallucinate (fact + fabricated citation)
3. **Provide grounding context** -- the closer source material is to the desired answer, the less it invents
4. **Give an "out":** `"Respond with 'not found' if the answer isn't present in the documents"`
5. **Use Structured Outputs** with mandatory fields for confidence/source
6. **Cross-validate** with Claude or Gemini (both at 72% SimpleQA) for fact-sensitive claims

---

## 6. Prompt Caching (Up to 90% Input Cost Reduction)

### How It Works
- **Automatic** -- no code changes required
- Minimum **1,024 tokens** to activate
- Matches in **128-token blocks** -- exact prefix match until first mismatch
- Reduces latency up to 80%, input costs up to 90%

### Maximize Cache Hits

**STATIC PREFIX (top) -> DYNAMIC CONTENT (bottom)**

1. Developer message, instructions, tool definitions, examples, schemas at **top**
2. User-specific, variable content at **bottom**
3. **Never put timestamps or request IDs early** -- invalidates cache
4. Images, tool definitions, schemas all cacheable but must be **identical**

### `prompt_cache_key` Parameter
- Improved one customer's hit rate from 60% to 87%
- Keep each prefix + key combo under ~15 requests/minute

### Cache Retention

| Type | Duration |
|------|----------|
| In-Memory | 5-10 min idle, max 1 hour |
| Extended (24h) | Up to 24 hours (GPT-5.2 supported) |

Monitor: check `usage.prompt_tokens_details.cached_tokens` in API response.

---

## 7. Tool / Function Calling

- Write **detailed, specific** function descriptions -- clear descriptions scored **6% higher** than verbose alternatives
- Flatten deeply nested parameter structures -- flat schemas reduce parsing errors
- Under ~100 tools and ~20 arguments per tool is in-distribution
- Add: `"Do NOT promise to call a function later. If required, emit it now."` -- GPT thinking mode may defer tool calls otherwise
- Use `strict: true` for reliable schema adherence
- With thinking enabled and Responses API, reasoning persistence significantly improves tool selection across multi-step workflows

---

## 8. Vision

GPT-5.2 with thinking is **best-in-class for document understanding**:
- DocVQA: 95% (best of any frontier model)
- ScreenSpot-Pro: 86.3% (best UI element detection)

| Detail Setting | Tokens | Use Case |
|---------------|:------:|----------|
| `low` | 85 fixed | Quick classification, cost optimization |
| `high` | 170 + 129/tile | OCR, fine detail, small text |
| `auto` (default) | Model decides | General use |

- Max input: 50 MB, 10 images per call
- For text in images: spell out tricky names letter by letter
- Video and audio input supported natively

---

## 9. Key Differences from Claude/Gemini/Kimi

| Aspect | GPT-5.2 (thinking) | Claude 4.6 | Gemini 3.1 | Kimi K2.5 |
|--------|---------|-----------|-----------|-----------|
| Structured Outputs | Native, guaranteed | Tool_use workaround | Via function calling | OpenAI-compatible |
| Prompt caching | Automatic, 90% off | Manual markers | Automatic, 75% off | None |
| Thinking control | `reasoning.effort` (low/med/high) | `output_config.effort` (low-max) | `thinkingLevel` (minimal-high) | On/off toggle |
| CoT prompting | **Hurts** when thinking on | Helps (`<thinking>` tags) | Replace with thinkingLevel | Use thinking mode |
| Reasoning persistence | `previous_response_id` | Adaptive interleaved | Thought signatures | Not available |
| Hallucination | Poor (SimpleQA 58%) | Best tied (72%) | Best tied (72.1%) | Worst (37%) |
| Refusal rate | Almost never refuses (2%) | More selective | More selective | Moderate |
| Math | **Best** (MATH 98%, AIME 100%) | 93% | 91.1% | 98%, AIME 96% |
| Vision/OCR | **Best** (DocVQA 95%) | Good (93%) | Good | Good (MMMU-Pro 78.5%) |
| Medical reasoning | **Best** (1.6% HealthBench error) | Good | Good | -- |
| Web search grounding | Available (SimpleQA -> 95.1%) | Not available | Google Search native | Not available |


## Companion: PROMPTING_KIMI.md
# Kimi K2.5 Prompting Guide

Specific to Kimi K2.5 (Moonshot AI). Updated 2026-02-27.

**Sources:** Moonshot AI official docs (platform.moonshot.ai), Hugging Face model card, community benchmarks.

---

## 1. Two Modes: Thinking vs. Instant

Kimi K2.5 has two distinct operating modes with different optimal settings:

### Thinking Mode (default -- for hard problems)

```python
response = client.chat.completions.create(
    model="kimi-k2.5",
    messages=messages,
    temperature=1.0,
    top_p=0.95,
    max_tokens=4096
)
# Reasoning trace: response.choices[0].message.reasoning_content
# Final answer: response.choices[0].message.content
```

- Budget 2-4x the tokens of a standard response for reasoning
- AIME/MATH benchmarks used a 96K token completion budget
- Best for: math, science reasoning, complex analysis

### Instant Mode (for speed/cost)

```python
response = client.chat.completions.create(
    model="kimi-k2.5",
    messages=messages,
    temperature=0.6,
    top_p=0.95,
    max_tokens=4096,
    extra_body={'thinking': {'type': 'disabled'}}
)
```

- Best for: simple queries, code generation, high-volume work

**Important:** Non-thinking mode is often **better for code** than thinking mode. Moonshot's own guidance says this. Test both for your use case.

---

## 2. API Compatibility

Kimi K2.5 uses the **OpenAI-compatible** `chat.completions` format:

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-key",
    base_url="https://api.moonshot.ai/v1"  # Official
    # Or: "https://openrouter.ai/api/v1" (OpenRouter)
    # Or: "https://api.together.xyz/v1" (Together AI)
)
```

Model ID: `kimi-k2.5` (official) or `moonshotai/kimi-k2.5` (third-party providers)

---

## 3. Output Token Defaults

Like Gemini, Kimi has a **low default max output**:
- General chat: 4,096 tokens
- Vision tasks: 8,192-64K tokens
- Thinking mode: up to 96K tokens (completion budget)

**Always set `max_tokens` explicitly** for non-trivial tasks. The 256K context window is shared between input and output.

---

## 4. Verbosity Problem

Kimi K2.5 generates **excessively long responses**. This inflates real-world costs 2-4x beyond what token pricing suggests.

**Mitigation:**
- Add explicit length constraints: `"Answer in 3 sentences"` or `"Respond concisely"`
- Use structured output (JSON schema) to constrain response format
- For bulk work, factor in 2-4x cost multiplier when budgeting

---

## 5. Hallucination -- The Biggest Risk

**SimpleQA: 36.9%** -- Kimi hallucinates 63% of factual questions. This is the worst of any current frontier model.

### Mitigation
1. **Never use for unsourced factual claims** -- always ground with tool calls or documents
2. **Pair with tool augmentation** -- Kimi gains +20.1pp with tools (more than any competitor)
3. **Cross-validate** with Claude or Gemini (both at 72% SimpleQA) for fact-sensitive work
4. **Structured output** with mandatory source/confidence fields

Kimi is excellent for **reasoning over provided data** but dangerous for **generating facts from memory**.

---

## 6. Tool / Function Calling

OpenAI-compatible `tools` array format:

```python
tools = [{
    "type": "function",
    "function": {
        "name": "search",
        "description": "Search for information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    }
}]
```

- Strict function calling supported
- JSON schema response format supported (`response_format` with `json_schema` type)
- Kimi gains the most from tool augmentation of any frontier model (+20.1pp)
- Include system prompts emphasizing `"deep and proactive tool use"` for agentic tasks

---

## 7. Agent Swarm (Unique Capability)

No other frontier model has this natively:

- Up to **100 parallel sub-agents** per session
- Up to **1,500 tool calls** per session
- Trained via Parallel-Agent Reinforcement Learning (PARL)
- 4.5x faster than single-agent on long-horizon tasks
- 80% runtime reduction on complex tasks

Available via the Moonshot platform (not raw API). Best for:
- Large-scale data gathering
- Multi-source research
- Long-horizon tasks with many independent subtasks

---

## 8. Vision & Video

Kimi K2.5 was pre-trained from scratch on 15T mixed visual+text tokens (not bolted on post-hoc).

### Images
```python
messages = [{
    "role": "user",
    "content": [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
        # or {"url": "https://example.com/image.png"}
        {"type": "text", "text": "Describe this image"}
    ]
}]
```

### Video (Experimental)
- Only available via official API (not third-party providers)
- Use `video_url` content type with base64 encoding
- VideoMMMU: 86.6% -- best-in-class video understanding

### Tips
- Set `max_tokens=64000` for vision tasks
- Average over multiple runs for consistency
- MMMU-Pro 78.5%, OCRBench 92.3%

---

## 9. Coding

- HumanEval: 99% (best of any frontier model)
- LiveCodeBench: 85% (best of any frontier model)
- SWE-bench: 76.8% (trails Claude/GPT/Gemini by 3-4pp)

**Key insight:** Instant mode (thinking disabled) often produces **better code** than thinking mode. Test both.

For complex multi-file coding tasks, SWE-bench gap matters -- prefer Claude Opus/Sonnet for real-world codebase work.

---

## 10. Architecture Notes

Understanding the architecture helps with prompting:

- **MoE (Mixture of Experts):** 1T total params, only 32B activated per token
- **384 experts, 8 selected per token** -- fast inference despite massive parameter count
- **MoonViT vision encoder:** 400M params, native multimodal
- **Modified MIT License:** Free for commercial use; attribution required above 100M MAU or $20M/month revenue

---

## 11. Gotchas

| Gotcha | Detail |
|--------|--------|
| Thinking API parameter differs by deployment | Official API: `extra_body={'thinking': {'type': 'disabled'}}`. Self-hosted vLLM: `extra_body={'chat_template_kwargs': {"thinking": False}}`. Confusing them silently fails. |
| Verbose outputs inflate costs | Budget 2-4x the per-token price for real-world usage |
| Self-hosting is impractical | 1T MoE requires all 384 expert weights in memory. Consumer hardware runs ~100x slower than H100 clusters |
| Video is experimental | Only via official API, not third-party providers |
| Attribution required | Must display "Kimi K2.5" in UI built on the model |
| SimpleQA is 37% | Worst factual accuracy of any frontier model. Never trust unsourced claims |
| Limited production track record | Minimal real-world deployments, smaller developer ecosystem vs Claude/GPT/Gemini |

---

## 12. Key Differences from Claude/GPT/Gemini

| Aspect | Kimi K2.5 | Claude 4.6 | GPT-5.2 | Gemini 3.1 |
|--------|-----------|-----------|---------|-----------|
| Price (in/out MTok) | **$0.60/$2.50** | $5/$25 | $1.75/$14 | $2/$12 |
| Thinking control | On/off toggle | Adaptive effort | Integrated | thinkingLevel |
| Code (thinking off) | Often better | N/A | N/A | N/A |
| Factual accuracy | Worst (37%) | Best tied (72%) | Poor (58%) | Best tied (72%) |
| Tool augmentation gain | **+20.1pp** (biggest) | Moderate | Moderate | Moderate |
| Agent swarm | **Native (100 agents)** | Not native | Not native | Not native |
| Video | **Native** | Not supported | Not supported | Supported |
| API format | OpenAI-compatible | Anthropic SDK | OpenAI native | Google SDK |
| Open weights | **Yes** (modified MIT) | No | No | No |
| Writing quality | Weakest | Best | Good | Good |

---
# SKILL: model-review

---
name: model-review
description: Cross-model adversarial review via llmx. Dispatches architecture, code, or design decisions to Gemini 3.1 Pro and GPT-5.2 for independent critique, then fact-checks and synthesizes surviving insights. Supports review mode (convergent/critical) and brainstorming mode (divergent/creative).
argument-hint: [topic or decision to review — e.g., "selve search architecture", "authentication redesign"]
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Task
---

# Cross-Model Adversarial Review

You are orchestrating a cross-model review. Same-model peer review is a martingale — no expected correctness improvement (ACL 2025, arXiv:2508.17536). Cross-model review provides real adversarial pressure because models have different failure modes, training biases, and blind spots.

## Prerequisites

- `llmx` CLI installed (`which llmx`)
- API keys configured for Google (Gemini) and OpenAI (GPT)
- Gemini Flash for fact-checking (`llmx -m gemini-3-flash-preview`)

## Pre-Flight: Constitutional Check

Before building context, check if the project has constitutional documents:

```bash
# Check for project principles
CONSTITUTION=$(find . ~/Projects/intel/docs -maxdepth 3 -name "CONSTITUTION.md" 2>/dev/null | head -1)
GOALS=$(find . ~/Projects/intel/docs -maxdepth 3 -name "GOALS.md" 2>/dev/null | head -1)
```

- **If CONSTITUTION.md exists:** Inject as preamble into ALL context bundles. Instruct models to review against project principles, not their own priors.
- **If GOALS.md exists:** Inject into GPT context (quantitative alignment check) and Gemini context (strategic coherence).
- **If neither exists:** Warn the user: *"No CONSTITUTION.md or GOALS.md found. Reviews will lack project-specific anchoring. Consider `/constitution` or `/goals` first."* Proceed anyway — cross-model review still has value without constitutional grounding.

## Mode Selection

Choose the mode BEFORE building context. These are cognitively different tasks.

### Review Mode (default)
**Convergent thinking.** Find what's wrong: errors, inconsistencies, missed edge cases, violations of stated principles.

- Lower temperature for Gemini (`-t 0.3`) — more deterministic, stern
- GPT reasoning-effort high — deep fault-finding
- Prompts ask "what's wrong" and "where does this break"
- Output: ranked list of problems with verification criteria

### Brainstorming Mode
**Divergent thinking.** Generate new ideas, alternative approaches, novel connections.

- Default/higher temperature for Gemini (`-t 0.8`) — more creative
- GPT reasoning-effort medium — broader exploration, less tunnel vision
- Prompts ask "what else could work" and "what's the unconventional approach"
- Output: ranked list of ideas with feasibility assessment

Select mode based on the review target:
- Code/architecture/decisions → **Review mode**
- Strategy/design space/exploration → **Brainstorming mode**
- User can override with `--brainstorm` or `--review`

## The Process

### Step 1: Define the Review Target

State clearly what's being reviewed: `$ARGUMENTS`

Identify:
- **The decision/recommendation/code** under review
- **Who made it** (you, a previous Claude session, a human)
- **What evidence exists** (code, configs, research, benchmarks)
- **Mode:** Review (default) or Brainstorming

### Step 2: Bundle Context

Build context files. Constitutional documents go first (if found).

**Output directory setup:**
```bash
# Persist outputs — NOT /tmp
REVIEW_DIR=".model-review/$(date +%Y-%m-%d)"
mkdir -p "$REVIEW_DIR"
```

**Gemini 3.1 Pro context** (~50K-200K tokens target):
```bash
cat > "$REVIEW_DIR/gemini-context.md" << 'HEADER'
# CONTEXT: Cross-Model Review of [topic]
HEADER

# Constitutional preamble (if found)
if [ -n "$CONSTITUTION" ]; then
  echo -e "\n# PROJECT CONSTITUTION\nReview against these principles, not your own priors.\n" >> "$REVIEW_DIR/gemini-context.md"
  cat "$CONSTITUTION" >> "$REVIEW_DIR/gemini-context.md"
fi
if [ -n "$GOALS" ]; then
  echo -e "\n# PROJECT GOALS\n" >> "$REVIEW_DIR/gemini-context.md"
  cat "$GOALS" >> "$REVIEW_DIR/gemini-context.md"
fi

# Append source code, configs, research, docs
# ... include everything. Gemini's strength is pattern-matching over large context.
```

**GPT-5.2 context** (~10K-30K tokens target):
```bash
cat > "$REVIEW_DIR/gpt-context.md" << 'HEADER'
# CONTEXT: Cross-Model Review of [topic]
HEADER

# Constitutional preamble (if found)
if [ -n "$CONSTITUTION" ]; then
  echo -e "\n# PROJECT CONSTITUTION\nQuantify alignment gaps. For each principle, assess: coverage (0-100%), consistency, testable violations.\n" >> "$REVIEW_DIR/gpt-context.md"
  cat "$CONSTITUTION" >> "$REVIEW_DIR/gpt-context.md"
fi
if [ -n "$GOALS" ]; then
  echo -e "\n# PROJECT GOALS\nAssess quantitative alignment. Which goals are measurably served? Which are neglected?\n" >> "$REVIEW_DIR/gpt-context.md"
  cat "$GOALS" >> "$REVIEW_DIR/gpt-context.md"
fi

# Focused summary — GPT's strength is reasoning depth, not context volume
```

**Token budget guidance:**
| Model | Sweet spot | Max useful | Strength |
|-------|-----------|------------|----------|
| Gemini 3.1 Pro | 80K-150K | ~500K | Pattern matching, cross-referencing across large context |
| GPT-5.2 | 15K-40K | ~100K | Deep reasoning with `--reasoning-effort high`, formal analysis |

### Step 3: Dispatch Reviews (Parallel)

Fire both reviews simultaneously. Each model gets a DIFFERENT cognitive task.

---

#### Review Mode Prompts

**Gemini 3.1 Pro — Architectural/Pattern Review:**
```bash
cat "$REVIEW_DIR/gemini-context.md" | llmx chat -m gemini-3.1-pro-preview \
  -t 0.3 --no-stream --timeout 300 "
[Describe what's being reviewed]

RESPOND WITH EXACTLY THESE SECTIONS:

## 1. Where the Analysis Is Wrong
Specific errors or oversimplifications. Reference actual code/config.

## 2. What Was Missed
Patterns, problems, or opportunities not identified. Cite files, line ranges, architectural gaps.

## 3. Better Approaches
For each recommendation, either: Agree (with refinements), Disagree (with alternative), or Upgrade (better version).

## 4. What I'd Prioritize Differently
Your ranked list of the 5 most impactful changes, with testable verification criteria.

## 5. Constitutional Alignment
$([ -n "$CONSTITUTION" ] && echo "Where does the reviewed work violate or neglect stated principles? Which principles are well-served?" || echo "No constitution provided — assess internal consistency only.")

## 6. Blind Spots In My Own Analysis
What am I (Gemini) likely getting wrong? Where should you distrust my assessment?

Be concrete. No platitudes. Reference specific code, configs, and findings.
" > "$REVIEW_DIR/gemini-output.md" 2>&1
```

**GPT-5.2 — Quantitative/Formal Analysis:**
```bash
cat "$REVIEW_DIR/gpt-context.md" | llmx chat -m gpt-5.2 \
  --reasoning-effort high --stream --timeout 600 "
[Describe what's being reviewed]

You are performing QUANTITATIVE and FORMAL analysis. Gemini is handling qualitative pattern review separately. Focus on what Gemini can't do well.

RESPOND WITH EXACTLY:

## 1. Logical Inconsistencies
Formal contradictions, unstated assumptions, invalid inferences. If math is involved, verify it.

## 2. Cost-Benefit Analysis
For each proposed change: estimated effort, expected impact, risk. Rank by ROI.

## 3. Testable Predictions
Convert vague claims into falsifiable predictions with success criteria. If a claim can't be made testable, flag it.

## 4. Constitutional Alignment (Quantified)
$([ -n "$CONSTITUTION" ] && echo "For each principle in CONSTITUTION.md: coverage score (0-100%), specific gaps, suggested fixes." || echo "No constitution provided — assess internal logical consistency.")

## 5. My Top 5 Recommendations (different from the originals)
Ranked by measurable impact. Each must have: (a) what, (b) why with quantitative justification, (c) how to verify with specific metrics.

## 6. Where I'm Likely Wrong
What am I (GPT-5.2) probably getting wrong? Known biases to flag: overconfidence in fabricated specifics, overcautious scope-limiting, production-grade recommendations for personal projects.

Be precise. Show your reasoning. No hand-waving.
" > "$REVIEW_DIR/gpt-output.md" 2>&1
```

---

#### Brainstorming Mode Prompts

**Gemini 3.1 Pro — Creative Exploration:**
```bash
cat "$REVIEW_DIR/gemini-context.md" | llmx chat -m gemini-3.1-pro-preview \
  -t 0.8 --no-stream --timeout 300 "
[Describe the design space to explore]

Think divergently. Challenge assumptions. What would a completely different approach look like?

## 1. Alternative Architectures
3 fundamentally different approaches. Not variations — genuinely different paradigms.

## 2. What Adjacent Fields Do Differently
Patterns from other domains that could apply here. Cite specific systems or papers.

## 3. The Unconventional Idea
The approach that seems wrong but might work. Explain why it could succeed despite looking odd.

## 4. What's Being Over-Engineered
Where is complexity not earning its keep? What could be radically simplified?

## 5. Blind Spots
What am I (Gemini) missing because of my training distribution? Where should my creativity be distrusted?
" > "$REVIEW_DIR/gemini-brainstorm.md" 2>&1
```

**GPT-5.2 — Structured Ideation:**
```bash
cat "$REVIEW_DIR/gpt-context.md" | llmx chat -m gpt-5.2 \
  --reasoning-effort medium --stream --timeout 300 "
[Describe the design space to explore]

Generate novel approaches with feasibility assessment.

## 1. Idea Generation (10 ideas)
Quick-fire: 10 approaches ranked by novelty. For each: one sentence + feasibility (High/Medium/Low).

## 2. Deep Dive on Top 3
For each: architecture sketch, estimated effort, risk, what makes it non-obvious.

## 3. Combination Plays
Ideas that work poorly alone but well together. Cross-pollinate from the list above.

## 4. What Would Break Each Approach
Pre-mortem: for the top 3, what's the most likely failure mode?

## 5. Where I'm Likely Wrong
What am I (GPT-5.2) probably biased toward? Where should my suggestions be distrusted?
" > "$REVIEW_DIR/gpt-brainstorm.md" 2>&1
```

---

**Optional — Flash pattern extraction pass:**
For large codebases, a cheap Flash pass before the main reviews can surface mechanical issues:
```bash
cat /path/to/large-context.md | llmx chat -m gemini-3-flash-preview \
  -t 0.2 --no-stream --timeout 120 "
Mechanical audit only. Find:
- Duplicated content across files
- Inconsistent naming (model names, paths, conventions)
- Stale references (wrong versions, deprecated APIs)
- Missing cross-references between related documents
Output as a flat list. No analysis, no recommendations.
" > "$REVIEW_DIR/flash-audit.md" 2>&1
```

### Step 4: Fact-Check Outputs (MANDATORY)

**Both models hallucinate. Never adopt a recommendation without verification.**

For each claim in each review:

1. **Code claims** — Read the actual file and verify. Models frequently cite wrong line numbers, invent function names, or misread logic.
2. **Research claims** — Check if the cited paper/finding actually says what the model claims. Models often distort findings to support their argument.
3. **"Missing feature" claims** — Grep the codebase. The feature may already exist. Models frequently recommend adding things that are already implemented.

Use Flash for rapid fact-checking of specific claims:
```bash
echo "Claim: [model's claim]. Actual code: [paste relevant code]" | \
  llmx -m gemini-3-flash-preview "Is this claim about the code accurate? Be precise."
```

### Step 5: Synthesize

Build a trust-ranked synthesis:

| Trust Level | Criterion | Action |
|------------|-----------|--------|
| **Very high** | Both models agree + verified against code | Adopt |
| **High** | One model found + verified against code | Adopt |
| **Medium** | Both models agree but unverified | Verify before adopting |
| **Low** | Single model, unverified | Flag for investigation |
| **Reject** | Model recommends itself, or claim contradicts verified code | Discard |

**Output format:**

```markdown
## Cross-Model Review: [topic]
**Mode:** Review / Brainstorming
**Date:** YYYY-MM-DD
**Models:** Gemini 3.1 Pro, GPT-5.2
**Constitutional anchoring:** Yes/No (CONSTITUTION.md, GOALS.md)

### Verified Findings (adopt)
| Finding | Source | Verified How |
|---------|--------|-------------|
| ... | Gemini + GPT | Checked search.py:312 |

### Where I Was Wrong
| My Original Claim | Reality | Who Caught It |
|-------------------|---------|--------------|

### Gemini Errors (distrust)
| Claim | Why Wrong |

### GPT Errors (distrust)
| Claim | Why Wrong |

### Revised Priority List
1. ...
```

**Save synthesis:**
```bash
# Persist alongside model outputs
cp synthesis.md "$REVIEW_DIR/synthesis.md"
```

## Known Model Biases

Flag these when they appear in outputs. Don't adopt recommendations that match a model's known bias without independent verification.

| Model | Bias | How It Manifests | Countermeasure |
|-------|------|-----------------|----------------|
| **Gemini 3.1 Pro** | Production-pattern bias | Recommends enterprise patterns (DuckDB migrations, service meshes) for personal projects | Check if recommendation matches project scale |
| **Gemini 3.1 Pro** | Self-recommendation | Suggests using Gemini for tasks, recommends Google services | Flag any self-serving suggestions |
| **Gemini 3.1 Pro** | Instruction dropping | Ignores structured output format in long contexts | Re-prompt if output sections are missing |
| **GPT-5.2** | Confident fabrication | Invents specific numbers, file paths, function names with high confidence | Verify every specific claim against actual code |
| **GPT-5.2** | Overcautious scope | Adds caveats that dilute actionable findings, hedges everything | Push for concrete recommendations |
| **GPT-5.2** | Production-grade creep | Recommends auth, monitoring, CI/CD for hobby projects | Match recommendations to actual project scale |
| **Flash** | Shallow analysis | Good for pattern matching, bad for architectural judgment | Use ONLY for mechanical audits and fact-checking |
| **Flash** | Recency bias | Defaults to latest patterns even when older ones are better | Don't use for "which approach" decisions |

## Model-Specific Prompting Notes

**Gemini 3.1 Pro:**
- Excels at cross-referencing across large context (finds contradictions between file A and file B)
- Review mode: `-t 0.3` for analytical work. Brainstorming mode: `-t 0.8` for creative exploration
- Note: Gemini thinking models may lock temperature server-side — the flag is a hint, not a guarantee
- Will recommend itself for tasks — always flag self-serving suggestions
- Tends to over-recommend architectural changes (DuckDB migrations, etc.)

**GPT-5.2:**
- `--reasoning-effort high` is essential for review mode (burns thinking time for deep fault-finding)
- `--reasoning-effort medium` for brainstorming mode (avoids tunnel vision)
- MUST use `--stream` with reasoning-effort high — non-streaming timeouts are common
- Temperature is locked at 1.0 for reasoning models (llmx overrides lower values)
- `--timeout 600` minimum for high reasoning effort
- Tends toward overcautious "production-grade" recommendations for personal projects
- **Differentiated role:** Quantitative/formal analysis — logical inconsistencies, math errors, cost-benefit, testable predictions. Gemini handles the qualitative pattern review.

**Gemini Flash (`gemini-3-flash-preview`):**
- Use for rapid verification of specific claims against code snippets
- Fast and cheap — good for 10-20 quick checks and mechanical audits
- Don't use for architectural judgment, only factual verification and pattern matching
- Note: `gemini-flash-3` and `gemini-3-flash` are both 404s — always use `gemini-3-flash-preview`

## Anti-Patterns

- **Adopting recommendations without code verification.** Both models hallucinated "missing" features that already existed in the codebase.
- **Treating model agreement as proof.** Two models can be wrong the same way (shared training data). Always verify against source code.
- **Letting models review their own previous output.** Send fresh prompts, not "here's what you said last time, improve it."
- **Using same-model instances as "different reviewers."** Claude reviewing Claude = same distribution. This skill exists because cross-model is the only form that provides real adversarial pressure.
- **Skipping the self-doubt section.** The "Where I'm Likely Wrong" section is the most valuable part of each review. Models that can't identify their own weaknesses are less trustworthy.
- **Same prompt to both models.** Gemini and GPT have different strengths. Sending the same qualitative prompt to both wastes GPT's formal reasoning capability. Gemini = patterns, GPT = quantitative/formal.
- **Writing to /tmp.** Review outputs are valuable artifacts. Always persist to `.model-review/YYYY-MM-DD/`.
- **Skipping constitutional check.** Reviews without project-specific anchoring drift into generic advice. Always check for CONSTITUTION.md/GOALS.md first.
- **Mixing review and brainstorming.** Convergent (find errors) and divergent (generate ideas) thinking are cognitively different. Don't ask for both in one prompt — the outputs will be mediocre at both.

$ARGUMENTS

---
# SKILL: researcher

---
name: researcher
description: Autonomous research agent that orchestrates all available MCP tools with epistemic rigor. Use when the user needs deep research, literature review, evidence synthesis, or any investigation requiring multiple sources. Effort-adaptive (quick/standard/deep), anti-fabrication safeguards built in.
argument-hint: [research question or topic]
---

# Researcher

Research with the rigor of an investigative journalist, not a search engine. Every claim needs provenance. Inference is fine — but say it's inference, not fact.

**Invoke companion skills if relevant:**
- **`epistemics`** — if the question touches bio/medical/scientific claims
- **`source-grading`** — if this is an investigation/OSINT context (use Admiralty grades)

**Project-specific tool routing and gotchas are in `.claude/rules/research-depth.md`** (if it exists). Check it before starting.

## Available Research Tools

Use whichever of these are available in the current project's `.mcp.json`:

| Tool | What it does | When to use |
|------|-------------|-------------|
| `mcp__selve__search` | Personal knowledge search | Prior work, conversations, notes — **always check first** if available |
| `mcp__duckdb__execute_query` | Query project DuckDB views | Local data — check before going external |
| `mcp__intelligence__*` | Entity resolution, dossiers, screening | Investigation targets (if configured) |
| `mcp__research__search_papers` | Semantic Scholar search | Finding papers. **No date filtering** — use Exa for recency |
| `mcp__research__save_paper` | Save paper to local corpus | After finding useful paper |
| `mcp__research__fetch_paper` | Download PDF + extract text | **Before citing any paper** |
| `mcp__research__read_paper` | Get full extracted text | Reading a fetched paper |
| `mcp__research__ask_papers` | Query across papers (Gemini 1M) | Synthesizing multiple papers |
| `mcp__research__list_corpus` | List saved papers | Check before searching externally |
| `mcp__research__export_for_selve` | Export for knowledge embedding | End of session, persist findings (if configured) |
| `mcp__paper-search__search_arxiv` | arXiv search | Preprints — flag as `[PREPRINT]` |
| `mcp__paper-search__search_pubmed` | PubMed search | Clinical/medical literature |
| `mcp__paper-search__search_biorxiv` | bioRxiv/medRxiv search | Biology/medical preprints |
| `mcp__exa__web_search_exa` | Semantic web search | Non-obvious connections, expert blogs, recent work |
| `mcp__exa__company_research_exa` | Company intelligence | Business/financial research |
| `mcp__exa__get_code_context_exa` | Code/docs search | Technical implementation |
| `mcp__context7__*` | Library documentation | API/framework questions |
| WebFetch | Fetch specific URLs | Known databases, filings, regulatory |
| WebSearch | General web search | News, grey literature |

Not all tools exist in every project. Use what's available. The agent will error on tools not in `.mcp.json` — just skip them.

**Critical rule:** `fetch_paper` then `read_paper` BEFORE citing. Abstracts are not primary sources.

**S2 gotcha:** No date filtering on free tier. ~100 req/5min rate limit. Use Exa for "recent papers on X."

## Effort Classification

Before doing anything, classify the question:

| Tier | Signals | Axes | Output |
|------|---------|------|--------|
| **Quick** | Factual lookup, single claim | 1 | Inline answer with source |
| **Standard** | Topic review, comparison, "what do we know?" | 2 | Research memo with claims table |
| **Deep** | Literature review, novel question, "investigate X" | 3+ | Full report with disconfirmation + search log |

User can override with `--quick` or `--deep`. Announce the tier before starting.

## Domain Profiles

Classify the question's domain before starting. Domain-specific gotchas (non-obvious mistakes per field) are in **`DOMAINS.md`** alongside this skill. Read it when the domain applies.

If a question spans domains, name the primary and secondary. Use the stricter evidence standard. Project-specific routing (which DuckDB views, which databases) lives in `.claude/rules/research-depth.md`.

## Phase 1 — Ground Truth (always first)

Before any external search, check what exists locally:

1. **Personal knowledge** — `selve` MCP search if available, or local docs
2. **Project data** — DuckDB queries, local analysis files, entity docs
3. **Research corpus** — `list_corpus` for previously saved papers
4. **Training data** — what you know (label `[TRAINING-DATA]`)

Output: "What I already know" inventory. Flag contradictions with later findings.
**Quick tier:** If ground truth answers the question, stop here.

## Phase 2 — Exploratory Divergence

**Mandatory:** Name 2+ independent search axes before searching. Different axes reach different literatures.

Example axes:
- **Academic-anchored:** concept → literature → state of the art
- **Mechanism-anchored:** pathway → modulators → evidence
- **Investigation-anchored:** entity → enforcement → patterns
- **Population-anchored:** comparable cases → what happened
- **Application-anchored:** use case → implementations → lessons
- **Genotype-anchored:** variant → mechanism → intervention (genomics)
- **Guideline-anchored:** clinical guidelines → standard of care (medical)

If your axes all start from the same place, you have one axis with multiple queries.

**Search strategy per axis:**
- Minimum 3 query formulations (vary semantic vs keyword)
- Use different tools per axis when possible
- Scan titles/abstracts from 15+ sources before forming hypotheses
- **Save papers** with `save_paper`, **fetch full text** before citing

**Exa search philosophy (semantic search, not keyword):**
- Exa matches by meaning, not keywords. Query by phrase — describe the *concept* you want results from, not the terms you'd grep for. "Gene-diet interaction abolishing cardiovascular genetic risk" finds different (better) results than "9p21 diet interaction."
- **Seek insight from adjacent domains.** The most useful context often isn't phrased the same way or even from the same field. Ask: "What knowledge space would contain a brilliant critique of this idea?" Then phrase the query *from that domain's perspective*.
- **Avoid searching for things you're already certain about** from pre-training that won't have changed. Use your intuition for stable knowledge. Search for things that are *fast-moving* or where new insights likely exist since your cutoff.
- **Sequential exploration, not shotgun.** Don't fire 10 Exa queries in parallel and flood the context window with noise. Instead: 3 targeted queries → scan summaries → identify which direction has signal → 3 more queries doubling down on the most promising vein. This is an affinity tree, not a broadcast.
- **Use Exa's `summary` and `highlights` fields** to scan results before pulling full text. Set `maxCharacters` on `text` to limit per-result context. The best sources are usually papers, blog posts, essays, and threads — not marketing pages.
- **First results may be SEO noise.** Don't stop at the top 3 — scan 8-10 results at summary level, then read the 2-3 that actually have signal.

**Quick:** 1 axis, 1-2 queries. **Standard:** 2 axes, 5+ queries. **Deep:** 3+ axes, 10+ queries.

## Phase 3 — Hypothesis Formation (Standard + Deep)

From Phase 2 findings, form 2-3 testable hypotheses as falsifiable claims:
- "If X is true, we should see Y in the data/literature."
- "If X is false, we should see Z."

## Phase 4 — Disconfirmation (Standard + Deep)

For EACH hypothesis, actively search for contradictory evidence:
- "X does not work", "X failed", "X criticism", "X negative results"
- "no association between X and Y", "X limitations"
- Check single lab/group vs independent replication

If no contradictory evidence after genuine effort: "no contradictory evidence found" (≠ "none exists").
**This phase is structurally required.** Output without disconfirmation is incomplete.

## Phase 5 — Claim-Level Verification

For every specific claim in your output:

- **Numbers:** From a source, or generated? If generated → `[ESTIMATED]`
- **Names:** From a source you accessed, or memory? If memory → verify or label `[UNVERIFIED]`
- **Existence:** Does this paper actually exist? If you cannot confirm, DO NOT cite it
- **Attribution:** Does the paper actually say what you think? Use `read_paper` to verify

**YOU WILL FABRICATE under pressure to be precise.** The pattern: real concept + invented specifics (author name, fold-change, sample size). Catch yourself. Vague truth > precise fiction.

## Phase 6 — Diminishing Returns Gate

After each research action, assess marginal yield:

```
IF last action added new info that changes conclusions → CONTINUE
IF two independent sources agree, no contradictions   → CONVERGED: synthesize
IF last 2+ actions added nothing new                  → DIMINISHING: start writing
IF expanding laterally instead of resolving question   → SCOPE CREEP: refocus
IF question is more complex than initially classified  → UPGRADE TIER
```

The goal is sufficient evidence for the stakes level, not exhaustive coverage.
3 well-read papers beat 20 saved-but-unread papers.

## Phase 6b — Recitation Before Conclusion

Before writing any conclusion or synthesis that draws on multiple sources:

**Restate the specific evidence you're drawing from.** List the concrete data points, not summaries. Then derive the conclusion.

This is the "recitation strategy" (Du et al., EMNLP 2025, arXiv:2510.05381): prompting models to repeat relevant evidence before answering improves accuracy by +4% on long-context tasks. Training-free, model-agnostic. Works because it forces the model to retrieve and hold evidence in recent context before reasoning over it.

```
WRONG: "The evidence suggests X is effective."
RIGHT: "Study A found 26% improvement (n=500). Study B found no effect (n=200).
        Study C found 15% improvement but only in subgroup Y (n=1200).
        Weighing by sample size and methodology: modest evidence for X, limited to subgroup Y."
```

This is structural, not stylistic. Recitation surfaces contradictions that narrative synthesis buries.

## Phase 7 — Source Assessment

For each source that grounds a claim:

1. **Quality:** Peer-reviewed vs preprint vs blog? Sample size, methodology, COI?
2. **Situating:** Confirms prior work? Contradicts it? Novel/`[FRONTIER]`? Isolated/`[SINGLE-SOURCE]`?
3. **Confidence:** Strong methodology > volume of weaker studies. "We don't know yet" is valid.

## Phase 8 — Corpus Building

During and after research:
- **Papers:** `save_paper` for key finds, `fetch_paper` for papers you cited
- **Cross-paper synthesis:** `ask_papers` to query across fetched papers
- **Session end:** `export_for_selve` → run `./selve update` to embed into unified index
- **Research memos:** Write to project-appropriate location (`docs/research/`, `analysis/`)

## Output Contract

### Quick Tier
Answer inline with source citation. No formal report.

### Standard Tier
```markdown
## [Topic] — Research Memo

**Question:** [what was asked]
**Tier:** Standard | **Date:** YYYY-MM-DD
**Ground truth:** [what was already known]

### Claims Table
| # | Claim | Evidence | Confidence | Source | Status |
|---|-------|----------|------------|--------|--------|
| 1 | ... | RCT / dataset | HIGH | [DOI/URL] | VERIFIED |
| 2 | ... | Inference | LOW | [URL] | INFERENCE |

### Key Findings
[With source quality assessment]

### What's Uncertain
[Unresolved questions]

### Sources Saved
[Papers/sources added to corpus]
```

### Deep Tier
Standard tier plus:
- **Disconfirmation results** — contradictory evidence found
- **Verification log** — claims verified via tool vs training data, caught fabricating
- **Search log** — queries run, tools used, hits/misses
- **Provenance tags** — every claim tagged

## Provenance Tags

Tag every claim:
- **`[SOURCE: url]`** — Directly sourced from a retrieved document
- **`[DATABASE: name]`** — Queried a reference database (ClinVar, gnomAD, DuckDB)
- **`[DATA]`** — Our own analysis, query reproducible
- **`[INFERENCE]`** — Logically derived from sourced facts (state the chain)
- **`[TRAINING-DATA]`** — From model training, not retrieved this session
- **`[PREPRINT]`** — From unreplicated preprint
- **`[FRONTIER]`** — From unreplicated recent work
- **`[UNVERIFIED]`** — Plausible but not verified

Never present inference as sourced fact. Never present training data as retrieved evidence.

**Precedence:** When `source-grading` (Admiralty `[A1]`-`[F6]`) is active during `/investigate` or OSINT workflows, use Admiralty grades instead. Don't mix both.

## Parallel Agent Dispatch (Deep tier)

- Split by **axis and subtopic**, not by tool
- Include ground truth context in each agent
- Dispatch verification agent after research agents return
- Synthesis is a separate step (agents can't see each other's output)
- 2 agents on 2 axes > 10 agents on 1 axis

## Anti-Patterns

- **Synthesis mode default:** Summarized training data instead of fetching primary sources. THE failure mode this skill exists to prevent.
- **Confirmation bias:** Queries like "X validation" instead of "X criticism" or "X failed".
- **Authority anchoring:** Found one source and stopped
- **Precision fabrication:** Invented specific numbers under pressure to be precise
- **Author confabulation:** Remembered finding but not author, generated plausible name
- **Telephone game:** Cited primary study via review without reading the primary
- **Directionality error:** Cited real paper but inverted the sign of the finding
- **Single-axis search:** All queries from same starting point
- **Ground truth neglect:** Went external without checking local data first
- **Infinite research:** Kept searching past convergence instead of writing conclusions
- **Source hoarding:** Saved papers but never fetched/read them
- **Tier inflation/deflation:** Mismatched effort to stakes
- **MCP bypass:** Used WebSearch when a specialized MCP tool exists
- **Scope creep without pushback:** User asks 15 things, attempt all, run out of context. Say "this session can handle N of these well; which are priority?"
- **Training data as research:** Reciting textbook citations from training without `[TRAINING-DATA]` tags
- **S2 for recency:** Using Semantic Scholar when Exa is better for recent work
- **Redundant documentation:** For tools the model already knows, adding instructions is noise

## What Research Shows About Agent Reliability

Evidence from 4 papers (Feb 2026), all read in full. Not aspirational — measured.

- **Instructions alone don't produce reliability.** EoG (IBM, arXiv:2601.17915): giving LLM perfect investigation algorithm as prompt = 0% Majority@3 for 2/3 models. Architecture (external state, deterministic control) produces reliability, not instructions. This skill is necessary but NOT sufficient — hooks, healthchecks, and deterministic scaffolding are what make agents reliable.
- **Consistency is flat.** Princeton (arXiv:2602.16666): 14 models, 18 months, r=0.02 with time. Same task + same model + different run = different outcome. Retry logic and majority-vote are architectural necessities.
- **Documentation helps for novel knowledge, not for known APIs.** Agent-Diff (arXiv:2602.11224): +19 pts for genuinely novel APIs, +3.4 for APIs in pre-training. Domain-specific constraints (DuckDB types, ClinVar star ratings) are "novel" = worth encoding. Generic tool routing is "known" = low value.
- **Simpler beats complex under stress.** ReliabilityBench (arXiv:2601.06112): ReAct > Reflexion under perturbations. More complex reasoning architectures compound failure.

$ARGUMENTS


## Companion: DOMAINS.md
# Domain Profiles

Domain-specific gotchas for the researcher skill. These focus on non-obvious mistakes — evidence hierarchies are standard and don't need repeating. Classify the question's domain and apply the relevant profile.

If a question spans domains, name the primary and secondary. Use the stricter evidence standard. Project-specific tool routing (which databases, which views) lives in `.claude/rules/research-depth.md` if it exists.

## Scientific / Biomedical
- **Invoke `epistemics` skill** if available — it has the evidence hierarchy and grading rules.
- ClinVar single-submitter entries get reclassified often — don't treat as settled. ≥2 stars only.
- gnomAD frequency alone is not clinical evidence. PRS percentiles are population-relative, not absolute risk.
- You WILL fabricate supplement dosages and effect sizes under pressure to be precise. Don't.
- Rodent studies and mechanistic reasoning are hypothesis-generating, not evidence for human protocols.
- PubMed for clinical literature. Exa for recent work (Semantic Scholar can't filter by date on free tier).

## Trading / Investment
- **Invoke `source-grading` skill** if available — Admiralty grades, not provenance tags.
- **Detrend before claiming correlation.** Spurious correlations are the norm — control for market, seasonality, and shared trends before reporting any r value.
- Consensus = zero information. If every analyst says it, the price already reflects it.
- For high-conviction leads, use `/competing-hypotheses` to prevent single-hypothesis confirmation bias.
- **Predict the data footprint BEFORE querying.** Write what you expect to find, then query. Prevents confirmation bias.
- Check PIT (point-in-time) safety — disclosure lags vary by dataset (e.g., insider trades: 2-45 days, government spending: up to 365 days).
- Survivorship bias in backtests. Look-ahead bias in feature construction. Both invisible until you check.
- Absence of expected evidence IS evidence. If your hypothesis predicts X and X isn't there, that's diagnostic.

## Mathematics / Formal
- Reproduce derivations from source. Don't cite formulas from training data.
- You WILL invent coefficients, sample sizes, and p-values. The pattern: real concept + fabricated specifics.
- Verify probability vs odds vs log-odds at function boundaries — unit confusion is a real and common bug.
- Small-denominator metrics need Empirical Bayes shrinkage, not raw proportions.

## Investigative / OSINT
- **Invoke `source-grading` skill** if available — Admiralty grades mandatory.
- Grade claims, not datasets. The same dataset can have different reliability for different fields.
- **Predict the data footprint BEFORE querying.** If your hypothesis is true, what should you see in the data?
- Correlated signals (e.g., shared phone + shared address + shared official) can't be summed as independent log-likelihood ratios. Use composite scoring.
- Missing data ≠ no evidence. If actors hide information, missingness is evidence.
- The null hypothesis is always "error, not fraud." Don't skip it.

## Social Science
- Replication crisis is real. Check if the finding has been independently replicated before citing.
- WEIRD samples (Western, Educated, Industrialized, Rich, Democratic) — most psych findings are from US undergrads.
- Pre-registered studies > post-hoc analysis. Check if the study was pre-registered.

## Economics / Policy
- Ecological fallacy: aggregate patterns don't imply individual behavior.
- Policy effects are context-dependent. What worked in one country may not transfer.
- Goodhart's Law: when a metric becomes a target, it ceases to be a good metric.

---
# SKILL: source-grading

---
name: source-grading
description: NATO Admiralty System for grading source reliability and information credibility. Apply automatically during OSINT, forensic investigations, legal research, entity audits, or fraud analysis — NOT for general software or casual research. Every claim gets a 2-axis grade (A-F for source reliability, 1-6 for information credibility).
user-invocable: false
---

# Source Grading: The Admiralty System

Every claim in research or investigation output must be graded on two independent axes.

## Axis 1: Source Reliability (Who provided this?)

| Grade | Label | Criteria | Examples |
|-------|-------|----------|----------|
| **A** | Completely Reliable | Proven track record; legally accountable for falsehood | Court records, SEC filings, government audit reports, enforcement actions |
| **B** | Usually Reliable | Institutional reputation at stake; editorial/peer review | Academic peer-reviewed studies, major investigative journalism, GAO/OIG reports |
| **C** | Fairly Reliable | Domain expertise but potential bias; less rigorous review | Trade press, industry reports, state agency press releases |
| **D** | Not Usually Reliable | Self-interested; no independent verification | Company press releases, PR, marketing, self-reported data |
| **E** | Unreliable | Known bias, history of inaccuracy, no accountability | Social media, anonymous forums, unverified tips |
| **F** | Cannot Be Judged | Source reliability cannot be assessed | New/unknown source, automated data with unknown provenance |

## Axis 2: Information Credibility (Is this claim true?)

| Grade | Label | Criteria |
|-------|-------|----------|
| **1** | Confirmed | Independently verified by 2+ sources from different domains |
| **2** | Probably True | Consistent with known data; one independent confirmation |
| **3** | Possibly True | No confirmation, no contradiction; plausible but unverified |
| **4** | Doubtful | Inconsistent with some known data; requires assumptions |
| **5** | Improbable | Contradicted by known data or independent sources |
| **6** | Cannot Be Judged | Not enough information to assess truth value |

## Combined Grade Format

Write grades as `[Grade: X#]` inline with claims:

- "ABI owes $14.3M in wage theft" **[A1]** — Crain's (A), confirmed by DOL records (1)
- "The entity has no web presence" **[F3]** — absence of evidence (F), possibly true (3)
- "$1.68B in Medicaid billing" **[A1]** — CMS official data (A), cross-verified (1)

## Rules

1. **Grade source and information independently.** A completely reliable source (A) can report wrong information (4-5). An unreliable source (E) can provide independently confirmed information (1).

2. **Upgrade credibility when sources converge.** Three C-grade sources independently reporting the same fact → credibility upgrades toward 1-2.

3. **Downgrade credibility when sources share upstream.** Three sources citing the same original report = ONE source, not three.

4. **Absence of evidence is not evidence of absence.** "No enforcement action found" is [B3] at best.

5. **Self-interested sources get automatic D.** Company statements about their own compliance, self-attestation, marketing — never above D unless independently confirmed.

6. **Data from our own analysis is [DATA].** A-reliability (official source), credibility depends on query correctness.

## Integration with Provenance Tags

| Old Tag | Admiralty Equivalent |
|---------|---------------------|
| [DATA] | [DATA] (keep — indicates own analysis) |
| [SOURCE: url] | [Grade: X#] with the URL |
| [INFERENCE] | [INFERENCE: X# + X#] — cite grades of premises |
| [UNCONFIRMED] | Any claim graded 3-6 on credibility |

## When to Grade

- **Always** during `investigate` or `deep-research` workflows
- **Always** in analysis documents for handoff (attorneys, journalists, government)
- **Optional** in informal conversation or brainstorming
- **Required** before any lead enters the diagnosticity matrix in `competing-hypotheses`

