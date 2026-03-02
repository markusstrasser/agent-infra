# Improvement Log

Findings from session analysis. Each tracks: observed → proposed → implemented → measured.
Source: `/session-analyst` skill analyzing transcripts from `~/.claude/projects/`.

## Findings
<!-- session analyst appends below -->

### [2026-02-28] TOKEN WASTE: Iterative regex parsing via repeated Bash one-liners
- **Session:** intel 16552a95
- **Evidence:** 9 reads of `setup_duckdb.py`, 6 separate `python3 -c "import re..."` Bash commands to iteratively test regex parsing of view names from Python source. Each attempt failed, requiring a new iteration with slightly modified regex.
- **Failure mode:** Token waste — iterative debugging via tool calls instead of writing a script
- **Proposed fix:** CLAUDE.md change: "When extracting structured data from Python source, use `ast` module or write a standalone script. Never iterate regex via inline Bash one-liners."
- **Status:** [x] implemented — global CLAUDE.md rule (2026-02-28)

### [2026-02-28] OVER-ENGINEERING: Regex parsing of Python source instead of AST
- **Session:** intel 16552a95
- **Evidence:** Agent used complex regexes with line-lookaheads and paren-counting to extract view names and directory paths from `setup_duckdb.py` f-strings. Repeatedly failed on edge cases. The `ast` module or simply importing the file's data structures would have been simpler and correct.
- **Failure mode:** Over-engineering — fragile approach when robust alternative exists
- **Proposed fix:** CLAUDE.md change: "Prefer `ast` module or direct import over regex when parsing Python source code."
- **Status:** [x] implemented — global CLAUDE.md rule (2026-02-28)

### [2026-02-28] TOKEN WASTE: Repeated find commands instead of saving to temp file
- **Session:** intel deb3fac6
- **Evidence:** 9 `find /Volumes/SSK1TB/corpus/` commands with minor variations (`wc -l`, `sed`, `stat`, `printf`) instead of saving the file list to `/tmp/` once and processing it. Each re-traverses 6,031 files.
- **Failure mode:** Token waste — filesystem re-traversal
- **Proposed fix:** rule: "Save `find`/`ls` output to `/tmp/` file when you need multiple passes over the same listing."
- **Status:** [x] implemented — global CLAUDE.md rule (2026-02-28)

### [2026-02-28] SYCOPHANCY: No pushback on "ALWAYS BE DOWNLOADING" bulk hoarding directive
- **Session:** intel f32653c6
- **Evidence:** User said "DO NOT STOP, ALWAYS BE DOWNLOADING." Agent immediately complied, spawning 105+ task dispatches and 123 inline Python download scripts across 13 context continuations. No discussion of: data quality, schema alignment, storage cost, API rate limits, or whether the downloaded datasets had integration plans. Session burned through context 13 times and hit usage limits 145 times.
- **Failure mode:** Sycophancy — compliance with directive that warranted pushback
- **Proposed fix:** rule: "Pushback required when download requests lack integration plan. Ask: What view will this create? What entity does it join to? If no answer, deprioritize."
- **Severity:** high
- **Status:** [x] implemented — intel CLAUDE.md "Download Discipline" section (2026-02-28). Instructions-only; acknowledged weakness per EoG.

### [2026-02-28] TOKEN WASTE: 123 inline Python scripts via Bash instead of writing .py files
- **Session:** intel f32653c6
- **Evidence:** 123 `Bash: uvx --with requests python3 -c "import requests, os..."` one-liners for individual downloads instead of writing download functions to a `.py` file. 496 total Bash calls in the session. Each inline script wastes tokens on boilerplate and is not reusable.
- **Failure mode:** Token waste — inline scripts where file-based scripts would save tokens and be maintainable
- **Proposed fix:** CLAUDE.md change: "Multi-line Python (>10 lines) must go in a .py file, not inline Bash. Exception: one-shot queries."
- **Severity:** high
- **Status:** [x] implemented — global CLAUDE.md rule (2026-02-28)

