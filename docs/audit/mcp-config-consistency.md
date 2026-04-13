# MCP Config Consistency Audit

Date: 2026-03-18

Scope:
- `/Users/alien/Projects/intel/.mcp.json`
- `/Users/alien/Projects/selve/.mcp.json`
- `/Users/alien/Projects/genomics/.mcp.json`
- `/Users/alien/Projects/meta/.mcp.json`
- `/Users/alien/Projects/skills/.mcp.json`
- `/Users/alien/Projects/meta/CLAUDE.md`

Note: `/Users/alien/Projects/skills/.mcp.json` does not exist.

## Expected Rollout From `CLAUDE.md`

- `repo-tools` is documented as "Configured in all projects' `.mcp.json`." Evidence: `/Users/alien/Projects/meta/CLAUDE.md:18`.
- `knowledge-substrate` is documented as configured in `intel`, `selve`, and `genomics`. Evidence: `/Users/alien/Projects/meta/CLAUDE.md:217`.
- `research` is documented as "Configured in `.mcp.json` per project." Evidence: `/Users/alien/Projects/meta/CLAUDE.md:280`.
- `agent-infra` is documented as an MCP server, but no per-project rollout claim is stated. Evidence: `/Users/alien/Projects/meta/CLAUDE.md:17`.

## Shared Server Comparison

| Server | Normalized command / args / env | intel | selve | genomics | meta | skills | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `repo-tools` | `uv run --directory /Users/alien/Projects/meta python3 scripts/repo_tools_mcp.py`; no `env` | yes | yes | yes | yes | no `.mcp.json` | `/Users/alien/Projects/intel/.mcp.json:94-102`, `/Users/alien/Projects/selve/.mcp.json:65-73`, `/Users/alien/Projects/genomics/.mcp.json:54-62`, `/Users/alien/Projects/meta/.mcp.json:55-63` |
| `agent-infra` | `uv run --directory /Users/alien/Projects/meta agent-infra-mcp`; no `env` | yes | yes | yes | yes | no `.mcp.json` | `/Users/alien/Projects/intel/.mcp.json:68-75`, `/Users/alien/Projects/selve/.mcp.json:39-46`, `/Users/alien/Projects/genomics/.mcp.json:28-35`, `/Users/alien/Projects/meta/.mcp.json:19-26` |
| `research` | `uv run --directory /Users/alien/Projects/research-mcp research-mcp`; `S2_API_KEY=${S2_API_KEY}` | yes | yes | yes | yes | no `.mcp.json` | `/Users/alien/Projects/intel/.mcp.json:56-66`, `/Users/alien/Projects/selve/.mcp.json:27-37`, `/Users/alien/Projects/genomics/.mcp.json:16-26`, `/Users/alien/Projects/meta/.mcp.json:7-17` |
| `knowledge-substrate` | `uv run --directory /Users/alien/Projects/meta python3 substrate/mcp_server.py --project <project>`; no `env` | `--project intel` | `--project selve` | `--project genomics` | absent | no `.mcp.json` | `/Users/alien/Projects/intel/.mcp.json:107-117`, `/Users/alien/Projects/selve/.mcp.json:75-85`, `/Users/alien/Projects/genomics/.mcp.json:64-74`, `/Users/alien/Projects/meta/CLAUDE.md:217` |
| `selve` | `uv run --directory /Users/alien/Projects/selve/mcp selve-mcp`; no `env` | yes | yes | yes | absent | no `.mcp.json` | `/Users/alien/Projects/intel/.mcp.json:23-30`, `/Users/alien/Projects/selve/.mcp.json:14-21`, `/Users/alien/Projects/genomics/.mcp.json:3-10` |
| `exa` | identical HTTP MCP URL in each present repo; no `env` | yes | yes | yes | yes | no `.mcp.json` | `/Users/alien/Projects/intel/.mcp.json:52-55`, `/Users/alien/Projects/selve/.mcp.json:23-26`, `/Users/alien/Projects/genomics/.mcp.json:12-15`, `/Users/alien/Projects/meta/.mcp.json:3-6` |
| `context7` | `npx -y @upstash/context7-mcp`; no `env` | yes | yes | yes | yes | no `.mcp.json` | `/Users/alien/Projects/intel/.mcp.json:77-82`, `/Users/alien/Projects/selve/.mcp.json:48-53`, `/Users/alien/Projects/genomics/.mcp.json:37-42`, `/Users/alien/Projects/meta/.mcp.json:28-33` |
| `brave-search` | `npx -y @modelcontextprotocol/server-brave-search`; `BRAVE_API_KEY=${BRAVE_API_KEY}` | yes | yes | yes | yes | no `.mcp.json` | `/Users/alien/Projects/intel/.mcp.json:84-92`, `/Users/alien/Projects/selve/.mcp.json:55-63`, `/Users/alien/Projects/genomics/.mcp.json:44-52`, `/Users/alien/Projects/meta/.mcp.json:45-53` |
| `firecrawl` | `npx -y firecrawl-mcp`; `FIRECRAWL_API_KEY` set in config | yes | absent | absent | yes | no `.mcp.json` | `/Users/alien/Projects/intel/.mcp.json:42-50`, `/Users/alien/Projects/meta/.mcp.json:35-43` |

