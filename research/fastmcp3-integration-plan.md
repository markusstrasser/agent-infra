---
title: FastMCP 3 Integration Plan — All MCP Repos
date: 2026-04-03
---

# FastMCP 3 Integration Plan — All MCP Repos

**Date:** 2026-04-03 (updated)
**Current FastMCP:** 3.2.0 (installed across all 6 active projects, 2026-04-03)
**Scope:** 6 MCP servers across 5 repos (repo-tools retired, knowledge-substrate retired)

---

## MCP Server Inventory

| # | Server | Repo | Tools | FastMCP | Status |
|---|--------|------|-------|---------|--------|
| 1 | `agent-infra` | meta/agent_infra_mcp.py | 1 | 3.2.0 | OK |
| 2 | `biomedical` | biomedical-mcp/ | ~81 | 3.2.0 | OK — Code Mode candidate |
| 3 | `research-mcp` | research-mcp/ | ~12 | 3.2.0 | OK |
| 4 | `selve-mcp` | selve/mcp/ | ~5 | 3.2.0 | OK |
| 5 | `tournament-mcp` | tournament-mcp/ | ~8 | 3.2.0 | OK |
| 6 | `genomics` | genomics/ | ~4 | 3.2.0 | OK |

**Retired:** `repo-tools` (2026-03-20, zero usage), `knowledge-substrate` (2026-03-24, 4 reads/60 writes).
**Total:** ~111 tools across 6 servers.

---

## FastMCP 3 Feature Assessment

### What's new in v3.0–3.2

| Feature | What it does | ROI for us |
|---------|-------------|------------|
| **`mount()` composition** | Mount sub-servers with namespace prefixes. Tools become `namespace_toolname`. Lifespan and middleware of child invoked by parent. | **HIGH** — biomedical-mcp has 41 tools; grouping by domain (genes, proteins, drugs, pathways) improves discoverability |
| **Provider architecture** | `FastMCPProvider`, `OpenAPIProvider`, `FileSystemProvider`, `ProxyProvider`. Plug different sources of tools. | **MEDIUM** — OpenAPIProvider could auto-wrap APIs without hand-coding |
| **`FastMCP.from_openapi()`** | Auto-generate MCP server from any OpenAPI spec + httpx client. Route filtering via `RouteMap`. | **HIGH** — many biomedical APIs have OpenAPI specs (Ensembl, Reactome, ChEMBL). Could replace hand-written modules. |
| **`create_proxy()`** | Mount external HTTP MCP servers or local Python scripts as sub-servers. | **MEDIUM** — could compose servers in `.mcp.json` with fewer entries |
| **Transforms** | `Namespace`, rename, filter, version tools dynamically at mount time. | **MEDIUM** — tool renaming/filtering without code changes |
| **Middleware** | Pluggable middleware chain: auth, logging, custom. Runs on every request. | **MEDIUM** — telemetry/logging middleware across all servers |
| **Auth (scope-based)** | `require_scopes()` on individual tools or server-wide. OAuth providers (GitHub, Google, etc). | **LOW** — all our servers are local stdio, no auth needed |
| **Transport separation** | `mcp.run(transport="http")` instead of constructor params. | **LOW** — cosmetic, already using stdio |
| **State isolation** | Mounted servers get isolated state stores. Explicit sharing via same `session_state_store`. | **LOW** — only matters if we use mount() |
| **FileSystemProvider** | Auto-discover `@tool`-decorated functions from a directory tree. | **LOW** — our servers are already well-organized |
| **Tasks protocol** | MCP Tasks support (long-running operations with progress). SEP-1686. | **LOW now** — not yet widely adopted by clients |
| **Concurrent sampling** | `context.sample()` for parallel LLM calls within tools. | **LOW** — we don't sample from within tools |
| **Code Mode** (3.1) | LLM searches tools via BM25 meta-tools instead of loading full catalog. Sandboxed `call_tool()` chaining. | **HIGH** — biomedical-mcp (81 tools) is the primary candidate. Reduces context bloat from tool schemas. |
| **Search Transforms** (3.1) | Standalone BM25 text search over tool names/descriptions. | **MEDIUM** — useful for dynamic tool catalogs, simpler than Code Mode |
| **MultiAuth** (3.1) | Compose multiple token verification sources. | **LOW** — all servers are local stdio |
| **Lazy imports** (3.1) | Heavy imports deferred to first use. | **FREE** — automatic startup improvement |
| **FastMCPApp** (3.2) | Tools return interactive UIs (charts, forms, dashboards). `@app.ui()` + `@app.tool()` separation. | **WATCH** — needs MCP Apps client support in Claude Code |
| **Built-in Providers** (3.2) | FileUpload, Approval, Choice, FormInput, GenerativeUI. | **WATCH** — Approval/Choice interesting for HITL gates, needs client support |
| **Security hardening** (3.2) | SSRF/path traversal, JWT algorithm restrictions, OAuth scope, CSRF. | **FREE** — already applied via version bump |

