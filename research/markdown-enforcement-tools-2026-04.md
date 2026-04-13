## Markdown Enforcement & Schema Validation Tools — Survey

**Question:** Are there newer tools (2025-2026) for structured markdown enforcement, schema validation, or markdown-as-database that go beyond basic linting?
**Tier:** Quick-Standard | **Date:** 2026-04-03

### Summary Verdict

Yes, a small but genuine wave of tools emerged in 2025-2026, mostly driven by the AI-agent-writes-markdown pattern (Obsidian vaults, knowledge bases, agent memory). Nothing is mature (>1.0, >500 stars, production-proven). The landscape splits into four categories. For our use case (enforcing frontmatter schemas + structural conventions in agent memory files), **mdschema + a custom 50-line Python validator** remains the pragmatic answer — but mdschema is worth evaluating as a real dependency.

---

### 1. YAML Frontmatter Schema Validation

| Tool | Language | What it does | Stars | Maturity | Notes |
|------|----------|-------------|-------|----------|-------|
| **remark-lint-frontmatter-schema** | JS (remark) | Validates frontmatter against JSON Schema via remark-lint plugin | ~100 | Stable (2022+) | The incumbent. Works if you're already in the remark ecosystem. JSON Schema for frontmatter fields. No structural markdown validation. |
| **mdschema** | Go | Declarative YAML schema for markdown structure AND frontmatter | 54 | Active (2025-07) | Most interesting find. Validates heading hierarchy, code block languages, required sections, frontmatter field types/formats (email, URL, date), word counts, image alt-text, table columns. GitHub Action available. |
| **lintel** | Rust | JSON Schema validation for YAML/JSON config files | 2 | Pre-alpha (v0.0.19) | General YAML linter, not markdown-specific. Could validate frontmatter if extracted separately. |
| **Front Matter CMS (VS Code)** | TS | VS Code extension with frontmatter schema support | 2K+ | Mature | Full CMS-in-editor. Schema validation is a feature, not the product. Overkill unless you want the full CMS experience. Issue #990 tracks deeper schema/validation support (open since Dec 2025). |
| **giantswarm/frontmatter-validator** | Go | Hugo-specific frontmatter validation | 0 | Niche | Single-purpose, single-org. |

**Assessment:** `remark-lint-frontmatter-schema` is the only battle-tested option but requires the remark Node.js ecosystem. `mdschema` is the first tool that validates both frontmatter AND document structure in a single declarative schema — genuinely new capability. Worth a `brew install` to evaluate. Everything else is either too narrow or too immature.

