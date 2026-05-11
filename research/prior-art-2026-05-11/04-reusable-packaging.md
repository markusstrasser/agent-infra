---
title: Reusable Packaging for corpus_core + Scientific Substrate
date: 2026-05-11
tags: [packaging, uv-workspace, mcp, plugins, scientific-substrate, oss]
status: research-memo
audience: AI Agent developers designing the corpus substrate for reuse
inputs:
  - research/scientific-substrate-target-architecture.md
  - PaperQA2, mem0, cognee, fastmcp, dvc pyproject.toml + source layouts
  - Claude Code plugin docs (code.claude.com/docs/en/plugins)
  - uv workspace documentation (docs.astral.sh/uv)
---

# Reusable Packaging for `corpus_core` + Scientific Substrate

## TL;DR — Recommended Packaging Shape

**Single GitHub repo, `uv` workspace, ~5 published packages, one Claude Code plugin bundle.** Concretely:

```
corpus/                          (repo root; published as the workspace)
├── pyproject.toml               (workspace root, tool.uv.workspace = ["packages/*"])
├── packages/
│   ├── corpus-core/             pip install corpus-core   (store layout, IDs, schemas, validators)
│   ├── corpus-cli/              pip install corpus-cli    (CLI on top of corpus-core)
│   ├── corpus-mcp/              uvx corpus-mcp            (MCP server; depends on corpus-core)
│   ├── corpus-extractors/       optional; built-in extractor adapters
│   └── corpus-plugin-claude/    Claude Code plugin bundle (skills + hooks + .mcp.json)
└── docs/
```

Why this shape:
- **`corpus-core` is the contract** (schemas + identity rules + store layout). Per-repo MCPs in `phenome`/`genomics`/`intel` install it and implement the shared interface contract from §"Per-repo MCP shared interface" of the target architecture memo.
- **`corpus-mcp` is the canonical-store MCP.** Distributed via `uvx corpus-mcp` (2026 standard, see PyPI MCP server pattern).
- **`corpus-plugin-claude` is the Claude Code-native distribution.** Ships skills + hooks + `.mcp.json` declaring `corpus-mcp` via `uvx`. Users get the full kit with `/plugin install corpus`.
- **Plugin packages for extractors and per-repo bindings live in *consumer* repos** (genomics/phenome/intel), not in the corpus monorepo. They declare `corpus-core>=X` as a dependency and implement a typed plugin protocol exposed by `corpus-core`.

