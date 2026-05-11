# Skill & MCP Server DX — 2026 Best Practices

Date: 2026-05-11
Audience: AI agent developers consuming `corpus_core` + `corpus-mcp` + a Claude Code plugin bundle.
Scope: scaffolding, testing, hot-reload, observability, distribution, type safety, common DX pitfalls.

---

## TL;DR — Recommended DX Patterns

1. **Ship as a Claude Code plugin, not a loose skill.** Plugins are the canonical distribution format — `.claude-plugin/plugin.json` + `skills/` + `.mcp.json` in one repo. Install is `/plugin install <plugin>@<marketplace>`. ~4,200+ skills and 770+ MCP servers are distributed via plugins as of mid-2026, so plugin-shape is what users expect.
2. **Author skills as folders, not files.** Each skill is `<plugin>/skills/<name>/SKILL.md` with optional `references/`, `examples/`, `scripts/` for progressive disclosure. SKILL.md body stays in context for the rest of the session — keep it under ~500 lines.
3. **Test MCP servers in-memory with FastMCP `Client(server)`.** Sub-millisecond, deterministic, no subprocess, no network. Cover 4 patterns: tool-call assertions, schema validation, parameterized edge cases, transport tests.
4. **Test skills with the official `skill-creator` plugin.** It is the de-facto eval harness — Executor/Grader/Comparator/Analyzer subagents, blind A/B comparison, `evals/evals.json` next to each skill. No need for DSPy/promptfoo at this scale.
5. **Instrument with OpenTelemetry, not custom logging.** FastMCP emits OTel spans natively under MCP semantic conventions — point at `otel-desktop-viewer` locally, Tempo/Jaeger/SigNoz in prod. Never `print()` from a stdio server (corrupts the JSON-RPC stream) — use `stderr` and OTel spans only.
6. **Hot-reload is solved at the Claude Code layer.** Claude Code 2.1.x watches `~/.claude/skills/`, project `.claude/skills/`, and `--add-dir` skills directories — edit-save-test loop is already < 1s with no restart.
7. **Keep tool surface tight.** 5–15 tools per server is the sweet spot. Polymorphic outcome-oriented tools beat one-tool-per-endpoint by every measured metric (GitHub Copilot 40→13, Block Linear 30+→2, Speakeasy: 95% accuracy at 20 tools collapses near 0% at 107).

---

## Per-Area Best Practice

### Scaffolding & Templates

**Authority chain (use in this order):**

1. `anthropics/claude-plugins-official` — `plugins/example-plugin/` is the canonical template (34 plugins live there as of May 2026: `mcp-server-dev`, `skill-creator`, `plugin-dev`, `hookify`, `pr-review-toolkit`, `code-review`, LSP plugins for 10 languages, etc.).
2. The official `mcp-server-dev` plugin itself contains three meta-skills (`build-mcp-server`, `build-mcp-app`, `build-mcpb`) that scaffold a new MCP server interactively — recommend it to downstream users in our docs.
3. `skill-creator` is Anthropic's meta-skill for authoring + testing skills. Audience that's writing skills against `corpus-mcp` should be pointed at `/plugin install skill-creator@claude-plugins-official` on first contact.