[SOURCE: https://github.com/jackchuka/mdschema]
[SOURCE: https://github.com/JulianCataldo/remark-lint-frontmatter-schema]

---

### 2. Markdown-as-Database (Structured Queries)

| Tool | Language | What it does | Stars | Maturity | Notes |
|------|----------|-------------|-------|----------|-------|
| **grubber** | Crystal/Ruby | Extracts YAML frontmatter + code-block YAML into queryable records (JSON/TSV). Pipe to jq/nushell. | 14 | Active (v0.7.2, Mar 2026) | Unix-philosophy: extracts, doesn't query. 1K files in <50ms (Crystal). Merges frontmatter with inline YAML blocks. |
| **matterbase** | Python | TUI for querying frontmatter with field filters + full-text search | 10 | Early (no releases) | Built on grubber. Nushell pipelines for table manipulation. Interactive but not scriptable. |
| **mdbasequery** | TypeScript | Obsidian-compatible query engine: filter, sort, group, computed columns over frontmatter | 4 | Early (v0.0.1, Feb 2026) | SQL-like expressions: `--filter "score >= 7" --sort score:desc`. Works as CLI and library. Multi-runtime (Node/Bun/Deno). |
| **groundDb** | Rust | Schema-driven DB stored as markdown files. SQL views, file watching, typed codegen. | 1 | Concept (Feb 2026) | Ambitious but essentially vaporware (14 downloads). Interesting idea: define schema, data lives in .md files, get SQL views and typed Rust structs. |
| **QMD** | TypeScript | MCP server for hybrid BM25 + vector search over markdown knowledge bases | 4 | Early (Jan 2026) | Search tool, not a query engine. Indexes markdown for retrieval by AI agents. |
| **markdown-vault-mcp** | Python | FTS5 + semantic search over markdown with frontmatter-aware indexing | 3 | Early (Mar 2026) | Another MCP-based search layer. SQLite FTS5 backend. |

**Assessment:** Nothing here replaces `sqlite3` + a 30-line Python frontmatter extractor. The grubber approach (extract to JSON, pipe to jq) is the most honest — it admits markdown isn't a database and provides a good extraction layer instead. mdbasequery has the right API shape but is too early. groundDb is architecturally interesting (schema-first markdown storage) but has zero traction.

For our actual use case: `scripts/sessions.py` already does FTS5 over session data. A similar pattern (Python script that reads frontmatter with `yaml.safe_load`, loads into SQLite, queries) would be 50 lines and zero dependencies beyond stdlib+pyyaml.

[SOURCE: https://github.com/rhsev/grubber]
[SOURCE: https://github.com/intellectronica/mdbasequery]
[SOURCE: https://github.com/justmaier/groundDb]

---

### 3. Convention Enforcement (Beyond markdownlint)

| Tool | Language | What it does | Stars | Maturity | Notes |
|------|----------|-------------|-------|----------|-------|
| **Vale** | Go | Prose linting with custom rule packages. Markup-aware. | 7K+ | **Mature** | The standard for prose quality enforcement. Not new (2018+) but still the only production-grade option for custom style enforcement. Used by GitLab, Grafana, Datadog. Pragmatic Press book published 2025. Rules are YAML-defined regex/NLP patterns grouped into packages. |
| **contextlint** | TypeScript | Cross-file structural integrity: broken references, duplicate IDs, traceability chains, DAG validation | 25 | Active (Mar 2026, 154 commits) | **Genuinely new capability.** Not a linter — it's a structural integrity checker for markdown document graphs. Rules: table column validation, required sections, ID cross-references, acyclic graph validation, placeholder detection. JSON config with schema. Designed for "Spec Driven Development." |
| **mdlint-obsidian** | Python | 22-rule Obsidian-flavored markdown linter | 0 | Early (Mar 2026) | Catches unclosed wikilinks, invalid frontmatter, broken links. Niche. |
| **github/markdownlint-github** | JS | GitHub's opinionated markdownlint rule set | ~100 | Stable | Not new, but a good reference for custom markdownlint rule authoring. |

**Assessment:** Vale is the only mature option beyond markdownlint. It solves a different problem (prose quality, not structure) but is genuinely useful for enforcing terminology, voice, and style in documentation. contextlint is the most interesting new find — it validates cross-file referential integrity in markdown repos, which no other tool does. If you have markdown files that reference each other (IDs, anchors, traceability chains), contextlint catches broken references deterministically. Worth evaluating for repos where markdown files form a graph (like our research memos with cross-references).

[SOURCE: https://vale.sh]
[SOURCE: https://github.com/nozomi-koborinai/contextlint]

---

### 4. Markdown Conventions + Programmatic Enforcement Bridge

| Approach | Implementation | Notes |
|----------|---------------|-------|
| **mdschema** (above) | Go binary + GitHub Action | Closest to "schema for markdown" — single YAML file defines what a valid .md file looks like |
| **contextlint** (above) | TypeScript CLI | Cross-file integrity, not per-file schema |
| **Claude Code hooks** (what we already have) | Bash/Python hooks triggered on file write | `postwrite-source-check.sh` enforces provenance tags on writes. This is already our enforcement layer. |
| **Custom Python validator** | 50-100 lines | Read frontmatter with yaml.safe_load, validate against a JSON Schema (jsonschema library), check required sections with regex. Zero new dependencies if pyyaml already present. |

**Assessment:** The bridge between "markdown conventions" and "programmatic enforcement" is still mostly DIY. mdschema is the first tool that attempts to be a general-purpose bridge, and it's the most worth evaluating. But our existing hook infrastructure (Claude Code hooks + Python validators) already provides enforcement at the right layer — the moment of writing, not post-hoc CI. A hook that validates frontmatter schema on file write is architecturally better than a CI-only check.

---

### What's Genuinely New vs. What We Already Have

**Genuinely new (2025-2026):**
- mdschema: declarative schema for entire markdown document structure (not just frontmatter, not just formatting)
- contextlint: cross-file referential integrity for markdown document graphs
- grubber/mdbasequery: extraction layers that treat markdown frontmatter as queryable data
- MCP-based markdown search servers (QMD, markdown-vault-mcp): AI-agent-oriented search over markdown vaults

**Not new, just newly popular:**
- Vale (2018+): prose linting with custom rules. Mature and useful but not 2025-2026.
- remark-lint-frontmatter-schema (2022+): JSON Schema validation for frontmatter. Stable.
- markdownlint custom rules: always been possible, just rarely done well.

**What custom scripts still do better:**
- Anything requiring project-specific logic (our frontmatter format, our provenance tags, our cross-project references)
- Enforcement at write-time via hooks (no CI tool does this)
- SQLite-backed queries over extracted frontmatter (50 lines of Python beats any of the query tools above)

### Bottom Line

Nothing here justifies replacing our hook-based enforcement. Two tools are worth knowing about:

1. **mdschema** — if you want a standardized way to define "what a valid markdown file looks like" that others could adopt. Evaluate with `go install github.com/jackchuka/mdschema@latest`. 54 stars, active, Go binary, MIT.

2. **contextlint** — if cross-file referential integrity becomes a pain point (broken links between research memos, orphaned references). 25 stars, TypeScript, actively developed.

Everything else is either too immature (<5 stars, v0.0.x) or solves a problem we don't have.

<!-- knowledge-index
generated: 2026-04-04T00:42:57Z
hash: 13990ca132b6


end-knowledge-index -->