### What NOT to adopt

- **Auth/OAuth** — All servers are local stdio transport. Auth adds complexity with zero benefit.
- **HTTP transport** — We run everything via stdio through `.mcp.json`. HTTP transport is for remote/cloud deployment.
- **FastMCP Cloud / Docket** — We self-host everything. Cloud deployment not relevant.
- **Tasks protocol** — Not yet supported by Claude Code client. Monitor but don't build for it.

---

## Integration Plan

### Phase 0: Critical Fixes (do immediately)

#### 0a. Fix substrate import

`substrate/mcp_server.py` uses the deprecated `from mcp.server.fastmcp import FastMCP`. This import relies on the `mcp` package re-exporting FastMCP, which may break on any mcp package update.

```python
# BEFORE (line 20)
from mcp.server.fastmcp import FastMCP

# AFTER
from fastmcp import FastMCP
```

**Risk:** None. This is the official v3 import.
**Deps:** Ensure `fastmcp>=3.0` is in meta's `pyproject.toml` (it is: line `"fastmcp>=3.0"`).

#### 0b. Upgrade tournament-mcp to FastMCP 3

`tournament-mcp/pyproject.toml` has `"fastmcp>=2.0.0"`. Need to:
1. Bump to `"fastmcp>=3.0"`
2. Fix any breaking changes (likely just the import path)
3. Test that tools still register

**Breaking changes in v3:**
- Import: `from mcp.server.fastmcp import FastMCP` → `from fastmcp import FastMCP`
- Constructor: transport params (`host`, `port`) removed — moved to `run()` (we use stdio, not affected)
- State stores: isolated per server (only matters with `mount()`)

**Risk:** Low. Surface API (`@mcp.tool()`) is unchanged.

---

### Phase 1: Organize biomedical-mcp with `mount()` (high ROI)

**Problem:** 41 tools in a flat list. Agents see all 41 at once. Tool names give some grouping (`ot_*`, `chembl_*`, `string_*`) but it's not structured.

**Solution:** Split into domain sub-servers, mount with namespaces.

```python
from fastmcp import FastMCP

# Domain sub-servers
genetics = FastMCP("genetics")    # gene_info, gene_search, ensembl_*, kegg_gene_pathways
proteins = FastMCP("proteins")    # uniprot_*, alphafold_*, string_*
drugs = FastMCP("drugs")          # chembl_*, ot_drug_info, openfda_*
pathways = FastMCP("pathways")    # kegg_*, reactome_*
variants = FastMCP("variants")    # variant_*, ot_pharmacogenetics
clinical = FastMCP("clinical")    # ct_*, icd10_*, npi_*
targets = FastMCP("targets")      # ot_search, ot_target_info, ot_disease_*

# Main server composes all
main = FastMCP("biomedical")
main.mount(genetics, namespace="genetics")
main.mount(proteins, namespace="proteins")
main.mount(drugs, namespace="drugs")
main.mount(pathways, namespace="pathways")
main.mount(variants, namespace="variants")
main.mount(clinical, namespace="clinical")
main.mount(targets, namespace="targets")
```