### [2026-02-28] TOKEN WASTE: Polling failed tasks after hitting usage limits
- **Session:** intel f32653c6
- **Evidence:** 145 "out of extra usage" messages. Agent continued attempting to read task outputs and retry failed downloads instead of halting and informing the user. Burned tokens on identical failure loops.
- **Failure mode:** NEW: Usage-limit spin loop — agent keeps polling when API limits are hit
- **Proposed fix:** hook: Detect repeated usage-limit errors and halt with user notification instead of retrying.
- **Severity:** high
- **Status:** [x] partially implemented — PostToolUse:Bash hook (`posttool-bash-failure-loop.sh`) detects 5+ consecutive Bash failures. Deployed to intel (2026-02-28). Does NOT catch API-level usage limits (system messages, not tool outputs).

### [2026-02-28] BUILD-THEN-UNDO: Download scripts rewritten for broken URLs
- **Session:** intel f32653c6
- **Evidence:** `download_new_alpha_datasets.py` written, run, URLs found broken (FERC, USITC, PatentsView, FL Sunbiz, NRC), script edited, re-run, more broken URLs found, edited again. Pattern repeated across multiple download scripts.
- **Failure mode:** Build-then-undo — URL validation should precede bulk download script writing
- **Proposed fix:** architectural: HEAD-request validation step before writing download scripts. Already partially addressed in `data_sources.md` lessons.
- **Severity:** medium
- **Status:** [x] implemented — intel CLAUDE.md "Download Discipline" rule: validate URLs with HEAD before bulk scripts (2026-02-28)

### [2026-02-28] SYCOPHANCY: Built heuristic auto-classification rules without epistemic challenge
- **Session:** selve a2679f18
- **Evidence:** After user asked "what can we do now that's better?", agent proposed and immediately implemented 3 heuristic rules to auto-demote variants as LIKELY_BENIGN (HLA region, alt contigs, tolerant + AM benign). Only after user pushback did agent articulate why these were epistemically unsound: "HLA gene -> LIKELY_BENIGN is a population-level prior, not evidence about the specific variant. HLA genes *do* cause disease." Agent had the knowledge to pushback before building but didn't.
- **Failure mode:** Sycophancy — compliance without epistemic challenge on safety-critical classification
- **Proposed fix:** [rule] "Distinguish mechanistic vs. heuristic changes before implementing. Mechanistic (parser fix, known-good data source) can proceed. Heuristic (new classification rule based on correlation/prior) requires stating the false-negative risk and requesting confirmation."
- **Severity:** high
- **Status:** [ ] rejected — one-off domain judgment, not a recurring pattern. General sycophancy pushback rule already covers this.

### [2026-02-28] BUILD-THEN-UNDO: Implemented and reverted heuristic auto-classification rules
- **Session:** selve a2679f18
- **Evidence:** Agent added `_is_alt_contig()`, `_is_tolerant_missense_benign()`, `_PRIMARY_CHROMS`, and modified `auto_classify()` to add 3 new LIKELY_BENIGN rules. After user pushback, all code was reverted and dead helpers cleaned up. The priority tiering function survived, but the filtering rules were wasted. Estimated ~4K output tokens on code that was deleted.
- **Failure mode:** Build-then-undo — direct consequence of missing pushback (above)
- **Proposed fix:** Same as above — epistemic challenge before building prevents the undo
- **Severity:** medium
- **Status:** [ ] rejected — linked to above

### [2026-02-28] TOKEN WASTE: 4 consecutive Read calls on same 700-line file
- **Session:** selve a2679f18
- **Evidence:** Lines 132-146 of transcript show 4 back-to-back `Read(generate_review_packets.py)` calls before a single Edit. The file was already in context from the first Read. Later in the session, similar patterns appear: Read -> Edit -> Read -> Edit on the same file when content was already available.
- **Failure mode:** Token waste — redundant file reads
- **Proposed fix:** [architectural] Before issuing Read, check if the file content is already in recent context. Use Grep for targeted lookups instead of full file reads when only checking a specific function or line.
- **Severity:** medium
- **Status:** [ ] deferred — a PreToolUse:Read hook would be too noisy (many legitimate re-reads). Claude Code already instructs agents to prefer Grep. Not worth the false-positive cost.

