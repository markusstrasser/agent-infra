# CONTEXT: Cross-Model Review of Context Bundling Infrastructure Design

# PROJECT CONSTITUTION
Review against these principles, not your own priors.

## Constitution (from CLAUDE.md)

### Generative Principle
> Maximize the rate at which agents become more autonomous, measured by declining supervision.

Autonomy is the primary objective. Grow > de-grow. Build the guardrails because they're cheap, not because they're the goal.

### Key Principles
1. **Architecture over instructions.** If it matters, enforce with hooks/tests/scaffolding. Text is a prototype; architecture is the product.
2. **Measure before enforcing.** Log every hook trigger to measure false positives.
3. **Self-modification by reversibility + blast radius.**
4. **Research is first-class.** Divergent → convergent → eat your own dogfood → analyze.
5. **Skills governance.** Meta owns skill quality.
6. **Fail open, carve out exceptions.**
7. **Recurring patterns become architecture.** If used/encountered 10+ times → hook, skill, or scaffolding.
8. **Cross-model review for non-trivial decisions.** Same-model review is a martingale.
9. **The git log is the learning.**

### Session Architecture
- Fresh context per orchestrated task (no --resume)
- 15 turns max per orchestrated task
- Subagent delegation for fan-out

# PROJECT GOALS

Mission: Maximize autonomous agent capability across all projects while maintaining epistemic integrity.

Primary Success Metric: Ratio of autonomous-to-supervised work. No reverted work, no 5-hour runs that should be 1-hour, no error branch spirals, no agent theater, no repeated corrections.

Resource Constraints: Single human operator, cost-conscious, local Mac + cloud APIs.

# THE DESIGN BEING REVIEWED

## Problem Statement

When an agent orchestrates cross-model review (sending context to Gemini and GPT for adversarial critique), the current process is:

1. **Serial context assembly** — Claude reads files one-by-one via tool calls, writes context bundles manually
2. **Serial model dispatch** — two `llmx` calls run sequentially (the SKILL.md doesn't instruct parallel)
3. **No caching** — identical codebase context is rebuilt from scratch each review
4. **No pre-computation** — every review starts from zero, re-reading the same files
5. **No structured output** — models return free text, synthesis is lossy prose summarization

This takes 3-10 minutes per review, wastes Claude's own tokens on copy-paste, and misses provider-side prompt cache hits.

## Proposed Design: Pre-computed Context Views + Parallel Dispatch + Caching

### Pre-computed Context Views

Each project gets a `.context/` directory (gitignored) with pre-computed repomix outputs:

```
.context/
  manifest.json         # views, timestamps, token counts
  full.xml              # repomix: everything
  src.xml               # repomix --include "src/**"
  docs.xml              # repomix --include "docs/**,*.md"
  infra.xml             # repomix --include config/CI/hooks
  signatures.xml        # repomix --compress (tree-sitter signature extraction, ~70% smaller)
  filetree.txt          # directory structure only
  diffs.xml             # repomix --include-diffs
  constitution.md       # stable prefix: constitution + GOALS + arch ref
  profiles/
    *.config.json       # one repomix config per view
```

**Repomix features used:**
- XML output with `<file path="...">` tags (best for LLM parsing)
- `--compress` for tree-sitter signature extraction (~70% token reduction)
- `sortByChanges` to prioritize hot files
- `--include-diffs` for working tree changes
- `--include-logs` for recent commit history
- Token counting built in (tiktoken)
- `--copy` for clipboard, `--stdout` for piping

**Multiple views require multiple config files** — repomix doesn't support profiles natively. Each view = one `--config path/to/profile.json` invocation.

### Generation Triggers

A `context-gen` script that:
1. Reads per-project profile configs from `.context/profiles/`
2. Runs repomix for each view
3. Computes token counts, writes manifest
4. Triggered by: SessionEnd hook (auto-refresh), manual invocation, or before model-review

### Prompt Caching Mechanics

Both Gemini and OpenAI do automatic prefix caching:

| Provider | Caching | Discount | Min tokens | TTL |
|----------|---------|----------|------------|-----|
| Gemini | Implicit (auto since May 2025) | 90% on cached reads | 32K | Short-lived (auto) |
| OpenAI/GPT | Automatic | 50% on cached reads | 1K | ~minutes |

**Key requirement:** Prefix must be byte-identical across calls for cache hits.

**Context structure for caching:**
```
[STABLE PREFIX - cached across reviews]
  Constitution + GOALS.md
  Project architecture reference
  Base context (repomix output of the codebase)

[VARIABLE SUFFIX - changes per review]
  Topic-specific files or diffs
  The actual review prompt
```

If we review the same project 3 times in a day, calls 2 and 3 get 90% cheaper on Gemini.

### Consumption Flow (model-review)

1. Claude picks relevant views from manifest based on review topic
2. Composes: constitution.md + selected views + topic-specific content + prompt
3. Fires two parallel Bash calls (Claude Code supports multiple Bash tools in one turn)
4. Reads both outputs, synthesizes

### llmx Changes

| Change | Why |
|--------|-----|
| Fix `--json` to set `response_format` | Structured output for merge-not-summarize synthesis |
| Add `--system` flag | System msg = separate cache prefix from user content |
| Add `-f/--file` flag | Cleaner than `cat ... \|` piping |

### What We Decided NOT to Build

- `llmx review` subcommand — parallel `&` + `wait` in shell is simpler
- Automatic view selection — Claude picking from manifest is better than heuristics
- Python repomix wrapper — CLI is fine

## CURRENT llmx SOURCE CODE

### cli.py (the CLI interface)

```python
# Key facts:
# - No --system flag on CLI (system only available via Python API)
# - Stdin is concatenated into user message: stdin + "\n\n" + prompt
# - No -f/--file flag; files must be piped via cat
# - --json flag exists but only affects stderr logging, NOT response_format
# - --compare dispatches to multiple providers in parallel via ThreadPoolExecutor
# - chat_cmd passes everything to providers.chat()

@click.command("chat")
@click.argument("prompt", nargs=-1, required=False)
@click.option("-m", "--model", ...)
@click.option("-p", "--provider", default=None, ...)
@click.option("-t", "--temperature", default=None, type=float, ...)
@click.option("--reasoning-effort", type=click.Choice(["minimal", "low", "medium", "high"]), ...)
@click.option("--stream/--no-stream", default=False, ...)
@click.option("--compare", is_flag=True, ...)
@click.option("--timeout", default=120, type=int, ...)
@click.option("--json", "json_output", is_flag=True, ...)
@click.option("--fast", is_flag=True, ...)
@click.option("--search", is_flag=True, ...)
```

Stdin handling:
```python
if not sys.stdin.isatty():
    stdin_text = sys.stdin.read().strip()
if stdin_text and prompt_text:
    prompt_text = f"{stdin_text}\n\n{prompt_text}"
```

### providers.py (dispatch layer)

```python
# Everything routes through LiteLLM. No custom provider abstraction.
# Messages are built as: [{"role": "user", "content": prompt}]
# No system message support in CLI path.
# Temperature is validated/adjusted per model restrictions.

PROVIDER_CONFIGS = {
    "google": {"model": "gemini/gemini-3.1-pro-preview", ...},
    "openai": {"model": "gpt-5.2", ...},
    "anthropic": {"model": "anthropic/claude-opus-4-6", ...},
    "xai": {"model": "xai/grok-4", ...},
    ...
}

MODEL_RESTRICTIONS = {
    "gpt-5.2": {"temperature": 1.0, "fixed": True, "reasoning_effort": True},
    "gemini-3.1-pro": {"temperature": 1.0, "fixed": True, "reasoning_effort": True},
    ...
}

def chat(prompt, provider, model, temperature, reasoning_effort, stream, ...):
    messages = [{"role": "user", "content": prompt}]
    completion_kwargs = {
        "model": model_name,
        "messages": messages,
        "temperature": adjusted_temp,
        "timeout": timeout,
    }
    if reasoning_effort and provider in ("openai", "google"):
        completion_kwargs["reasoning_effort"] = reasoning_effort
    # No response_format parameter ever set
    response = completion(**completion_kwargs, stream=stream)
```

### api.py (Python programmatic API)

```python
class LLM:
    def chat(self, prompt, system=None, temperature=None, **kwargs) -> Response:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = completion(model=self.model, messages=messages, ...)
        return Response(content=..., usage=..., latency=...)

    def stream(self, prompt, **kwargs) -> Iterator[str]:
        # No system message support
        messages = [{"role": "user", "content": prompt}]
        ...

def chat(prompt, provider="google", model=None, system=None, ...) -> Response:
    llm = LLM(provider=provider, model=model, ...)
    return llm.chat(prompt, system=system)

def batch(prompts, provider="google", parallel=3, ...) -> List[Response]:
    # ThreadPoolExecutor with map()
    # No system message support in batch
    ...
```

## REPOMIX CAPABILITIES (v1.12.0)

- **Output formats:** XML (default, best for LLMs), Markdown, JSON, Plain text
- **XML structure:** `<file_summary>`, `<directory_structure>`, `<files><file path="...">`, `<instruction>`, `<git_logs>`
- **Token counting:** Built-in via tiktoken (o200k_base encoding)
- **--compress:** Tree-sitter signature extraction, ~70% token reduction
- **sortByChanges:** Reorders files by git activity frequency (most-changed first)
- **--include-diffs / --include-logs:** Git integration
- **--config path:** Per-profile config files (workaround for no native profiles)
- **output.instructionFilePath:** Embeds custom instructions/prompts in output
- **MCP server:** Built-in (`npx repomix --mcp`), exposes pack_remote_repository, pack_local_directory
- **Python wrapper:** Third-party `python-repomix` on PyPI
- **Node.js API:** Official, `runCli()` function
- **No token budget enforcement** — counting only, no truncation
- **No multiple profiles in one config** — open feature request (#325)

## PROMPT CACHING RESEARCH

**Gemini implicit caching (since May 2025):**
- Automatic, no API changes needed
- 90% discount on cached reads
- Requires identical token prefix
- Works across separate API calls if within TTL
- Min 32K tokens for explicit caching; implicit has lower threshold

**Gemini explicit caching:**
- `cacheContent` API for long-lived caches
- Configurable TTL
- Best for: large static datasets queried multiple times
- Cost: one-time write fee + storage + 90% reduced reads

**OpenAI automatic caching:**
- Automatic for prompts >1024 tokens
- 50% discount
- Prefix matching
- No API changes needed

**For our use case (llmx calling via LiteLLM):**
- Gemini implicit caching kicks in automatically if prefix is stable
- OpenAI automatic caching kicks in automatically for >1K token prompts
- The key is: **stable prefix structure** (same content, same order, byte-identical)
- System message is ideal for the stable prefix (constitution + base context)
- But llmx CLI has no --system flag — everything goes in user message currently

## USER'S CURRENT REPOMIX USAGE PATTERNS

```bash
# Full repo minus CSS
repomix --copy --ignore "public/css" && rm repomix-output.xml

# Markdown journals only
repomix --copy --include "journals/**/*.md,pages/**/*.md" --ignore "logseq/bak/**,logseq/**,**/.git/**"

# Everything minus media/config
repomix --copy --ignore ".obsidian/**,.git/**,*/.git/**,**/*.png,**/*.jpg,..."

# Source + diffs
repomix --copy --include-diffs --output /dev/null --include "src/**,README.md"
```

These show the pattern: different include/ignore profiles for different purposes, clipboard output, cleanup of the output file.

## QUESTIONS FOR THE REVIEWER

1. Is the `.context/` directory the right abstraction? Should views be stored differently?
2. Is SessionEnd the right trigger for regeneration, or is it wasteful for sessions that don't change code?
3. Should we pursue Gemini explicit caching (via the API) or is implicit sufficient?
4. Is the repomix XML format actually optimal, or would a different structure work better for each model?
5. Are there important views we're missing beyond full/src/docs/infra/signatures/filetree/diffs?
6. The `--system` flag for llmx: is it worth the effort given that Gemini and GPT both cache user message prefixes automatically?
7. Is the manifest.json approach over-engineered for what's essentially a directory of files with timestamps?