**Tool naming impact:**
- `gene_info` → `genetics_gene_info`
- `uniprot_protein` → `proteins_uniprot_protein`
- `string_interactions` → `proteins_string_interactions`

**DECISION NEEDED:** Do we want namespace prefixes? Pros: better discoverability, logical grouping. Cons: longer tool names, breaks existing tool references in CLAUDE.md/skills. Could mount WITHOUT namespace to keep flat names but still get organizational benefits (separate lifespans, middleware per domain).

**Recommended:** Mount WITH namespaces. Update CLAUDE.md references. The agent already knows tool names from the MCP server's instructions field — namespaces make this more explicit.

**Shared lifespan pattern:** All sub-servers need the same `Cache` instance. FastMCP 3 isolates state stores by default. Solution: pass cache via a shared module-level variable or use `session_state_store` sharing:

```python
from key_value.aio.stores.memory import MemoryStore

store = MemoryStore()
genetics = FastMCP("genetics", session_state_store=store)
proteins = FastMCP("proteins", session_state_store=store)
# ... etc
main = FastMCP("biomedical", session_state_store=store)
```

Or simpler: keep the current lifespan pattern (single server, all tools in one file) but use `mount()` purely for organizational namespacing. The sub-servers don't need their own lifespans — they're just grouping containers.

**Implementation:**
1. Create `biomedical_mcp/domains/genetics.py`, `proteins.py`, etc. — each returns a `FastMCP` instance with its tools
2. `server.py` creates the main server and mounts all domains
3. Each domain receives shared clients (Cache, httpx) via the lifespan context
4. Update `instructions` field to reflect namespace grouping
5. Test all 41 tools still work
6. Update genomics CLAUDE.md tool references

**Maintenance:** Low (one-time migration). **Risk:** Medium (tool renaming may break MCP clients).

---

### Phase 2: `from_openapi()` for API-heavy servers (high ROI, deferred)

Many biomedical APIs publish OpenAPI specs:
- **Ensembl REST:** `https://rest.ensembl.org/documentation/info` (Swagger/OpenAPI)
- **Reactome Content Service:** `https://reactome.org/ContentService/` (Swagger)
- **ChEMBL API:** `https://www.ebi.ac.uk/chembl/api/utils/swagger` (OpenAPI 2.0)
- **Open Targets Platform:** GraphQL, not REST (skip)
- **ClinicalTrials.gov:** REST with OpenAPI spec
- **OpenFDA:** REST with documented endpoints (no formal OpenAPI)

**Pattern:**
```python
import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import RouteMap, MCPType

# Auto-generate Ensembl tools from OpenAPI spec
spec = httpx.get("https://rest.ensembl.org/?content-type=application/json").json()
ensembl_client = httpx.AsyncClient(
    base_url="https://rest.ensembl.org",
    headers={"Content-Type": "application/json"}
)

ensembl_server = FastMCP.from_openapi(
    openapi_spec=spec,
    client=ensembl_client,
    name="Ensembl",
    route_maps=[
        # Only include the endpoints we use
        RouteMap(pattern=r"^/lookup/", mcp_type=MCPType.TOOL),
        RouteMap(pattern=r"^/xrefs/", mcp_type=MCPType.TOOL),
        RouteMap(pattern=r"^/sequence/", mcp_type=MCPType.TOOL),
        # Exclude everything else
        RouteMap(pattern=r".*", mcp_type=MCPType.EXCLUDE),
    ]
)
```

**Tradeoffs vs hand-written modules:**

