# Search MCP — Design Plan (v2, post-review)

Cross-model review: Gemini 3.1 Pro + GPT-5.2, 2026-02-28. Full review artifacts in `.model-review/2026-02-28/`.

## Problem

`emb` is a capable search library (BM25, dense, hybrid, rerank, freshness) but it's CLI-only. Agents can't use it without shelling out. Index discovery is manual. There's no cross-index search.

## Goal

An MCP server that makes `emb` indexes searchable from any agent session. Three tools, no CAG in v1.

## Non-Goals

- CAG/synthesis (deferred — research-mcp already has `ask_papers`; add when ≥2 weekly non-paper synthesis workflows exist)
- Replacing Exa (web search stays separate)
- Replacing research-mcp (paper discovery/download stays there)
- Query rewriting (agent's job, not the MCP's)

## Architecture

```
~/Projects/search-mcp/
├── pyproject.toml          # uv project, depends on emb + fastmcp only
├── src/search_mcp/
│   ├── __init__.py
│   ├── server.py           # FastMCP entry point + tool definitions
│   ├── router.py           # Query classification + strategy selection
│   └── engine.py           # SearchEngine pool, RRF fusion, thread safety
└── tests/
    ├── test_router.py
    └── test_engine.py
```

## Tools (3 tools)

### 1. `search`

```python
@mcp.tool()
def search(
    ctx: Context,
    query: str,
    indexes: str | None = None,     # comma-separated; None = all
    top_k: int = 10,
    strategy: str = "auto",         # auto | dense | bm25 | hybrid
    sources: str | None = None,     # comma-separated source filter
    freshness_weight: float = 0.0,  # 0-1
    rerank: bool = False,
) -> list[dict]:
    """Search local knowledge indexes.

    Returns ranked results with id, text snippet, source, score, and index name.
    Strategy 'auto' picks based on query characteristics and index metadata.
    Override with 'dense', 'bm25', or 'hybrid' if auto picks wrong.

    After reviewing results, use get_content to fetch full text of interesting entries.

    Args:
        query: Search query
        indexes: Comma-separated index names to search (default: all)
        top_k: Number of results to return
        strategy: auto, dense, bm25, or hybrid
        sources: Filter to specific sources (comma-separated)
        freshness_weight: 0-1, boost recent content
        rerank: Enable cross-encoder reranking (slower, more precise)
    """
```

**Multi-index search:** Queries each index's SearchEngine separately, then fuses rankings with RRF (k=60). Does NOT use `add_index()` — that invalidates the FTS cache and would destroy latency.

**Result schema:**
```python
{
    "id": str,
    "index": str,          # which index this came from
    "source": str | None,
    "title": str | None,
    "date": str | None,
    "text": str,           # truncated to 300 chars
    "score": float,        # RRF-fused rank score (comparable across indexes)
    "metadata": dict,
}
```

### 2. `get_content`

```python
@mcp.tool()
def get_content(
    ctx: Context,
    entry_ids: list[str],
    index: str | None = None,       # required if entry could be in multiple indexes
) -> list[dict]:
    """Get full text content for specific entries by ID.

    Use after search to read complete content of interesting results.
    Search results are truncated to 300 chars; this returns full text.

    Args:
        entry_ids: List of entry IDs from search results
        index: Index name (required if ambiguous)
    """
```

### 3. `indexes`

```python
@mcp.tool()
def indexes(ctx: Context) -> list[dict]:
    """List available search indexes with statistics.

    Returns index name, entry count, sources, embedding model, corpus token estimate,
    and last modified date. Use to discover what's searchable before calling search.
    """
```

Returns `corpus_tokens_estimate` per index (len(all_text) / 4) — enables the agent to decide if CAG via research-mcp would be more appropriate.

## Router Logic (`router.py`)

Corpus-aware heuristic, not an LLM call:

```python
def classify_query(query: str, index_hints: dict | None = None) -> str:
    """Classify query into strategy. Returns: bm25 | dense | hybrid

    Args:
        query: The search query
        index_hints: Optional {preferred_strategy, supports_rerank} from index metadata
    """
    # 1. Index hint takes precedence if set
    if index_hints and index_hints.get("preferred_strategy"):
        return index_hints["preferred_strategy"]

    # 2. Quoted phrases or known ID patterns → BM25
    if has_quoted_terms(query) or looks_like_id(query):
        return "bm25"

    # 3. Short queries (1-3 words) → hybrid (ambiguous intent)
    if len(query.split()) <= 3:
        return "hybrid"

    # 4. Default → dense (semantic similarity)
    return "dense"
```

**Why no CAG route:** CAG is deferred from v1. The routing decision framework from `search-retrieval-architecture.md` (corpus ≤200K → CAG) requires the agent to check `indexes()` output and decide to use research-mcp's `ask_papers` instead. That decision belongs to the agent, not inside the MCP.

**Known edge cases** (from GPT review):
- `compare "X" vs "Y"` — quoted terms trigger BM25 even though intent is comparative. Agent can override with `strategy=hybrid`.
- `"Why did contract W52P1J-… matter?"` — ID triggers BM25 though semantic might be better. Agent override.
- Heuristic is deliberately conservative. Wrong strategy = suboptimal ranking, not failure. Agent retries.

## Engine Pool (`engine.py`)