### [2026-02-28] RULE VIOLATION: Committed code without explicit user request
- **Session:** selve a2679f18
- **Evidence:** Agent committed at multiple points ("git add ... && git commit") without the user explicitly asking for commits. The user provided a plan and said "Implement the following plan" — the agent interpreted this as license to commit at each phase boundary. While the branch workflow in CLAUDE.md says "Git commit changes (semantic, granular)" when done, the global rule says "NEVER commit changes unless the user explicitly asks." The agent auto-committed 5+ times during implementation.
- **Failure mode:** Rule violation — auto-committing without explicit request
- **Proposed fix:** [rule clarification] The branch workflow instruction ("commit changes") and the global "never commit unless asked" are in tension. Resolve: branch workflow implicitly authorizes commits when user requests branch-based implementation.
- **Severity:** low (commits were well-structured and appropriate for branch workflow)
- **Status:** [x] implemented — clarified in global CLAUDE.md: branch workflow implicitly authorizes commits (2026-02-28)

### [2026-02-28] Supervision Audit
- **Period:** 1 day, 68 sessions, 348 user messages
- **Wasted:** 21.0% (target: <15%)
- **Top patterns:**
  1. **context-exhaustion (45):** User pasting "This session is being continued from a previous conversation that ran out of context" boilerplate. 33 in intel, 10 in selve, 3 in meta. The existing checkpoint.md + PreCompact hook generates the checkpoint, and CLAUDE.md tells the agent to read it, but the user still manually pastes continuation summaries. Root cause: no mechanism auto-injects checkpoint context at session start.
  2. **commit-boilerplate (12):** User pasting "IFF everything works: git commit..." block across 10 sessions. All rules already exist in global CLAUDE.md. Trust problem, not tooling problem — but a `/commit` command alias or explicit "when user says 'commit', follow CLAUDE.md commit rules" could reduce friction.
  3. **context-resume (4):** "Continue from where you left off" — overlaps with context-exhaustion.
  4. **rubber-stamp (6):** "ok", "do it", "go" — natural approvals, not clearly automatable without removing intentional oversight.
  5. **corrections (6 unique):** idempotency-check (2), completeness-verify (1), depth-nudge (1), env-uv-not-conda (1), capability-nudge (1) — below recurrence threshold, noise not signal.
- **Per-project:** intel 28.9%, selve 26.9%, meta 12.8%
- **Gemini synthesis:** Proposed SessionStart hook + commit skill. SessionStart hook is architecturally sound but SessionStart events can't inject prompt content (command-only). Commit skill is overkill given existing CLAUDE.md rules.
- **Fixes implemented:**
  1. [ARCHITECTURAL] UserPromptSubmit hook (`userprompt-context-warn.sh`) detects continuation boilerplate, warns user if checkpoint.md exists. Non-blocking. Deployed globally.
  2. [RULE] Strengthened CLAUDE.md Context Continuations instruction: agent infers task from git state, doesn't ask user for context.
  3. [RULE] Added "when user says 'commit', follow these rules" line to CLAUDE.md Git Commits section.
- **Status:** [x] implemented (2026-02-28)

### [2026-03-01] Supervision Audit
- **Period:** 1 day, 88 sessions, 355 user messages
- **Wasted:** 5.9% (target: <15%) -- down from 21.0% on 2026-02-28
- **Classifier fixes deployed this audit:**
  1. **context-continuation false positive.** Previous audit's 25 RE_ORIENT "context-exhaustion" messages were auto-continuation summaries injected by Claude Code, not human typing. Fixed: added SYSTEM classification for "session is being continued from a previous conversation". This alone dropped wasted% from 12.6% to 6.5%.
  2. **idempotency-check false positive.** "already exists as dormant code" in user-pasted context triggered `already (have|download|exist)` regex. Tightened to `we already (have|download)`. Dropped 2 more false positives.