**Required plugin layout:**

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # name, version, description (required)
├── .mcp.json                # MCP server config (optional but expected for MCP plugins)
├── skills/
│   └── my-skill/
│       ├── SKILL.md         # frontmatter + body; <500 lines
│       ├── references/      # loaded only when SKILL.md links to them
│       ├── examples/
│       └── scripts/         # executed via ${CLAUDE_SKILL_DIR}/scripts/...
├── commands/                # optional, merged with skills as of 2.1.x
├── agents/
└── README.md
```

**SKILL.md frontmatter that actually matters:** `description` (claude uses it for auto-routing — put key trigger first, capped at 1,536 chars total with `when_to_use`), `allowed-tools` (pre-approves bash patterns), `disable-model-invocation` (`true` for side-effect commands), `paths` (glob-scoped activation), `context: fork` (run in a subagent — but only with explicit task content, not reference material).

### Skill Testing

**Use `skill-creator`'s 5-dimension audit:** frontmatter completeness, description pushiness, line-count compliance, WHY explanations, eval pass rate. This is the closest thing to a community standard.

**Eval format that works:** drop `evals/evals.json` inside each skill with 3 cases — one positive trigger, one negative trigger (must NOT activate), one edge case. The `skill-creator` Executor runs them; the Grader scores; the Comparator does **blind A/B** vs prior version to avoid commitment bias. That blind-comparator pattern is genuinely good and worth copying for our internal evals.

**Avoid DSPy/promptfoo for skill behavior testing** at this scale — those are valuable for prompt programs with structured I/O, not for the natural-language router-and-instruction shape of skills. The skill-creator harness is closer to what you actually need.

### MCP Testing (FastMCP, where 70% of MCP servers live)

The fixture below is the entire test setup. It runs in-memory, no subprocess, no network:

```python
# tests/conftest.py
import pytest
from fastmcp import FastMCP, Client
from corpus_mcp.server import build_server  # your factory

@pytest.fixture
def server() -> FastMCP:
    return build_server(config=...)  # fresh instance per test

# tests/test_tools.py
async def test_tool_call(server):
    async with Client(server) as client:
        result = await client.call_tool("search_corpus", {"query": "x"})
        assert result.data["hits"]
