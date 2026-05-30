# Agent Error Patterns — agentlogs mining (2026-05-30)

Source: `~/.claude/agentlogs.db` (9.9 GB). Error signal = `tool_calls.status='error'`
(indexed). Error TEXT = `events.text` where `kind='error'` (join on `tool_call_id`).
LIVE = last 14 days (`ts_start >= '2026-05-16'`). Read-only; DB has live writers, so
time-bound every scan and expect intermittent `SQLITE_BUSY` under load.

**Totals:** 85,985 error tool-calls vs 394,471 success (~18% error rate across all vendors).

## What the data actually says

### Error mass by source (real)
| tool / source | errors | note |
|---|---|---|
| codex `exec_command` | 28,513 | codex-side shell; retry storms (Q7) |
| Read (builtin) | 21,276 / 1,886 live | mostly `File does not exist` — self-correcting |
| Bash (claude) | 16,105 / 2,903 live | python tracebacks + (historical) sed/nl paging |
| exa MCP | 4,298 (31.8% rate) | largest MCP error **volume** |
| Edit (builtin) | 1,979 / 823 live | string-not-match + read-before-edit |

### MCP error RATES (≥50 calls) — the real external error mass
scite **72.2%** · genomics **45.9%** (701) · fmp 39.2% · exa 31.8% (4298) ·
modal-triage 31.5% · brave 27.9% · perplexity 27.8% · research 24.5% · duckdb 22.6%.
Mostly external (rate limits, 403, 401/402 billing) — not agent mistakes. The
*agent-side* waste is retrying a flaky MCP instead of falling back.

### Top LIVE recurring error TEXT (count | live-14d)
- `File has not been read yet` — 1207 | **281** (Claude Edit/Write before Read)
- `String to replace not found` — 306 | **170** (Edit stale/non-unique old_string)
- `PreToolUse:Edit hook error` — 356 | **285** (see "Verified NOT a crash" below)
- `PreToolUse:Read hook error: tool-tracker.sh` — 867 | 75 (same — not a crash)
- Perplexity 401 Unauthorized — 327 | 84 (quota, live)
- duckdb execute_query fail — ~600 | ~145 (success:false/BigQuery/IO)
- `Sibling tool call errored` — 2720 | 0 — **artifact** of parallel-batch cancel, NOT real

### Project concentration (Q9)
codex/genomics 24,731 · claude/genomics 17,254 · claude/intel 8,023 · claude/meta 6,958.
Genomics is the #1 error-volume project on both vendors **and** has a 45.9% MCP error rate.

## Verified, NOT a crash (AI-text-policy check on subagent inference)
The subagent flagged the PreToolUse hook errors as "likely broken hooks." **Disproven by
direct test:** `tool-tracker.sh` and `pretool-ast-precommit.sh` both return EXIT=0 with
empty stderr on normal Read/Edit inputs (markdown + python). Most plausible cause of the
"hook error" signal is **timeout under concurrency** — this session began with 11 active
agents; hot-path PreToolUse hooks spawn `python3` per call (tool-tracker spawns it **2×**
on every Bash/Read/Edit/Write/Grep/Glob/Task/WebFetch/WebSearch), and cold-start
contention can exceed the hook timeout → logged as "hook error." Unproven but consistent
with: not reproducible solo, correlates with highest-frequency tools, concentrated in the
busiest projects (genomics/intel).

## Already covered — do NOT rebuild (verified by reading the hooks)
- `posttool-bash-failure-loop.sh` — 5 consecutive Bash fails → exit 2 with *targeted*
  diagnosis (missing-file/permission/syntax/network/import). This IS the circuit-breaker.
- `spinning-detector.sh` — blocks 8 identical calls; session-keyed (not racy); Bash
  same-tool ceiling deliberately disabled after calibration.
- `pretool-bash-loop-guard.sh` (multiline zsh) · `rate-limit-backoff.sh` (exit 3) ·
  `posttool-dup-read.sh` (fired on me this session) · `permission-denied-retry.sh`.

## Honest conclusion
The classic error-LOOP cases are already well-covered. Remaining live error mass is
either **external** (MCP/API failures — largely unavoidable) or **cheap self-correcting**
(builtin-tool ordering errors that block instantly and the agent fixes in one round-trip).
Neither screams "add a blocking hook." Per constitution (#1 architecture>instructions,
#3 measure-before-enforce, "don't over-hook"), the bar for a NEW hook is not clearly met.

## Build candidates (ranked by confidence; none are slam-dunks)
1. **Hot-path hook cost** — collapse tool-tracker.sh's 2× `python3` spawn into 1 (or jq).
   Cheap, autonomous (meta owns it), reduces per-call latency under concurrency. Worth
   doing regardless of whether it fully explains the "hook error" noise. *Lowest risk.*
2. **MCP fallback as architecture, not instruction** — routing rules ("scite 403→fallback",
   "exa quota", "S2 403→OpenAlex") are INSTRUCTIONS (≈0% reliable). A PreToolUse hook on
   the flaky MCP tools that, after an in-session failure of that server, injects the
   documented fallback on the next same-server call. Converts instruction→architecture.
   *Medium value; needs in-session failure-state tracking (the failure-loop hooks already
   show the pattern).*
3. **Read-before-edit pre-warn** — PreToolUse:Edit/Write hook keyed on the existing
   `/tmp/claude-read-tracker-$PPID`; warn (not block) when editing a file not read this
   session. ~281 live hits. *Borderline: the tool already self-corrects in one round-trip;
   risk of false warnings (subagents, prior-session reads).*
4. **genomics MCP 45.9% error rate** — surface to user. Cross-project (genomics repo) →
   propose, not autonomous.

## Out of jurisdiction (note only)
- codex `exec_command` retry storms (Q7: 12 runs >340 errors each) — codex harness, not
  Claude hooks. Codex has its own failure handling.
- `Sibling tool call errored` (2720) — Claude Code parallel-batch cancel artifact, not a
  real error class. Exclude from any triage.

## Reproduce (time-bound — full scans hit SQLITE_BUSY under live writers)
```sql
-- error mass by tool+vendor
SELECT tc.tool_name, s.vendor, COUNT(*) n FROM tool_calls tc
JOIN runs r ON tc.run_id=r.run_id JOIN sessions s ON r.session_pk=s.session_pk
WHERE tc.status='error' GROUP BY 1,2 ORDER BY n DESC LIMIT 25;
-- recurring error TEXT, with live split
SELECT substr(replace(e.text,char(10),' '),1,70) sig, COUNT(*) n,
       SUM(tc.ts_start>='2026-05-16') live
FROM events e JOIN tool_calls tc ON e.tool_call_id=tc.tool_call_id
WHERE tc.status='error' AND e.kind='error' GROUP BY sig ORDER BY n DESC LIMIT 40;
```