- **Top remaining patterns (corrected):**
  1. **commit-boilerplate (7):** Same clipboard paste as 2026-02-28. Rule exists in CLAUDE.md. User habit, not agent failure. 6 sessions, identical text. No new fix needed -- the 2026-02-28 CLAUDE.md rule addition is the right fix; user adoption is the bottleneck.
  2. **rubber-stamp (7):** "ok", "do it", "go ahead" -- intentional approval checkpoints. Not automatable without removing oversight the user wants.
  3. **context-resume (3):** "Continue from where you left off" -- checkpoint.md mechanism exists but user still types this. The 2026-02-28 UserPromptSubmit hook should be catching this. Possible: hook not deployed to all projects.
  4. **corrections (4 unique):** completeness-verify (1), depth-nudge (1), env-uv-not-conda (1), capability-nudge (1). All singletons, noise not signal.
- **Trend:** Wasted supervision 21.0% -> 5.9% in 2 days. ~60% of the drop is classifier accuracy (false positives removed), ~40% is genuine improvement from 2026-02-28 fixes (commit rule, context continuation rule, UserPromptSubmit hook).
- **Gemini synthesis (cross-checked):**
  - Proposed commit-boilerplate DEFAULT fix -- rejected, rule already exists (CLAUDE.md git_rules section).
  - Proposed context-exhaustion ARCHITECTURAL fix -- moot, these were false positives in the classifier.
  - Proposed build-failure SKILL and tool-error HOOK -- both from one selve/genomics session (a2679f18), not recurring. Below threshold.
- **Fixes deployed:**
  1. [CLASSIFIER] `extract_supervision.py`: Added SYSTEM classification for auto-continuation messages
  2. [CLASSIFIER] `extract_supervision.py`: Tightened idempotency-check regex to avoid context-paste false positives
- **No new automation fixes warranted.** At 5.9% wasted, the remaining patterns are either (a) user habits that rules already address, (b) intentional approval checkpoints, or (c) singletons below recurrence threshold. Further investment in automation has diminishing returns until new patterns emerge.
- **Status:** [x] reviewed

### [2026-03-02] TOKEN WASTE: 21 reads of signal_scanner.py + 11 reads of setup_duckdb.py in single session
- **Session:** intel 0769f753
- **Evidence:** Session 0769f753 (553 messages, 35.9M input tokens, ~15h duration across context compactions) issued 21 `Read(signal_scanner.py)` and 11 `Read(setup_duckdb.py)` calls. These are ~2000+ line files. Most reads were partial (offset/limit), but many re-read sections already in context. Lines 117-174 of transcript show 11 Read calls before the first Edit — agent was reading the same file in overlapping windows instead of using Grep to find specific insertion points.
- **Failure mode:** Token waste — redundant file reads on large files
- **Proposed fix:** [rule] "For files >500 lines, use Grep to locate the insertion point first. Only Read the specific section (offset+limit) needed for the Edit. Never read the entire file multiple times."
- **Severity:** high (35.9M input tokens in one session; even 10% reduction = 3.6M saved)
- **Status:** [x] deployed — added to CLAUDE.md gotchas 2026-03-02

### [2026-03-02] TOKEN WASTE: Background task management overhead — 33 TaskOutput polls, 3 TaskStops
- **Session:** intel 0769f753, 3104aa73
- **Evidence:** Across sessions 0769f753 and 3104aa73, the agent issued 33 `TaskOutput` polling calls and 3 `TaskStop` calls. Many TaskOutput calls were for expired/compacted background tasks that returned empty. Pattern: agent launches scanner in background, loses track of task ID across context compactions, re-launches, polls the old ID, finds nothing, re-launches again. Lines 662-680: agent polls task `b00vpwcbc`, gets empty output, stops it, re-launches with tee, polls again, user interrupts asking how much longer.
- **Failure mode:** Token waste — background task thrashing across context compactions
- **Proposed fix:** [architectural] Long-running tasks (signal_scanner, setup_duckdb rebuild) should write output to a known path (e.g., `/tmp/scanner_output_latest.txt`) regardless of how they're launched. Agent checks the file, not the ephemeral task ID. Also: don't launch scanner in background if you need the output immediately.
- **Severity:** medium (~33 tool calls wasted, plus user friction from "any idea how much longer?")
- **Status:** [x] deployed — setup_duckdb.py and signal_scanner.py write to /tmp/intel_{rebuild,scanner}_latest.log