This is the **PaperQA2 pattern** ([Future-House/paper-qa workspace](https://github.com/Future-House/paper-qa)) with **DVC-style extras** ([iterative/dvc-data subpackages](https://github.com/iterative/dvc)) and the **Claude Code plugin bundle** as the user-facing wrapper.

---

## Single-Package vs Workspace vs Plugins — Comparison

| Shape | Examples | Pros | Cons | Fit for corpus |
|---|---|---|---|---|
| **Single fat package + extras** | mem0 (`mem0[vector_stores,llms,extras]`), cognee (single PyPI `cognee==1.0.9` with `[postgres,neo4j,scraping,fastembed]` extras) | One install line; simple PyPI release | Extras explode (mem0 has 6 extras groups, 50+ optional deps); heavy core; vendor-coupled deps; users pull deps for backends they don't use | **No** — bundled backends contradict our small-footprint per-repo MCP model |
| **Monorepo, multiple PyPI packages, uv workspace** | PaperQA2 (`paper-qa`, `paper-qa-pypdf`, `paper-qa-pymupdf`, `paper-qa-docling`, `paper-qa-nemotron`), DVC (`dvc`, `dvc-data`, `dvc-objects`, `dvc-azure`, `dvc-s3`, ...) | Core small; backends opt-in; one repo for dev; one lockfile; PaperQA2's `[tool.uv.workspace] members = ["packages/*"]` is industry standard | More release coordination; users must learn which packages to install | **Yes** — matches our "core + per-repo plugins" mental model |
| **Multi-repo siblings** | `iterative/dvc` + separate `iterative/dvc-data` repos; `topoteretes/cognee` (main) + `topoteretes/cognee-mcp` (subdir in same repo) | Independent lifecycles | More repo overhead; cross-repo PRs hard; no shared CI; tooling friction | **No** — overkill for single-developer phase |
| **Cookiecutter template** | various scientific repo templates | Easy fresh starts | No upgrade path; downstream repos can't pull fixes; not a library | **No** — we want updates, not one-shot scaffolding |
| **Claude Code plugin bundle** | `anthropics/claude-plugins-official`, 2,500+ marketplaces | One-line install for end users; bundles skills+hooks+MCP | Not a Python library; needs underlying Python pkg for code reuse | **Yes, alongside** PyPI packages — for the developer-experience win |

**Decision: monorepo + uv workspace + Claude Code plugin bundle on top.** This is what PaperQA2, DVC, and cognee-mcp converge on.

---

## MCP Distribution Recommendation

The 2026 standard for Python MCP servers (verified across `mcp-server-git`, `mcp-server-fetch`, `aws-mcp`, `azure-mcp`, `postgres-mcp-server`, and the cognee-mcp subdirectory):

**Publish to PyPI as a regular package, declare a `[project.scripts]` entry, advertise `uvx <pkg>` as the installation command.**

```toml
# packages/corpus-mcp/pyproject.toml
[project]
name = "corpus-mcp"
version = "0.1.0"
dependencies = [
    "corpus-core>=0.1,<0.2",
    "mcp>=1.24.0,<2.0",
    "fastmcp>=2.0",
    "duckdb>=1.1",
]

[project.scripts]
corpus-mcp = "corpus_mcp.server:main"
```

User installs via Claude Code's `.mcp.json`:
```json
{
  "mcpServers": {
    "corpus": {
      "command": "uvx",
      "args": ["corpus-mcp"]
    }
  }
}
```

**Reject Docker as the primary distribution.** Docker is the cdata.com / Snyk recommendation for *enterprise* MCPs, but the genomics/phenome/intel projects run uvx-native and Docker layering would just add cold-start latency. Provide a `Dockerfile` for users who want it (cognee ships one), but document `uvx` as the path of first choice.

**Bundle the MCP into the Claude Code plugin too** — `corpus-plugin-claude/.mcp.json` declares the `uvx corpus-mcp` command, so users get one install (`/plugin install corpus`) and Claude Code spawns the MCP via `uvx` automatically.

---

## Multi-Project Install / Config Story

### Filesystem path discovery — three layers, in order

`corpus_core.config.resolve_corpus_root()` checks, in order:
1. **Explicit kwarg:** `Corpus(root="/path/to/corpus")` — for tests and ad-hoc use.
2. **Env var:** `CORPUS_ROOT=/Users/markus/Projects/corpus` — for shells and CI.
3. **`pyproject.toml`:** `[tool.corpus] root = "../corpus"` — for per-project pinning. Resolved relative to the project's `pyproject.toml`.
4. **Default:** `platformdirs.user_data_dir("corpus")` — XDG-respecting, `~/.local/share/corpus` on Linux, `~/Library/Application Support/corpus` on macOS, `XDG_DATA_HOME` honored.

This is the [platformdirs](https://platformdirs.readthedocs.io/) pattern used by `dvc`, `pip`, `ruff`. Avoids hardcoding `~/Projects/corpus/` while letting our current setup keep working via env var.

### DuckDB graph index — shared file, per-project derivative views

The `graph.duckdb` lives at `<corpus_root>/graph.duckdb` (one file, shared). Per-project queries use `DuckDB ATTACH` against per-repo DuckDBs (genomics' `knowledge.duckdb`, phenome's claims store) to join across the canonical source identity. No copy, no sync — one read path.

This avoids the "shared DB" pitfall (concurrent-write contention) because corpus annotations write to JSONL (atomic `O_APPEND` per the target arch memo §Q3), and `graph.duckdb` is rebuilt-on-demand from annotations + INDEX.json. Single writer = the indexer; readers are everywhere.

### Per-project schemas — versioned via `corpus.schemas` namespace

Each project's annotation schema versions itself: `genomics.annotation.v2.json` lives in `~/Projects/genomics/schemas/`, but is *registered* with `corpus_core` via entry_points:

```toml
# genomics/pyproject.toml
[project.entry-points."corpus.schemas"]
genomics_annotation = "genomics.schemas:annotation_v2"
```

`corpus_core` discovers all registered schemas at startup (via `importlib.metadata.entry_points(group="corpus.schemas")`) and validates annotations against the right schema based on the annotation's `repo` field. This is the [Python entry_points plugin discovery pattern](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/) — standard since PEP 660 — and is what pytest, jupyter, sphinx use.

---

## Schema Governance for Reuse

Versioning rule: **annotation/claim/verdict schemas live in `corpus_core/schemas/`, versioned by integer (`v1`, `v2`), never deleted, never edited.** v2 lives alongside v1; writers stamp the version into each row.

Migration story (copying DVC and pytest's playbook):

| Scenario | Pattern |
|---|---|
| Add a field (forward-compat) | Bump minor version. v1 readers ignore extras. No migration. |
| Rename a field | Bump major. v1 writers shut off (corpus_core raises). v1 rows still readable; new rows in v2. Migration script `corpus migrate-schema --from v1 --to v2 --dry-run` provided. |
| Restructure (e.g., annotation_id changes algorithm) | New schema name (`annotation.v2`) + new file (`annotations.v2.jsonl`). v1 file frozen, readable forever. |

**No migrate-in-place ever.** Append-only stores never rewrite history. The `supersedes_event` mechanism from the target arch (genomics' verdict_supersedings) carries forward — schema-level supersession via `corpus_core.supersede(old_id, new_record_id)`.

This matches the Constitution Principle 14 (breaking refactors by default) for *new* schemas, but preserves *historical readability* — the dual we keep getting right in genomics/phenome.

---

## Configuration — `~/.config/corpus/config.toml`

**TOML file, optional, env-var override.** Format follows DVC's `voluptuous`-validated schema model. Example:

```toml
# ~/.config/corpus/config.toml
[store]
root = "~/Projects/corpus"
schema_strict = true             # reject unknown fields in annotations
posix_atomic_append = true       # enforce <= 4096 byte annotation lines

[graph]
duckdb_path = "<store.root>/graph.duckdb"
auto_rebuild = false             # set true for dev; false for prod

[mcp]
extra_repos = ["genomics", "phenome", "intel"]
require_attest = true            # writes must call attest(), not append directly

[telemetry]
enabled = false                  # opt-in only; we don't want PostHog like mem0
```

`corpus_core` resolves via [platformdirs](https://platformdirs.readthedocs.io/): `user_config_dir("corpus") + "/config.toml"`. Env vars (`CORPUS_STORE_ROOT`, `CORPUS_MCP_REQUIRE_ATTEST`) override individual keys. Pyproject `[tool.corpus]` overrides config file. Explicit kwargs override everything.

**Reject pydantic-settings unless we need a dependency** — DVC uses `voluptuous`, cognee uses pydantic-settings (and pays the dep cost). For our scale, `tomllib` (stdlib) + dataclass validators is enough.

---

## Testing Infrastructure for Downstream Projects

Ship two things in `corpus-core`:

### 1. Pytest fixtures: `corpus_core.testing`

```python
# In any downstream project's conftest.py:
from corpus_core.testing import corpus_fixture, sample_annotation

def test_my_extractor(corpus_fixture):
    src = corpus_fixture.add_source(doi="10.1234/example")
    annotation = sample_annotation(source_id=src.id, repo="mytestproject")
    corpus_fixture.attest(annotation)
    assert corpus_fixture.lookup(src.id).annotations[0]["repo"] == "mytestproject"
```

`corpus_fixture` is a pytest fixture that spins a tmpdir-backed corpus, registers a test schema, and tears down at session end. Pattern lifted from `pytest`'s `tmp_path_factory` and DVC's `dvc.testing` (downstream-installable test utilities).

### 2. Reference test corpus: `corpus_core/testing/fixtures/`

5-10 canonical sources (one DOI, one PMID, one db_release, one tool_output, one repo_internal, one no-DOI-no-PMID fallback) shipped as `corpus_core.testing.fixtures.SAMPLE_SOURCES`. Lets downstream code test against a known good corpus state without internet.

### 3. Schema test helper

```python
from corpus_core.testing import schema_compat_test

def test_my_v2_schema():
    schema_compat_test("genomics.annotation.v2",
                      forward_compat_with="genomics.annotation.v1")
```

Asserts v1 readers can ignore v2's new fields. Standard pattern, copying ProtoBuf-style compat testing.

---

## What We Should Copy from {mem0, cognee, fastmcp, dvc}

### From mem0 — copy: factory pattern; reject: bundled extras

The `LlmFactory` / `VectorStoreFactory` pattern ([mem0/utils/factory.py](https://github.com/mem0ai/mem0)) is clean: dict mapping `provider_name → ("import.path.Class", ConfigClass)`. We'll use this for **extractor dispatch**:

```python
class ExtractorFactory:
    provider_to_class = {
        "pypdf": ("corpus_extractors.pypdf.PyPDFExtractor", PyPDFConfig),
        "docling": ("corpus_extractors.docling.DoclingExtractor", DoclingConfig),
        # plugins auto-registered via entry_points:
        # "genomics_vcf": ("genomics.extractors.VCFExtractor", VCFConfig),
    }
```

**Reject mem0's monolithic install.** `mem0[vector_stores]` pulls 20 vector DBs (qdrant + chroma + cassandra + weaviate + pinecone + faiss + ...). We won't repeat that.

### From cognee — copy: per-repo subdirectory MCP; reject: 60-dep core

The `cognee/` + `cognee-mcp/` split inside one repo ([cognee-mcp subdir](https://github.com/topoteretes/cognee/tree/main/cognee-mcp)) is exactly our `packages/corpus-core/` + `packages/corpus-mcp/` shape. The cognee-mcp pyproject declares its own `[project.scripts] cognee-mcp = "src:main_mcp"` — verbatim what we want.

**Reject cognee's "kitchen sink" core**: pinned `numpy`, `pylance`, `ladybug==0.16.0`, `fastapi`, `gunicorn` in the base install. Our `corpus-core` should be `duckdb + pydantic + platformdirs + tomli` and nothing else. Heavy deps move to extras.

### From fastmcp — copy: server framework; reject: telemetry-by-default

Use `fastmcp>=2.0` ([PrefectHQ/fastmcp](https://github.com/PrefectHQ/fastmcp)) as the MCP server framework. It's the de facto standard ("70% of MCP servers across all languages"). Decorator-driven tool registration is exactly the ergonomics we want for the shared interface contract.

```python
# packages/corpus-mcp/src/corpus_mcp/server.py
from fastmcp import FastMCP
from corpus_core import Corpus

mcp = FastMCP("corpus")
corpus = Corpus.from_env()

@mcp.tool
def corpus_lookup(source_id: str) -> dict:
    return corpus.lookup(source_id).model_dump()

@mcp.tool
def corpus_annotate(source_id: str, repo: str, model: str, scope: str, **kw) -> str:
    return corpus.annotate(source_id, repo=repo, model=model, scope=scope, **kw)

def main():
    mcp.run()
```

**Reject fastmcp's opentelemetry-by-default** — we're a personal/single-user system. Don't ship telemetry; add it as `corpus-mcp[telemetry]` if someone wants it.

### From DVC — copy: subpackage architecture; reject: voluptuous

The `dvc[azure]` → installs `dvc-azure>=3.1.0,<4` pattern is the production-grade version of what we want: **core stays small, backends are separate packages that core delegates to via entry_points.** From [iterative/dvc pyproject.toml](https://github.com/iterative/dvc/blob/main/pyproject.toml):

```toml
[project.optional-dependencies]
azure = ["dvc-azure>=3.1.0,<4"]
s3 = ["dvc-s3>=3.2.1,<4"]
gs = ["dvc-gs>=3.0.2,<4"]
```

For us: `corpus-core[genomics]` would pull `corpus-binding-genomics` (a thin shim that registers genomics' schemas via entry_points and exposes its claim-store interface to corpus-mcp). Same shape, different domain.

**Reject voluptuous** — pydantic is now the standard and ships with everything else we use. DVC chose voluptuous in 2017 before pydantic v2 existed.

### From PaperQA2 — copy: workspace layout verbatim

[Future-House/paper-qa](https://github.com/Future-House/paper-qa) is the closest analog. Their workspace declaration:

```toml
# corpus/pyproject.toml (root)
[tool.uv.workspace]
members = ["packages/*"]

[tool.uv.sources]
corpus-core = {workspace = true}
corpus-cli = {workspace = true}
corpus-mcp = {workspace = true}

[dependency-groups]
dev = [
    "corpus-core[dev]",
    "corpus-cli[dev]",
    "corpus-mcp[dev]",
]
```

This is verbatim PaperQA2's setup. It's tested, it works with `uv sync`, and it preserves editable installs across the workspace. **We adopt this without modification.**

---

## Concrete Repo Layout (Copy-Paste Template)

```
corpus/
├── pyproject.toml                              # uv workspace root
├── README.md
├── LICENSE                                     # Apache-2.0 (matches PaperQA2/DVC/cognee/mem0)
├── .git-scopes                                 # canonical commit scopes
├── packages/
│   ├── corpus-core/
│   │   ├── pyproject.toml                      # name="corpus-core"
│   │   ├── src/corpus_core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py                       # platformdirs + tomli resolution
│   │   │   ├── identity.py                     # source_id slugifier (doi_, pmid_, db_, ...)
│   │   │   ├── store.py                        # filesystem layout
│   │   │   ├── annotations.py                  # O_APPEND writer, validator
│   │   │   ├── schemas/                        # annotation.v1.json, claim.v1.json
│   │   │   ├── plugins.py                      # entry_points discovery
│   │   │   ├── factory.py                      # ExtractorFactory (mem0 pattern)
│   │   │   └── testing/                        # pytest fixtures + sample corpus
│   │   └── tests/
│   ├── corpus-cli/
│   │   ├── pyproject.toml                      # [project.scripts] corpus = "corpus_cli:main"
│   │   └── src/corpus_cli/
│   ├── corpus-mcp/
│   │   ├── pyproject.toml                      # [project.scripts] corpus-mcp = "corpus_mcp.server:main"
│   │   └── src/corpus_mcp/server.py            # fastmcp-based
│   ├── corpus-extractors/                      # optional: pypdf, docling adapters
│   │   ├── pyproject.toml
│   │   └── src/corpus_extractors/
│   └── corpus-plugin-claude/                   # Claude Code plugin bundle
│       ├── .claude-plugin/plugin.json
│       ├── .mcp.json                           # declares uvx corpus-mcp
│       ├── skills/corpus/SKILL.md
│       ├── hooks/hooks.json                    # pretool-corpus-remind, etc.
│       └── README.md
├── docs/
└── tests/                                      # integration tests across packages
```

Workspace root `pyproject.toml` (minimal):

```toml
[build-system]
requires = ["setuptools>=64", "setuptools_scm>=8"]
build-backend = "setuptools.build_meta"

[project]
name = "corpus"
dynamic = ["version"]
description = "Canonical scientific source store + MCP for AI agents"
requires-python = ">=3.11"
license = "Apache-2.0"
authors = [{name = "Markus", email = "markus@synthoria.bio"}]

[tool.uv.workspace]
members = ["packages/*"]

[tool.uv.sources]
corpus-core = {workspace = true}
corpus-cli = {workspace = true}
corpus-mcp = {workspace = true}
corpus-extractors = {workspace = true}

[dependency-groups]
dev = [
    "corpus-core[dev]",
    "corpus-cli[dev]",
    "corpus-mcp[dev]",
    "pytest>=8",
    "ruff",
    "mypy",
]
```

---

## Sources

- [PaperQA2 (Future-House/paper-qa) — uv workspace + packages/](https://github.com/Future-House/paper-qa) — closest analog; verbatim adoption candidate
- [DVC (iterative/dvc) — subpackage architecture](https://github.com/iterative/dvc) and [dvc-data subpackage](https://github.com/iterative/dvc-data) — production-grade multi-package monorepo
- [mem0 (mem0ai/mem0) — factory pattern + extras](https://github.com/mem0ai/mem0) — reject monolithic extras, copy factory
- [cognee (topoteretes/cognee) — cognee-mcp subdir](https://github.com/topoteretes/cognee/tree/main/cognee-mcp) — per-repo MCP-in-monorepo split
- [FastMCP (PrefectHQ/fastmcp) — MCP server framework](https://github.com/PrefectHQ/fastmcp) — adopted as base
- [Claude Code Plugins documentation](https://code.claude.com/docs/en/plugins) — `.claude-plugin/plugin.json` schema + `.mcp.json` bundling
- [Claude Code Plugin Marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) — distribution mechanism
- [uv workspace documentation](https://docs.astral.sh/uv/concepts/projects/workspaces/) — `tool.uv.workspace` + `tool.uv.sources`
- [platformdirs](https://platformdirs.readthedocs.io/en/latest/) — XDG-respecting cross-platform config locations
- [Python entry_points plugin discovery](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/) — standard since PEP 660; used by pytest/sphinx/jupyter
- [importlib.metadata — accessing package metadata](https://docs.python.org/3/library/importlib.metadata.html) — 2026 standard, supersedes pkg_resources
- [uvx MCP server pattern](https://devblogs.microsoft.com/azure-sdk/azure-mcp-server-better-python-support/) — Azure SDK confirmation of uvx as canonical Python MCP distribution
- [pluggy plugin manager](https://pluggy.readthedocs.io/en/stable/) — considered, not recommended (entry_points is enough at our scale)
- [Building a Python Monorepo with UV (Medium 2026)](https://medium.com/@naorcho/building-a-python-monorepo-with-uv-the-modern-way-to-manage-multi-package-projects-4cbcc56df1b4) — 2026 contemporary monorepo guide
- [research/scientific-substrate-target-architecture.md](file:///Users/alien/Projects/agent-infra/research/scientific-substrate-target-architecture.md) — corpus design context this memo packages

<!-- knowledge-index
generated: 2026-05-11T07:26:52Z
hash: c7a8163be937

title: Reusable Packaging for corpus_core + Scientific Substrate
status: research-memo
tags: packaging, uv-workspace, mcp, plugins, scientific-substrate, oss
cross_refs: research/scientific-substrate-target-architecture.md, research/scientific-substrate-target-architecture.md](file:///Users/alien/Projects/agent-infra/research/scientific-substrate-target-architecture.md

end-knowledge-index -->