```

**Four mandatory test patterns (from `dev.to/klement_gunndu` + jlowin's own blog):**

1. **Tool-call assertions** — call each tool with realistic params, assert response shape.
2. **Schema validation** — `await client.list_tools()` + assert names, descriptions ≥10 chars, parameter types match. Catches silent schema drift that breaks LLM routing.
3. **Parameterized edge cases** — `@pytest.mark.parametrize("invalid_days", [0, -1, 15, 100])` on every numeric/enum param. LLMs send weird inputs.
4. **Transport tests** (separate module) — use `run_server_async` for in-process HTTP + `StreamableHttpTransport`. Don't mix with logic tests.

**Anti-pattern jlowin names "vibe-testing":** firing up Claude Desktop, typing a prompt, eyeballing the output. Stochastic, slow, opaque, no edge-case coverage. Do not ship this as your test story.

**FastMCP's own `tests/conftest.py`** uses `tmp_path` per-test isolation, OTel `InMemorySpanExporter` for span assertions, and auto-marks anything under `integration_tests/` with `pytest.mark.integration` — copy these patterns directly.

### Hot Reload / Dev Loop

**Skills:** Claude Code 2.1.x watches `~/.claude/skills/`, project `.claude/skills/`, and `.claude/skills/` inside `--add-dir` targets. Edits land within the current session. Creating a *new* top-level skills directory still requires restart.

**MCP servers:** No native hot-reload — you must restart the server process. Pragmatic options:

- Run `mcp-inspector` (`npx @modelcontextprotocol/inspector uv run server.py`) and `/reload-plugins` in Claude Code to re-pull tool list. 9.7K-star repo, transport-agnostic, React UI.
- For tight inner-loop: FastMCP's in-memory `Client(server)` in a pytest test is faster than any Inspector reload — write the change, hit save, pytest reruns in ms.

**The recommended dev loop:** edit → in-memory pytest (sub-second) → mcp-inspector once for protocol sanity → `/reload-plugins` in Claude Code for end-to-end.

### Type-Safe MCP Clients

The 2026 state: **generate from OpenAPI both directions.**

- **Server-side:** `FastMCP.from_openapi(spec)` converts an OpenAPI doc directly to an MCP server. `openapi-mcp-generator` (TS) generates standalone Zod-validated servers. Stainless and Speakeasy do this as part of SDK generation.
- **Client-side:** typed clients are still rough. FastMCP's Python `Client` is async and type-hinted but not codegen'd. For TS, Speakeasy generates the SDK and the MCP server together so the client gets Zod-validated calls.

**Practical recommendation:** publish your MCP tool schemas as a JSON schema export (one command in CI) so downstream agents can codegen typed clients if they want. Don't try to bake a client codegen into `corpus-core` — that's not where the ecosystem standardized.

### Observability

**FastMCP ships OTel out of the box** with the official MCP semantic conventions (`mcp.method.name`, `mcp.session.id`, `mcp.resource.uri`, plus `fastmcp.component.type` etc.). Zero-config CLI:

```bash
pip install opentelemetry-distro opentelemetry-exporter-otlp
opentelemetry-bootstrap -a install
opentelemetry-instrument --service_name corpus-mcp fastmcp run server.py
```

Local viewer: `otel-desktop-viewer` (single binary). Prod: any OTLP backend (Jaeger, Tempo, SigNoz, Datadog, Grafana, traceloop). The `traceloop/opentelemetry-mcp-server` lets agents *read back* their own traces for debugging.

**Critical gotcha for stdio servers:** `print()` / `console.log()` corrupts the JSON-RPC stream. Use `stderr` only (`console.error()` in TS, Python's `logging` with a `stderr` handler) plus OTel spans. This bites every new MCP author.

### Plugin Distribution

**Two paths, both supported:**

1. **Marketplace submission** — submit to `clau.de/plugin-directory-submission` for the official Anthropic-managed catalog (`claude-plugins-official`). Inclusion is curated.
2. **Custom marketplace** — host a git repo with a `marketplace.json` index; users add it once (`/plugin marketplace add <url>`) then `/plugin install <plugin>@<your-marketplace>`. ~2,500+ community marketplaces exist as of May 2026.

For a project like ours, **both**: publish to our own marketplace from day one (full control, fast iteration); submit the polished `corpus-tools` plugin to the official directory once stable. The "manual install via `/plugin install <url>`" middle path is supported but produces a worse first-touch experience than a marketplace.

---

## What to Bake Into `corpus-core` / `corpus-mcp` Scaffolding

**Yes, ship test fixtures.** Concretely:

1. **`corpus_core.testing` module** with a `corpus_server_factory()` and an `async_corpus_client()` pytest fixture that downstream MCPs can `from corpus_core.testing import *` and immediately get FastMCP in-memory testing.
2. **`tests/conftest.py` template** that downstream `corpus-mcp` repos can copy: includes `tmp_path`-isolated config, OTel `InMemorySpanExporter` for span assertions, `pytest.mark.integration` auto-marker, `pytest-asyncio` mode strict.
3. **An `evals/` folder convention** in our skills: `evals.json` with positive/negative/edge cases, runnable by `skill-creator`. Document the format in our plugin README so contributors know where to add cases.
4. **A `just dev` recipe** that runs: `mcp-inspector` against the local server + `pytest --watch` + `otel-desktop-viewer` in one tmux pane. This is the loop downstream devs should use.
5. **`schemas/` export** — one `just export-schemas` recipe writes tool JSON schemas to disk so contributors can codegen typed clients. Don't generate the clients ourselves.
6. **Plugin scaffold via `mcp-server-dev`** — point new contributors at `/plugin install mcp-server-dev@claude-plugins-official` and `/mcp-server-dev:build-mcp-server` rather than writing our own scaffolder. Reuse, don't reinvent.

### Minimal "Hello World" Plugin Install Experience

The bar to clear:

```
# In a fresh Claude Code session
/plugin marketplace add https://github.com/<our-org>/corpus-marketplace
/plugin install corpus@corpus-marketplace
/reload-plugins
> What's in my corpus?
```

Three commands, then it works. If a user needs to set env vars, follow the `.mcp.json` env-var pattern (Claude Code prompts for missing vars on first call) — never put it in a README "before you start" section.

---

## Anti-Patterns to Avoid

1. **One MCP tool per REST endpoint.** Speakeasy data: at 107 tools, task success ≈ 0%; at 20 tools, 95%; at 10 tools, near-perfect. Block Linear: 30+ → 2. GitHub Copilot: 40 → 13 = +2-5pp benchmark + 400ms latency cut. **Aim for outcome-oriented polymorphic tools, 5-15 per server.**
2. **`print()` / `console.log()` from a stdio server.** Corrupts JSON-RPC. Stderr + OTel only.
3. **Vibe-testing.** Manual prompts in Claude Desktop are not tests — they're hope. Atomic deterministic in-memory tests catch schema drift, edge cases, regression. Required from day one.
4. **Subprocess test harnesses.** `subprocess.Popen` + sleep + stdin pipe = flaky, slow, port-conflict-prone. Use `Client(server)` in-memory.
5. **Hand-rolled hot-reload code.** Claude Code already watches the skills dirs. Just leverage it.
6. **Custom logging frameworks.** Use OTel. The ecosystem standardized.
7. **`npx`-installed MCPs in security-sensitive contexts.** Unpinned `npx` fetches latest from npm — supply-chain risk. Pin versions or use `uvx --from <git+ssh>`/MCPB-bundled installs for our own distribution.
8. **Auto-invocable skills with side effects.** Use `disable-model-invocation: true` for anything that deploys, commits, sends, deletes. Don't let Claude decide your timing on irreversible ops.
9. **Reference-content skills in `context: fork`.** Forked skills need a *task*, not just guidelines. Reference-only skills should run inline.
10. **DSPy/promptfoo for skill behavior testing.** Wrong shape — use `skill-creator`'s eval harness.

---

## Sources

- [Anthropic — Claude Code Skills docs](https://code.claude.com/docs/en/skills)
- [Anthropic — `claude-plugins-official` repo](https://github.com/anthropics/claude-plugins-official) (34 plugins including `mcp-server-dev`, `skill-creator`, `plugin-dev`, `hookify`)
- [Claude Code Plugin Marketplace docs](https://code.claude.com/docs/en/discover-plugins)
- [Karkera — Complete Guide to Testing Claude Code Skills With the Skill Creator (Mar 2026)](https://medium.com/@karkeralathesh/the-complete-guide-to-testing-claude-code-skills-with-the-skill-creator-1ae3821bd7b8) — 5 eval dimensions, blind comparator pattern
- [FastMCP — Testing docs](https://gofastmcp.com/development/tests) — in-memory `Client(server)` fixtures
- [jlowin — "Stop Vibe-Testing Your MCP Server"](https://jlowin.dev/blog/stop-vibe-testing-mcp-servers) — atomic deterministic testing rationale
- [MCPcat — Unit Testing MCP Servers](https://mcpcat.io/guides/writing-unit-tests-mcp-servers/)
- [klement_gunndu — 4 Test Patterns for MCP Servers](https://dev.to/klement_gunndu/your-mcp-server-has-no-tests-here-are-4-patterns-to-fix-that-2k59)
- [FastMCP — OpenTelemetry integration](https://gofastmcp.com/servers/telemetry) — MCP semantic conventions, zero-config OTel
- [OpenTelemetry — MCP semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/mcp/)
- [traceloop/opentelemetry-mcp-server](https://github.com/traceloop/opentelemetry-mcp-server) — agents reading their own traces
- [modelcontextprotocol/inspector](https://github.com/modelcontextprotocol/inspector) — 9.7K stars, transport-agnostic UI
- [AWS Heroes — MCP Tool Design: Why Your AI Agent Is Failing](https://dev.to/aws-heroes/mcp-tool-design-why-your-ai-agent-is-failing-and-how-to-fix-it-40fc) — GitHub 40→13, Block 30+→2, Speakeasy tool-count curve
- [Speakeasy — Generate MCP from OpenAPI](https://www.speakeasy.com/blog/generate-mcp-from-openapi)
- [FastMCP — OpenAPI integration](https://gofastmcp.com/integrations/openapi)
- FastMCP `tests/conftest.py` ([jlowin/fastmcp](https://github.com/jlowin/fastmcp)) — reference conftest with tmp_path isolation, OTel InMemorySpanExporter, xdist worker_id fixture
- [Toolradar — MCP Security Best Practices 2026](https://toolradar.com/blog/mcp-server-security-best-practices) — Jan 2026 scan: 66% of MCP servers had security findings, 43% command-injection

<!-- knowledge-index
generated: 2026-05-11T07:46:14Z
hash: 702c1c2dfc0c


end-knowledge-index -->
