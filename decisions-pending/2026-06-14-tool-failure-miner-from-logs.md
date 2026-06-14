# Build a deterministic "which tools are failing in real use" miner over agentlogs

**Boundary:** shared (conceptual home is `/observe`, a shared skill; the miner itself could live as an agent-infra script + doctor check, but it answers the cross-project "what's broken" question)

**Origin:** 2026-06-14, user: *"why don't you check the system? isn't that part of observe? don't you check the session logs and see which doesn't work?"* — after a full /improve health loop reported "all green / verified noop" six times while the `corpus` CLI was dead (editable pointer to a moved package). The failure signal was in `tool_calls.status='error'` for **days** (corpus errored ~11x across 06-06→06-10, multiple sessions). Nothing read it: observe's modes are `sessions` (Gemini behavioral quality) and `supervision` (wasted-supervision); neither queries tool failures. The 2026-04-16 `observe-technical-findings-mode` proposal is an *LLM* transcript pass — uncalibrated, never built.

**The catch — why the cheap version is a noise trap (4 probes, 2026-06-14):**
1. **Substring matching floods.** `args_json LIKE '%corpus %'` → 80 err / 521 ok, but mostly the corpus *directory path* (`cd ~/Projects/corpus`), not the CLI.
2. **By-design-nonzero tools.** `ruff` 233 err (lint findings = nonzero), `llmx` 79 err (rate-limit exit 3) — both healthy, both loud. `grep`/`test`/`||`-fallbacks too.
3. **Aggregate ratios miss bounded outages.** Invocation-scoped (command-start regex), corpus = 7 err / 57 ok over 2 weeks → looks "healthy" because the break was time-bounded and diluted by successes outside it.
4. **No "dead stretch" either.** corpus had successes *interleaved* on break days (some invocation paths still resolved), so "errored with zero same-day success" doesn't fire — and it false-flags ruff (one lint-only day).
   Root obstacle: `tool_calls` records `status`/`exit_code` but **not error text**, so "broken at launch" is indistinguishable from "ran, returned nonzero by design" without more.

**Recommendation:** Build the **error-text** version, deterministic, not LLM:
- Join errored `tool_calls` → their result `events` (via record_ref/correlation_id) and match a tight **launch-failure pattern bank**: `No module named`, `ModuleNotFoundError`, `command not found`, `ImportError`, `No such file or directory` on argv[0], entry-point/`console_scripts` errors. These ~never appear in by-design-nonzero output (ruff/grep/guards), so precision should be high.
- Scope to invocation (command-start regex), group by binary, surface a binary with ≥N launch-failures across ≥2 days. corpus would light up; ruff/llmx/grep would not.
- Report-only → `doctor.py` check + maintain SWEEP line. Calibrate FP on a labeled week before it can warn (measure-before-enforcing).

**Dissent / risk:**
- Scope creep vs the existing `observe-technical-findings-mode` proposal — but that's an LLM transcript pass for *architectural* issues; this is the cheap deterministic "is a tool broken" half. They're complementary; this one is buildable+verifiable without calibration drama.
- The `events`-join schema work is non-trivial (linkage, the 4 GB / 433k-event table). Bounded by the recent-window filter.
- Proactive coverage of the *specific* corpus class is **already shipped** (`doctor.check_uv_tool_editables`, 7956969) — this proposal is the *general reactive* miner, worth it only if you want the loop to catch *any* failing tool, not just moved-package editables.

**Open question for you:** build the deterministic error-text miner (above), or is the proactive editable-check enough for now and this stays parked until a second "loop missed a broken tool" incident?

**Reversible?** Yes — report-only script/check; delete if FP-noisy. No behavior change until wired to warn.

**Evidence:** 4 probes (this session, agentlogs `tool_calls`); corpus errors 06-06→10 in logs; shipped editable check 7956969; improvement-log [2026-06-14] coverage-gap entry; stale `~/.claude/steward-proposals/observe-technical-findings-mode.md`.