Project-specific one-offs with no cross-project comparison target in this audit:
- `intel`: `duckdb`, `intelligence`, `fmp`, `nordic-registry`. Evidence: `/Users/alien/Projects/intel/.mcp.json:3-21`, `/Users/alien/Projects/intel/.mcp.json:32-40`, `/Users/alien/Projects/intel/.mcp.json:104-105`.
- `selve`: `bodyspec`, `google-dev-knowledge`. Evidence: `/Users/alien/Projects/selve/.mcp.json:3-12`.

## Findings

### MISSING

- `repo-tools` is missing from the `skills` project in the audited set. `CLAUDE.md` says `repo-tools` is configured in "all projects' `.mcp.json`," but `/Users/alien/Projects/skills/.mcp.json` does not exist. Evidence: `/Users/alien/Projects/meta/CLAUDE.md:18`, `/Users/alien/Projects/intel/.mcp.json:94-102`, `/Users/alien/Projects/selve/.mcp.json:65-73`, `/Users/alien/Projects/genomics/.mcp.json:54-62`, `/Users/alien/Projects/meta/.mcp.json:55-63`.
- `research` is missing from the `skills` project in the audited set. `CLAUDE.md` says the research MCP is configured in `.mcp.json` "per project," but `/Users/alien/Projects/skills/.mcp.json` does not exist. Evidence: `/Users/alien/Projects/meta/CLAUDE.md:280`, `/Users/alien/Projects/intel/.mcp.json:56-66`, `/Users/alien/Projects/selve/.mcp.json:27-37`, `/Users/alien/Projects/genomics/.mcp.json:16-26`, `/Users/alien/Projects/meta/.mcp.json:7-17`.

### DRIFT

- None. Across the audited repos that actually have `.mcp.json` files, the shared launch definitions for `repo-tools`, `agent-infra`, `research`, `selve`, `exa`, `context7`, `brave-search`, and `firecrawl` match exactly where they are shared. `knowledge-substrate` is the only server with argument variation, and the differing `--project` values match the documented deployment scope rather than representing drift. Evidence: `/Users/alien/Projects/intel/.mcp.json:68-75`, `/Users/alien/Projects/selve/.mcp.json:39-46`, `/Users/alien/Projects/genomics/.mcp.json:28-35`, `/Users/alien/Projects/meta/.mcp.json:19-26`, `/Users/alien/Projects/intel/.mcp.json:107-117`, `/Users/alien/Projects/selve/.mcp.json:75-85`, `/Users/alien/Projects/genomics/.mcp.json:64-74`, `/Users/alien/Projects/meta/CLAUDE.md:217`.

### STALE_DOC

- `/Users/alien/Projects/meta/CLAUDE.md:18` is stale for the audited set. The statement that `repo-tools` is configured in "all projects' `.mcp.json`" is false while `skills` has no `.mcp.json`.
- `/Users/alien/Projects/meta/CLAUDE.md:280` is stale for the audited set. The statement that the research MCP is configured in `.mcp.json` "per project" is false while `skills` has no `.mcp.json`.