### [2026-03-02] RULE VIOLATION: Shell for-loop attempted despite known gotcha
- **Session:** intel 0769f753
- **Evidence:** Line 113: `Bash: for d in audit cisa epa_campd finra msha open_payments sec_efts treasury; do echo "=== $d ===" && ls ...` — agent attempted a shell for-loop despite CLAUDE.md explicitly stating "Shell for loops break in Bash tool. Use && chains or temp .sh file." and MEMORY.md listing this as a known gotcha. The agent then had to fix it on line 131 with an && chain. Wasted one tool call + user round-trip.
- **Failure mode:** Rule violation — ignoring documented gotcha
- **Proposed fix:** [hook] PreToolUse:Bash hook that greps for `for .* in .* do` patterns and warns. Lightweight regex, low false-positive risk.
- **Severity:** low (1 wasted call, known issue, self-corrected)
- **Status:** [x] deployed — PreToolUse:Bash hook in settings.json 2026-03-02

### [2026-03-02] TOKEN WASTE: DuckDB lock contention causing repeated rebuild attempts
- **Session:** intel 3104aa73
- **Evidence:** 10 lock-related messages across sessions 0769f753 and 3104aa73. In session 3104aa73 specifically: agent runs `setup_duckdb.py`, blocked by PID 52140 (signal_scanner). Then waits 20 min via Python polling loop. Then PID exits, but new PID 3123 appears (another scanner instance). Agent kills it, checks lsof, retries rebuild. Total: 5+ tool calls and ~20 min wall clock wasted on lock contention for what should be a single `setup_duckdb.py` run.
- **Failure mode:** Recurring infrastructure fragility — DuckDB single-writer lock blocks pipeline
- **Proposed fix:** [architectural] `setup_duckdb.py` and `signal_scanner.py` should use `flock` on a shared lockfile before opening the DB for write. If lock is held, fail fast with a clear message instead of cryptic DuckDB errors. Also: scanner should open `read_only=True` exclusively (currently sometimes opens read-write for materialized tables).
- **Severity:** high (20+ min blocked per occurrence, recurring across sessions)
- **Status:** [x] deployed — atexit-based lock release in setup_duckdb.py + signal_scanner.py, early release before schema cache regen

### [2026-03-02] MISSING PUSHBACK: "integrate everything that's left" accepted without scoping
- **Session:** intel 0769f753
- **Evidence:** User said "yeah integrate everything that's left to integrate." Agent immediately started mapping datasets and building enrichment views (lines 871-970). The agent did provide a useful assessment ("The graph should know everything that resolves to an entity. Most of what we just wired doesn't.") but only AFTER the user asked "Should the graph know everything?" — not proactively before starting work. The agent should have pushed back with: "Most remaining datasets don't resolve to entities. Building views for them adds queryability but zero graph value. Want me to prioritize the 3-4 that actually join to entity_id?"
- **Failure mode:** Missing pushback — compliance with vague scope before clarifying priorities
- **Proposed fix:** [rule] "When user gives a vague directive ('integrate everything', 'wire it all up'), enumerate what's in scope and its expected value BEFORE starting work. Don't build first and assess value after."
- **Severity:** medium (work was useful but not prioritized by ROI; ~9 enrichment views built, some with zero downstream consumers)
- **Status:** [ ] proposed — covered by global CLAUDE.md technical_pushback rules; not adding separate gotcha

