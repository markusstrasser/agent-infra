# CONTEXT: Cross-Model Review — Evo Infrastructure Patterns → Intel Transfer

## PROJECT CONSTITUTION (Intel)
Quantify alignment gaps. For each principle, assess: coverage (0-100%), consistency, testable violations.

> Maximize the rate at which the system corrects its own errors about the world, measured by market feedback.

Constitutional principles:
1. Autonomous Decision Test: "Does this make the next trade decision better-informed, faster, or more honest?"
2. Skeptical but Fair: Follow the data, consensus = zero information
3. Every Claim Sourced and Graded: NATO Admiralty [A1]-[F6], [DATA] for DuckDB
4. Quantify Before Narrating: Scope to dollars, base-rate every risk
5. Fast Feedback Over Slow Feedback: Markets grade fastest
6. The Join Is the Moat: Entity graph = compounding asset
7. Honest About Provenance: proven/inferred/speculative always labeled
8. Use Every Signal Domain: Board, insider, government, regulatory, complaints, etc.
9. Portfolio Is the Scorecard: Live portfolio view, integration test for intelligence engine
10. Compound, Don't Start Over: Git-versioned entity files, incremental priors
11. Falsify Before Recommending: Disprove thesis before trade recommendation
12. Size by Fractional Kelly: f=0.25 quarter Kelly

## META GOALS
- Maximize autonomous agent capability, measured by declining supervision
- Primary metric: ratio of autonomous-to-supervised work
- Wasted supervision currently ~21%, trending down

## WHAT'S BEING REVIEWED

An analysis proposing to transfer 10 infrastructure patterns from evo (a ClojureScript event-sourced UI kernel with ~20K LOC) to intel (a 525 GB adversarial investment research system with 152 Python scripts, 295 DuckDB views, 739K entities).

The proposals ranked by leverage:

### High Leverage
1. **Task runner** (bb.edn equivalent) — discoverable commands for 152 scripts
2. **Architecture analysis** — script/view dependency graphs, dead code detection, complexity hotspots
3. **Spec-as-database** — dataset schemas as executable specs with validation
4. **Failure modes as structured data** — consolidate scattered gotchas into queryable format

### Medium Leverage
5. **Multi-tier testing** — unit/integration/backtest tiers with speed expectations
6. **Event sourcing ledger** — append-only log of data changes (partially in progress)
7. **Dry-run simulation** — preview pipeline changes before committing

### Lower Leverage
8. Documentation landing page
9. Three-primitive kernel (constrained operations)
10. REPL-first development (iPython with DuckDB)

## KEY NUMBERS
- Intel: 152 .py files in tools/, 295 DuckDB views, 525 GB data, 739K entities, 24M graph edges
- Evo: 71 source files, 51 test files, 44 FRs in specs.edn, 40+ bb tasks
- Intel's backtest.py alone is 109K (larger than many entire projects)
- Intel's entity graph has no changelog — when entities update, old state is overwritten
- Intel has tests but no tier structure, no smoke test, no coverage auditing

## REVIEW QUESTIONS FOR GPT
1. Are the priorities correct? Which proposals would produce the most error correction per dollar of effort?
2. What's the ROI of each proposal given intel's scale (525 GB, 152 scripts)?
3. Are there logical inconsistencies in the analysis (e.g., recommending patterns that work at evo's scale but not intel's)?
4. Which proposals are YAGNI given intel's actual bottlenecks (data pipeline reliability, backtesting accuracy, entity resolution quality)?
5. What testable predictions can we make about each proposal's impact?