| | Hand-written (current) | from_openapi() |
|--|------------------------|----------------|
| **Control** | Full — custom response shaping, caching, error handling | Limited — raw API responses, no caching |
| **Maintenance** | Manual — must update when API changes | Auto — re-fetch spec to get new endpoints |
| **Tool quality** | High — curated descriptions, sensible defaults | Variable — depends on OpenAPI spec quality |
| **Setup** | Hours per API | Minutes per API |
| **Caching** | SQLite cache built in | None — would need middleware |

**Verdict:** `from_openapi()` is great for quickly adding NEW APIs we don't want to invest in. Not worth migrating our existing hand-written modules — they're better. Use it for:
- Quickly prototyping new API integrations
- APIs with excellent OpenAPI specs (Ensembl, Reactome)
- Mounting as "supplementary" tools alongside curated ones

**When to use:** Next time we want to add a new API (e.g., InterPro, Protein Atlas), try `from_openapi()` first. If the generated tools are good enough, ship them. If not, fall back to hand-written.

**Implementation:** Create `biomedical_mcp/openapi_providers.py` with a registry of OpenAPI specs and mount them as supplementary providers.

**Maintenance:** Low per API (auto-generated from spec, updates with spec). **Risk:** Low (additive).

---

### Phase 3: Middleware for telemetry (medium ROI)

**Problem:** We have no visibility into MCP tool usage across servers. Hook telemetry captures Claude Code tool calls, but not the internal MCP server behavior (cache hits, API latency, error rates).

**Solution:** FastMCP 3 middleware runs on every request:

```python
from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
import time
import logging

log = logging.getLogger("mcp.telemetry")

class TelemetryMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = context.request.params.name
        start = time.monotonic()
        try:
            result = await call_next(context)
            elapsed = time.monotonic() - start
            log.info("tool=%s elapsed=%.3fs status=ok", tool_name, elapsed)
            return result
        except Exception as e:
            elapsed = time.monotonic() - start
            log.info("tool=%s elapsed=%.3fs status=error error=%s", tool_name, elapsed, e)
            raise

mcp = FastMCP("biomedical", middleware=[TelemetryMiddleware()])
```

**Where to deploy:** All 7 servers. Could be a shared module in meta or a small package.

**Data destination:** stderr (captured in session transcripts) or a SQLite log (like hook telemetry).

**Maintenance:** Medium (shared middleware = shared dependency; changes propagate to all servers). **Composability:** High — standardized telemetry across all MCP servers.

---

### Phase 4: `create_proxy()` for server composition (medium ROI, deferred)

**Current state:** Each project's `.mcp.json` lists 5-10 servers individually. Some servers are duplicated across projects.

**FastMCP 3 pattern:** A "gateway" server that mounts other servers as proxies:

```python
from fastmcp import FastMCP
from fastmcp.server import create_proxy

gateway = FastMCP("bio-gateway")

# Mount local servers as sub-servers
gateway.mount(create_proxy("biomedical-mcp"), namespace="bio")
gateway.mount(create_proxy("./substrate/mcp_server.py --project genomics"), namespace="substrate")

# Mount remote HTTP MCP servers
gateway.mount(create_proxy("https://mcp.exa.ai/mcp?..."), namespace="exa")
```

**Benefit:** Reduce `.mcp.json` from 10 entries to 2-3 gateway servers. Single connection, less overhead.

**Risk:** Adds a proxy layer. If the gateway crashes, all mounted servers are unavailable. Also, namespacing changes all tool names (same issue as Phase 1).

**Verdict:** **Defer.** The benefit (fewer `.mcp.json` entries) doesn't justify the risk (single point of failure, tool renaming). Revisit if server count grows past 15 per project.

---

### Phase 5: Pin FastMCP version across all repos (maintenance)

Current state: All repos specify `fastmcp>=3.0` (open upper bound). This means a breaking change in 4.0 would break all servers.

**Action:** Pin to `fastmcp>=3.0,<4.0` in all `pyproject.toml` files.