### [2026-03-02] TOKEN WASTE: Gemini 503 retry cascade — 7+ failed calls across sessions
- **Session:** intel 331211bf
- **Evidence:** Session 331211bf attempted 6 `llm_check.py pattern` calls to Gemini 3.1 Pro, all returning 503 (overloaded). First attempt on line 1993 (`compare`), then three parallel `pattern` calls (lines 2130-2132) which all failed with `--max-tokens` (wrong flag) THEN 503, then three more without the flag (lines 2157-2168), all 503. Total: 6+ failed Gemini calls before switching to GPT-5.2. The agent knew from the first 503 that Gemini was down but continued retrying.
- **Failure mode:** Token waste — retrying a known-down service instead of failing over immediately
- **Proposed fix:** [rule] "After first Gemini 503, switch to GPT-5.2 for all remaining calls in the session. Don't retry Gemini until next session." [architectural] `llm_check.py` should cache 503 status and auto-failover for the session duration.
- **Severity:** medium (6 wasted background task launches + polling, plus user waited for results that never came)
- **Status:** [x] deployed — added to CLAUDE.md gotchas 2026-03-02

### [2026-03-02] SOURCE GRADING: Investment research output with minimal provenance tagging
- **Session:** intel 331211bf
- **Evidence:** The Monday trading brief (lines 1892-1907) and asset recommendations (lines 1940-1948) contain specific claims about insider buying amounts ($568K, $2.1M), FDA timelines, revenue figures, and P&L calculations. Source grading appears only 6 times across the full transcript, all reactive (after stop-research-gate hook blocked a commit, line 2107). The agent's initial Tier 1-2 research output (lines 1940-1948) contains claims like "CEO + CFO + Director all bought open-market on the same day (Feb 13)" without [A2] tags on the Form 4 source. The MRVL P&L figure (+$243, +3.1%) and HIMS (+$216, +6.9%) cite no source. The Iran geopolitical brief cites no sources at all.
- **Failure mode:** Rule violation — source grading is a core principle but only enforced reactively by hooks, not proactively by the agent
- **Proposed fix:** [rule reinforcement] "Every claim in investment research output — dollar amounts, dates, events, P&L — gets a source tag inline. Not after the hook catches it. If the claim came from an agent sub-task, the sub-task output must carry the tag."
- **Severity:** high (trade decisions being made on ungraded claims; constitutional violation of Principle 3)
- **Status:** [x] deployed — added to CLAUDE.md gotchas 2026-03-02

### [2026-03-02] Session b53878ae — No notable anti-patterns
- **Session:** intel b53878ae (17 messages, short session)
- **Evidence:** Agent checked for existing entity files, verified available data sources, identified gaps (no price data). Clean, efficient startup for a research planning session. No work product generated — session appears to have been cut short or was the start of a longer session.
- **Status:** clean

### [2026-03-02] Session 3a3a52cf — No notable anti-patterns
- **Session:** intel 3a3a52cf (37 messages, diagnostic session)
- **Evidence:** User asked about llmx Gemini errors. Agent efficiently diagnosed two issues (wrong model name alias, Gemini 503 outage), tested the fix, checked the skill file, and explained. Clean session with appropriate tool calls. Minor: 2 parallel Glob calls to find skill files could have been 1, but negligible.
- **Status:** clean

### [2026-03-02] BUILD-THEN-UNDO: Ruff linter fight over db.py import across 3 cycles
- **Session:** intel 92774402
- **Evidence:** Agent added `import duckdb` to `tools/lib/db.py`, ruff stripped it (pre-commit hook), agent re-added with `# noqa`, ruff stripped it again because `from __future__ import annotations` made ruff think it was type-only (TCH002). Agent tried 3 different fixes (re-add, add noqa, remove __future__) before settling on removing `from __future__ import annotations`. Lines 822-943 of transcript: Edit -> linter strips -> Read -> Edit -> linter strips -> Read -> Edit -> ruff check -> finally works. ~6 tool calls wasted.
- **Failure mode:** Build-then-undo -- should have diagnosed the root cause (future annotations + ruff TCH) on first failure instead of iterating
- **Proposed fix:** [rule] "When ruff strips an import, diagnose WHY (check ruff rule code) before re-adding. If `from __future__ import annotations` causes TCH002, add `# noqa: TCH002` or remove the future import. Don't iterate blindly."
- **Severity:** low (6 wasted tool calls, self-corrected within same session)
- **Status:** [x] deployed — added to CLAUDE.md gotchas 2026-03-02

