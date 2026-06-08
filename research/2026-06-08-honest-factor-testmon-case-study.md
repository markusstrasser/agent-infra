# Case study: sizing a win honestly — testmon, blocking test time, and the per-run vs session-level gap

**One-line lesson:** a tooling win's *per-run* speedup factor is not its *session-level*
impact. You only learn the difference by measuring frequency × blocking × where the
time concentrates — and the gap is usually large enough to turn a poster number into
an overclaim. This is the `/leverage` discipline ("measure the real impact, report the
honest factor") applied to a `/leverage` win.

## The setup

`pytest-testmon` (impacted-test selection) was wired across genomics/intel/phenome so
an agent runs only the tests affected by its edit. Measured **per run** (phenome):
cold full suite 121s → warm-impacted **1.6–3.9s**, i.e. **31–77x**. A real edit ran
48 impacted / 119 deselected in 14.9s vs 121s. Headline-worthy — and exactly the kind
of number that gets quoted as if it were the whole story.

## The question that actually decides the value

> "How often was the suite even run — and was it blocking or background?"

A 31–77x per-run factor is worth ~nothing if agents rarely run the full suite, or run
it backgrounded (non-blocking → no agent wall-clock cost). Before believing the win,
size it.

## The measurement (agentlogs, all indexed history)

Test-suite Bash calls (`pytest` / `just test` / `make test`), duration from
`ts_end − ts_start`, blocking vs background from `args_json.run_in_background`:

```sql
-- frequency + blocking split + total blocking wait
WITH test_calls AS (
  SELECT COALESCE(json_extract(tc.args_json,'$.run_in_background'),0) AS bg,
         (julianday(tc.ts_end)-julianday(tc.ts_start))*86400.0 AS dur_s
  FROM tool_calls tc
  WHERE tc.tool_name='Bash'
    AND (json_extract(tc.args_json,'$.command') LIKE '%pytest%'
      OR json_extract(tc.args_json,'$.command') LIKE '%just test%'
      OR json_extract(tc.args_json,'$.command') LIKE '%make test%'))
SELECT COUNT(*), SUM(bg), COUNT(*)-SUM(bg),
       ROUND(SUM(CASE WHEN bg=0 THEN dur_s END)/60.0,1)
FROM test_calls WHERE dur_s>=0;
-- DB: ~/.claude/agentlogs.db
```

Results:

- **4,011** test-suite runs; **3,981 blocking (99.3%)**, 30 background. Agents almost
  always *wait*.
- Average **9.9s/run**; total blocking ≈ **11 hours**.

Duration distribution — where the wait actually lives:

| Run duration | # runs | % of runs | blocking wait |
|---|---|---|---|
| <5s | 3,106 | **77%** | 81 min |
| 5–30s | 642 | 16% | 132 min |
| 30–120s | 162 | 4% | 184 min |
| >120s | 101 | **2.5%** | **269 min** |

## The honest finding

1. **Blocking? Yes, almost always (99.3%).** For an autonomous agent, blocking test
   time is pure dead wall-clock — it can't proceed.
2. **But 77% of runs are already <5s.** Agents hand-scope (`pytest path::test`) most
   of the time. testmon does *nothing* for those (and adds slight cold-start cost).
3. **The wait is in the tail.** The 6.5% of runs over 30s account for **68%** of the
   ~11h; the >120s full-suite runs alone are 2.5% of runs but **40%** of all blocking
   wait.
4. **So testmon's session-level win ≠ 31–77x.** It is: *collapse the slow tail* (the
   ~263 full-ish runs that ate ~7.5 of the ~11 hours) to near-zero, **plus** a
   correctness gain — auto-selecting the exactly-impacted set beats hand-scoping,
   which silently omits impacted tests the agent didn't think to run. The 31–77x is a
   true per-run factor on the tail; it is not a per-session multiplier.
5. **Cumulative, not per-week.** The ~11h spans months of indexed history across all
   repos. The per-session drag is real but modest and front-loaded onto whoever hits
   the full suite.

## Why this is the case study

- **Per-run ≠ session-level.** The headline factor measures one event; the value
  measures `frequency × blocking-fraction × concentration`. Here they diverge hard:
  31–77x per full-suite run, but full-suite runs are 2.5% of all test runs. Quoting
  "31–77x faster testing" would have been an overclaim.
- **The win needed measurement as much as the problem did.** The founding category
  failure was that reactive loops never measured *blocking test time* (latency
  telemetry with no consumer). The fix to that blindness is the same act that sizes
  the fix honestly: go to the telemetry. Measurement is the throughline on both ends.
- **Generalizable rule for any "Nx" tooling claim:** before reporting it, pull the
  frequency and blocking distribution from agentlogs. If the fast path is rare, or
  the slow path is already hand-mitigated, the session-level factor is a fraction of
  the per-run factor — and often the real value is *correctness/auto-scope*, not raw
  seconds. State that, not the poster number.

## Caveats

- Durations are wall-clock as recorded (`ts_end − ts_start`), including any
  queue/IO; a few runs hit a ~600s timeout ceiling (the `max` 602s).
- The `LIKE '%pytest%'` filter may miss bespoke test wrappers and may include a few
  non-suite invocations; the distribution shape is robust to small mislabeling.
- "Blocking" = not `run_in_background`; an agent could in principle do other work
  while a foreground call runs, but in practice foreground = the turn waits.

## Coda: the biggest suite was the *worst* fit (the sharpest honest-factor lesson)

The three repos finished and inverted the obvious intuition ("biggest, slowest suite
= biggest testmon win"):

| Repo | Suite | testmon outcome |
|------|-------|-----------------|
| **phenome** | ~967 tests, ~121s | **works** — 31–77x warm; cold populate feasible |
| **intel** | ~1,114 tests | **works** — cold 50s → warm 0.85s (13 sel / 71 desel on an `llr.py` edit); also *repaired a month-broken suite* as a side effect |
| **genomics** | ~9,000 items, heavy Modal/DB fixtures, ~35min | **does NOT fit** — testmon's per-test coverage instrumentation is ~10x+ on heavy fixtures, so the one-time cold populate (must run the *whole* suite once to know the dependency map) pushes toward **hours** and stalled at 17%. A *partial* `.testmondata` is worse than none — it silently **under-selects** (only knows the tests it instrumented). |

The lesson: testmon's bootstrap cost **scales with suite heaviness**, so the suite
with the most to gain is exactly where the mechanism can't bootstrap. The per-repo
win is not a function of "how slow is the suite" — it's "is the cold populate
affordable." genomics' 35min suite is best attacked by a *different* lever (the
diff-scoped coverage gate already shipped, or scoped subsets agents already run),
not testmon. Wiring landed in genomics but is left **dormant + guarded** (the recipe
must not auto-cold-populate — that's the stall that just happened).

This is the honest-factor rule taken to its conclusion: not only is the per-run
factor not the session factor — the *win itself doesn't generalize across surfaces*,
and only measuring each one (not extrapolating from phenome's 31–77x) revealed it.

*Method: `/leverage` step 7 (pilot + MEASURE) and the "honest factor" rule. Source
data: `~/.claude/agentlogs.db` `tool_calls`; per-repo agent runs 2026-06-08.
Companion: `research/agent-dev-loop-tooling-2026-06.md`.*
