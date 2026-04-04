# llmx Transport Routing

| Model | Transport | Flag needed | Cost |
|-------|-----------|-------------|------|
| Gemini Flash/Lite | CLI (free) | none | $0 |
| Gemini Pro | CLI (free) | none (no `--stream`) | $0 |
| GPT-5.x | API (direct) | none | per-token |

- **Gemini Pro on CLI works** — hang bug fixed in gemini-cli 0.32.1 (current: v0.36.0). No `--stream` needed.
- **`--stream` forces API fallback** — only add if CLI hits rate limits.
- **`--max-tokens` forces API fallback** — CLI caps at 8K, no override. Brainstorm still uses API.
- **codex-cli re-enabled** — ~37K token overhead from 9 MCP servers (no disable flag). Viable for substantial tasks (audits, reviews). ChatGPT auth: only `gpt-5.4` and `gpt-5.3-codex` work; `o3`/`gpt-4.1` rejected. Don't use for trivial queries.
- **Exit 6 = billing exhausted** (permanent). Exit 3 = rate limit (transient). Don't retry exit 6.
- **Gemini 503/rate-limit = session-level fallback.** After first 503 from Gemini, switch to GPT or Flash for remaining calls in the session. Don't retry the same Gemini model — 4 confirmed incidents of 4-6 wasted retries before fallback.
- **S2 403 = session-level fallback.** After first 403 from Semantic Scholar, switch to scite or PubMed for remaining paper searches. S2 rate-limits aggressively; retrying wastes turns. 7+ confirmed incidents in Codex sessions (Apr 2026).
- **Exa recency enum:** Valid values are `24h`, `week`, `month`, `year`, `any` only. GPT-5.4 hallucinates `365d`/`90d`/`180d` — these fail with validation errors. Use `startPublishedDate`/`endPublishedDate` (ISO 8601) for precise date ranges.
- **llmx is editable-installed** (`uv tool install --editable`). Source changes in `~/Projects/llmx/` propagate instantly.
- **No `--fallback`** — model should be the model. Diagnose failures, don't mask with model downgrade.