### [2026-03-02] TOKEN WASTE: Retroactive predictions script rewritten after timeout -- batch vs per-query
- **Session:** intel 92774402
- **Evidence:** Agent wrote `retroactive_predictions.py` with per-ticker-per-date SQL queries (3600 queries for 20 dates x 60 tickers), launched it in background, waited, it timed out, killed it, then rewrote the core logic to batch-compute all signals in a few DuckDB window-function queries. The batch approach was always the right design -- individual Python-loop-over-SQL is a known anti-pattern for DuckDB (documented in MEMORY.md as "Python line-by-line CSV parsing kills performance at scale"). Lines 1143-1235 of transcript.
- **Failure mode:** Build-then-undo -- built the slow version first despite knowing the batch pattern
- **Proposed fix:** [rule] "For DuckDB analytics scripts, default to batch window-function queries. Per-row Python loops over SQL are the anti-pattern, not the starting point."
- **Severity:** medium (~20 min wall clock wasted on first version + rewrite)
- **Status:** [x] deployed — added to CLAUDE.md gotchas 2026-03-02

### [2026-03-02] OVER-ENGINEERING: `--no-multi-horizon` flag added to emit_predictions.py
- **Session:** intel 92774402
- **Evidence:** Agent added a `--no-multi-horizon` CLI flag to `emit_predictions.py` with 3 extra Read calls to find the right insertion point in the argparse section. No caller uses this flag. The script is called from `daily_update.sh` with no arguments. Adding a flag "in case someone wants to disable it" is speculative code. Lines 876-891.
- **Failure mode:** Over-engineering -- config for a feature with one caller and no variant use case
- **Proposed fix:** [rule] "Don't add CLI flags for features with one caller. If the behavior needs to change, edit the source."
- **Severity:** low (3 extra Read calls, minimal code added, but sets a precedent for unnecessary config surface)
- **Status:** [ ] proposed — covered by global CLAUDE.md anti-over-engineering rules

### [2026-03-02] MISSING PUSHBACK: Exa web searches for "most undervalued stocks" alongside systematic DuckDB screening
- **Session:** intel 92774402
- **Evidence:** While running systematic insider-buying and drawdown screens from DuckDB, the agent also fired 5 Exa web searches for "most undervalued small cap stocks 2026" and "deeply undervalued stocks 2026 turnaround catalysts." These generic web searches return consensus listicles -- the exact opposite of the project's principle that "consensus = zero information." The DuckDB screens (Form 4 clusters, 52W drawdown, congressional trades) are the edge; the Exa searches are noise. Lines 81, 111, 147, 175, 210.
- **Failure mode:** Missing pushback -- agent should recognize that generic "best stocks" web searches violate the constitutional principle. Web searches should be entity-specific (specific company research) not generic (listicle aggregation).
- **Proposed fix:** [rule] "Web searches in investment research must be entity-specific ('NKE turnaround analysis') not generic ('best undervalued stocks'). Generic screens come from our data, not consensus aggregators."
- **Severity:** medium (5 wasted Exa calls that could surface misleading consensus signals)
- **Status:** [x] deployed — added to CLAUDE.md gotchas 2026-03-02

### [2026-03-02] Session 6e80ec54 -- No anti-patterns (trivial session)
- **Session:** intel 6e80ec54 (4 messages, 18 output tokens)
- **Evidence:** User invoked /project-upgrade, agent correctly identified dirty working tree and refused to proceed. Clean, correct behavior.
- **Status:** clean

### [2026-03-02] Sessions 04c371c6 and 1e936eb7 -- Empty sessions
- **Session:** intel 04c371c6, 1e936eb7 (0 messages each)
- **Evidence:** No messages recorded. Likely aborted sessions.
- **Status:** clean