```python
class EnginePool:
    """Per-index SearchEngine instances with lazy loading, caching, thread safety."""

    def __init__(self, index_dirs: list[Path]):
        self.index_dirs = index_dirs
        self._engines: dict[str, SearchEngine] = {}
        self._mtimes: dict[str, float] = {}
        self._lock = asyncio.Lock()         # protects shared embedding model

    def get_engine(self, name: str) -> SearchEngine:
        """Get or create SearchEngine. Reload if file mtime changed."""

    def list_indexes(self) -> list[dict]:
        """Scan all index_dirs for .json files, return metadata + token estimates."""

    async def search_multi(self, query: str, index_names: list[str] | None,
                           top_k: int, **kwargs) -> list[dict]:
        """Search each index separately, fuse with RRF."""
        async with self._lock:
            per_index_results = []
            for name in (index_names or self._engines.keys()):
                engine = self.get_engine(name)
                results = engine.search(query, top_k=top_k * 2, **kwargs)
                per_index_results.append((name, results))
        return rrf_fuse(per_index_results, top_k=top_k)
```

**Thread safety:** `asyncio.Lock()` around search calls. The embedding model is not thread-safe (no locks in emb's `_encode_query()`). Since FastMCP handles requests async, we need the lock to prevent concurrent model access.

**Cache invalidation:** Check file mtime before returning cached engine. If file changed, create new SearchEngine (old one gets GC'd).

**RRF fusion:**
```python
def rrf_fuse(per_index_results: list[tuple[str, list[dict]]], top_k: int, k: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion across indexes. Score = sum(1/(k + rank_i))."""
```

## Server Entry Point

```python
def create_mcp(index_dirs: list[Path] | None = None) -> FastMCP:
    @asynccontextmanager
    async def lifespan(server):
        raw = os.environ.get("SEARCH_INDEX_DIR", "~/embeddings")
        dirs = [Path(d).expanduser() for d in raw.split(":")]
        pool = EnginePool(dirs)
        yield {"pool": pool}

    mcp = FastMCP(
        "search",
        instructions=(
            "Local knowledge search across embedded indexes.\n\n"
            "Workflow:\n"
            "1. indexes — discover available knowledge and corpus sizes\n"
            "2. search — find relevant entries (fast, ~50ms, ~$0)\n"
            "3. get_content — read full text of interesting results\n\n"
            "For synthesis/comparison across many documents, consider "
            "research-mcp ask_papers or manual review instead.\n"
        ),
        lifespan=lifespan,
    )
    return mcp
```

## .mcp.json Configuration

```json
{
    "search": {
        "command": "uv",
        "args": ["run", "--directory", "/Users/alien/Projects/search-mcp", "search-mcp"],
        "env": {
            "SEARCH_INDEX_DIR": "/Users/alien/embeddings:/Users/alien/Projects/selve/indexes"
        }
    }
}
```

No GEMINI_API_KEY needed — no CAG in v1.

## Dependencies

```toml
[project]
name = "search-mcp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.0",
    "emb",
]

[tool.uv.sources]
emb = { path = "../emb", editable = true }

[project.scripts]
search-mcp = "search_mcp.server:main"
```

## Query Logging

Every search call logs a line to `~/.local/share/search-mcp/queries.jsonl`:

```json
{"ts": "2026-02-28T15:30:00", "query": "...", "strategy": "hybrid", "indexes": ["selve"], "latency_ms": 52, "result_count": 10}
```

Enables offline eval later without building a full harness now.

## Testing Strategy

1. **Router tests:** Query → expected strategy classification. Include edge cases from GPT review.
2. **RRF tests:** Two mock index results → verify fused ranking is correct.
3. **Engine pool tests:** Mock indexes, test loading/caching/mtime invalidation.
4. **Thread safety test:** Concurrent search requests don't crash.
5. **Integration test:** Real small index (embed 10 entries), search, verify results.
6. **Manual test:** `uv run search-mcp` → use from Claude Code session.

## Implementation Order

1. `engine.py` — EnginePool with per-index SearchEngine, mtime invalidation, asyncio.Lock, RRF fusion
2. `server.py` — FastMCP with `search` + `indexes` tools
3. `get_content` tool
4. `router.py` — corpus-aware heuristic with `strategy=auto|dense|bm25|hybrid`
5. Query logging
6. Tests
7. Wire into `.mcp.json` for intel and selve projects

## Review Decisions Log

| Question | Decision | Source |
|----------|----------|--------|
| Merge across indexes? | Yes, RRF fusion (not score sort) | GPT: scores not comparable across indexes |
| Router per-index config? | Yes, `preferred_strategy` in metadata | Both models agreed |
| CAG in v1? | No — defer | Both: unproven use case, high complexity |
| Index directory? | Colon-separated `SEARCH_INDEX_DIR` | GPT: don't force migration |
| `add_index()` for merging? | No — per-index engines + RRF | Gemini: FTS cache invalidation |
| Thread safety? | asyncio.Lock per pool | Gemini: emb has no locking |
| Provenance in results? | `index` field in every result | Both: needed for traceability |
| `ask` tool? | Cut from v1 | Both: research-mcp covers papers; no concrete non-paper use case yet |

## Future (v2, when needed)

- `ask` tool with CAG for non-paper synthesis (gate: ≥2 weekly workflows)
- Gemini context caching for repeated corpus queries
- `diversity=True` option for counterevidence retrieval
- Index metadata: `source_grade` field for NATO Admiralty integration