Repos to update:
- `meta/pyproject.toml`
- `biomedical-mcp/pyproject.toml`
- `research-mcp/pyproject.toml`
- `selve/mcp/pyproject.toml`
- `tournament-mcp/pyproject.toml`

**Maintenance:** None (config change).

---

## Execution Order

| Phase | What | Maintenance | Risk | Status |
|-------|------|-------------|------|--------|
| **0a** | Fix substrate import | None | None | **DONE** (meta@c691819) |
| **0b** | Upgrade tournament-mcp | None | Low | **DONE** (tournament-mcp@6d0df1d) |
| **5** | Pin FastMCP versions | None (config) | None | **DONE** (all 5 repos) |
| **1** | Organize biomedical-mcp with mount() | Low | Medium (tool renaming) | **DONE** (biomedical-mcp@1f7489b) — 7 domains, namespace prefixes |
| **3** | Telemetry middleware | Medium (shared dep) | Low | **DONE** — all 6 servers (meta×3, biomedical, papers, selve) |
| **2** | from_openapi() for new APIs | Low per API (auto-gen) | Low | Event-driven — use when adding next API |
| **4** | Gateway proxy servers | Medium (proxy layer) | Medium | Deferred — maintenance overhead exceeds value at current scale |

**All actionable phases complete.** Phases 2 and 4 are event-driven (triggered by future needs).

---

## FastMCP 3 Patterns Cheat Sheet

For reference when writing new MCP servers or modifying existing ones.

### Server creation (v3 style)
```python
from fastmcp import FastMCP, Context

mcp = FastMCP("my-server", instructions="...")

@mcp.tool()
def my_tool(ctx: Context, query: str) -> dict:
    """Tool description."""
    return {"result": "..."}

# Transport is a run() concern, not constructor
mcp.run()  # defaults to stdio
mcp.run(transport="http", host="0.0.0.0", port=8080)
```

### Lifespan for shared state
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(server):
    db = connect_db()
    yield {"db": db}

mcp = FastMCP("server", lifespan=lifespan)

@mcp.tool()
def query(ctx: Context) -> dict:
    db = ctx.lifespan_context["db"]
    return db.query(...)
```

### Mount sub-servers
```python
main = FastMCP("main")
sub = FastMCP("sub")

@sub.tool()
def greet(name: str) -> str:
    return f"Hello {name}"

main.mount(sub, namespace="sub")  # tool: sub_greet
main.mount(sub)  # tool: greet (no namespace)
```

### OpenAPI auto-generation
```python
import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import RouteMap, MCPType

spec = httpx.get("https://api.example.com/openapi.json").json()
client = httpx.AsyncClient(base_url="https://api.example.com")

mcp = FastMCP.from_openapi(
    openapi_spec=spec, client=client, name="API",
    route_maps=[
        RouteMap(pattern=r"^/v1/", mcp_type=MCPType.TOOL),
        RouteMap(pattern=r".*", mcp_type=MCPType.EXCLUDE),
    ]
)
```

### Middleware
```python
from fastmcp.server.middleware import Middleware, MiddlewareContext

class LogMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        print(f"Calling {context.request.params.name}")
        return await call_next(context)

mcp = FastMCP("server", middleware=[LogMiddleware()])
```

### Transforms (rename/filter tools at mount time)
```python
from fastmcp.server.transforms import Namespace

server = FastMCP("Server")
mount = server.mount(other_server)
mount.add_transform(Namespace("api"))  # Tools become api_toolname
```

### FileSystemProvider (auto-discover tools from directory)
```python
from pathlib import Path
from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider

mcp = FastMCP("server", providers=[FileSystemProvider(Path("./tools/"))])
# Any file in ./tools/ with @tool decorated functions gets auto-registered
```

<!-- knowledge-index
generated: 2026-04-03T19:27:55Z
hash: a5066b83bde0

title: FastMCP 3 Integration Plan — All MCP Repos

end-knowledge-index -->