### [2026-03-02] Supervision Audit (end of day)
- **Period:** 7 days, 319 sessions, 1820 user messages (66 sessions / 263 messages today)
- **Wasted:** 5.3% 7-day (5.1% today intel-only). Target: <15%.
- **Trend:** 21.0% (Feb 28) -> 5.9% (Mar 1) -> 5.3% (Mar 2). Stable in target range.
- **Top patterns (7-day):**
  1. **commit-boilerplate (43):** Identical clipboard paste across 20+ sessions. CLAUDE.md git_rules section already covers this. User habit, not agent failure. No new fix warranted -- the rules exist, user will eventually stop pasting. This is the dominant source of remaining waste.
  2. **rubber-stamp (26):** "ok", "do it", "go ahead" -- intentional approval checkpoints. These are NOT automatable without removing oversight the user wants. Several are after the agent proposes a plan and waits for confirmation, which is correct behavior.
  3. **context-resume (9):** "Continue from where you left off." Checkpoint.md mechanism exists and works. UserPromptSubmit hook deployed 2026-02-28. Residual occurrences are likely habit or cases where checkpoint.md wasn't generated (short sessions, no compaction).
  4. **depth-nudge (9):** "go deeper", "dig deeper" -- borderline between correction and new agency. In most cases, the user is providing genuine new direction (wanting more thorough analysis). The classifier counts these as CORRECTION but ~6/9 are arguably NEW_AGENCY (user is redirecting effort, not correcting a mistake).
  5. **commit-no-coauthor (3):** Part of the same clipboard paste as commit-boilerplate. Already covered by CLAUDE.md rules.
- **Today specifically (intel, 1 day):**
  - 19 sessions, 79 user messages, 4 wasted (5.1%)
  - 2 context-resume, 1 depth-nudge, 1 rubber-stamp
  - Zero boilerplate -- the commit-boilerplate pattern did not appear today. Either the CLAUDE.md rules are being trusted, or no commit-heavy sessions occurred.
- **Classifier tuning:**
  - **depth-nudge false positive rate ~67%.** Of 9 "depth-nudge" classifications over 7 days, ~6 are genuinely new direction ("go deeper on THIS specific thing") not corrections. Consider reclassifying depth-nudge as NEW_AGENCY when the message includes specific scope (e.g., "go deeper on Iran analysis" vs bare "go deeper").
- **Proposed fix implementations (final status):**
  - `[x]` Grep-first rule for large files -- deployed to CLAUDE.md gotchas
  - `[x]` Background task write-to-known-path -- deployed (setup_duckdb.py + signal_scanner.py write /tmp/intel_*_latest.log)
  - `[x]` PreToolUse:Bash hook for shell for-loops -- deployed to settings.json
  - `[x]` DuckDB flock for write contention -- deployed (atexit lock release + early release before schema regen)
  - `[ ]` Vague directive scoping rule -- covered by global CLAUDE.md technical_pushback rules
  - `[x]` Gemini 503 failover rule -- deployed to CLAUDE.md gotchas
  - `[x]` Source grading proactive rule -- deployed to CLAUDE.md gotchas
  - `[x]` Entity-specific web search rule -- deployed to CLAUDE.md gotchas
  - `[x]` Batch-first DuckDB rule -- deployed to CLAUDE.md gotchas
  - `[x]` Ruff diagnosis rule -- deployed to CLAUDE.md gotchas
  - `[ ]` No speculative CLI flags rule -- covered by global CLAUDE.md anti-over-engineering rules
- **Gemini synthesis:** SKIPPED -- Gemini 2.5 Pro and Flash both timed out (3 attempts, >5 min each). Possible rate limit or regional outage. Synthesis performed directly from raw data.
- **Assessment:** At 5.3% wasted supervision, the system is well below the 15% target. The remaining waste is dominated by user habit (commit-boilerplate paste) and intentional oversight (rubber-stamps). Neither is worth automating further. The 11 proposed fixes from the session-analyst audit earlier today are the real improvement surface -- they address token waste and rule violations, not supervision waste. Priority order for implementation:
  1. **Grep-first rule** (HIGH impact, LOW effort -- just add to CLAUDE.md)
  2. **Source grading proactive rule** (HIGH impact, LOW effort -- constitutional compliance)
  3. **Entity-specific web search rule** (MEDIUM impact, LOW effort)
  4. **DuckDB flock** (HIGH impact, MEDIUM effort -- architectural)
  5. **Gemini 503 failover** (MEDIUM impact, MEDIUM effort)
- **Status:** [x] reviewed
