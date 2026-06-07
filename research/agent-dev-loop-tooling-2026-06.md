# Agent Dev-Loop Tooling Survey — test / lint / debug / explore (2026-06-08)

**Consumer is an AI agent, not a human.** Humans do design + prompts; agents do all
testing, linting, debugging, and data-poking. Every tool is scored on **agent
feedback latency · parseable/greppable output · fewer agent turns · autonomy** —
NOT human DX. This single reframe kills most of the "obvious" picks (notebooks,
TUI debuggers, watch-mode) and changes what counts as a win.

Scope: genomics, phenome, intel (all uv + pytest + DuckDB/SQLite + ruff +
pyright-basic), with agent-infra owning the shared harness. Detail per axis in
`.scratch/tooling-research/0{1..5}-*.md`. Versions verified against PyPI/GitHub
via Exa on 2026-06-08 (Perplexity quota was exhausted, so a few dates are
single-sourced).

---

## The meta-finding

**The 100x is not a new tool or server — it's two conventions over primitives we
already have:**

1. **Parseable-everything.** Every gate — hook, test, lint, typecheck — should
   emit a machine-readable, greppable failure with a verbatim fix/override line.
   This is what turns a blocked agent into a one-turn self-correcting agent. It
   spans 4 of the 5 axes and is the highest-ROI item in the whole survey, at zero
   new dependencies.
2. **Tighten edit→verify, and make verify actually verify.** Impacted-test
   selection + fast typecheck shrink the loop; diff-scoped coverage+mutation
   closes the hole where a wrong patch passes weak tests (~1-in-5, SWE-ABS
   arXiv:2603.00520 / UTBoost).

Almost everything recommended below is a convention or a swap over already-installed
tools (ast-grep 0.43, ruff 0.12.8, duckdb 1.5.3 CLI, rich, pytest). New servers
lose: terminal/filesystem agents match-or-beat MCP-tool agents at ~5× lower cost
(arXiv:2604.00073, Mar 2026), consistent with our own ledger (repo-tools MCP:
0 uses / 4,287 runs).

---

## Tier 1 — ADOPT (low maintenance, clear agent ROI, ~zero new deps)

| # | Action | Why (agent ROI) | Blast radius |
|---|--------|-----------------|--------------|
| 1 | **Standardize the failure envelope** across ALL gates: `[<check>] ✗ BLOCKED — <reason>` + verbatim `fix:`/`override:` line | One-turn self-correction. Cross-cutting unifier (hooks already do this — propagate to tests + linters). Highest ROI in the survey. | shared (3+) → **propose** |
| 2 | **basedpyright** drop-in swap for pyright | `--outputjson` machine diagnostics; **baseline** system = incremental strict typing at ~0 migration cost. Lowest-maintenance path to real type rigor. | per-repo, reversible |
| 3 | **Agent pytest defaults**: `--tb=line -q -rN` + `--lf/--ff/--maxfail` + **pytest-reportlog** JSONL | Greppable failures, re-run only what broke. reportlog is pytest-dev official, tiny. | per-repo |
| 4 | **`COVERAGE_CORE=sysmon`** (PEP 669) on 3.12/3.13 | ~5% line-coverage overhead vs much higher; free. Unblocks coverage-gated work. | env var |
| 5 | **ast-grep for the ~26 pure-pattern linters** → shared YAML rules dir; also adopt ast-grep as the agent's structural multi-file **edit** primitive | ~4ms whole-`scripts/` scan vs ~25–40s for 80 serial `uv run` linter starts. Declarative rules an agent adds without writing+testing Python. Enforces our anti-regex constitutional rule. | meta + per-repo |
| 6 | **diff-scoped verification** — `just verify-diff` = coverage-of-the-diff + mutation on changed files only | Closes "patch passes weak tests but is semantically wrong" (~1-in-5). Native, ~0 maintenance. Turns "run the tests" into "prove the diff is exercised." | per-repo recipe |
| 7 | **rich tracebacks `show_locals=True` → file** | Post-mortem state dump the agent greps; no live debugger needed. rich already a dep. | per-repo |
| 8 | **`duckdb -readonly -markdown` / `-json`** as the agent SQL idiom (+ optional `just q`) | One safe, parseable Bash call for DB answers. | convention |
| 9 | **Fix stale pins**: syrupy 4.x → 5.1.0; bump ruff 0.12.8 → 0.15.x; uv 0.11.16 → 0.11.19 | Free correctness/feature; file-level ruff suppressions help agents. | per-repo |

## Tier 2 — TRIAL (scoped; validate before rollout)

| Item | What it buys | Gate / caveat |
|------|--------------|---------------|
| **pytest-testmon** (2.2.0, xdist-compatible) inner loop + **pytest-impacted** CI gate | The #1 agent prize: edit one file → minimal test set back, fast | MUST wrap with "migrations/.sql/data-fixture changed → full run" guard |
| **xdist `-n auto --dist worksteal`** | ~8–10× full-suite | Prerequisite: per-worker DuckDB/SQLite isolation (`worker_id`/`tmp_path_factory`) |
| **pyrefly** (Meta, GA 1.0, 2026-05-12, 1.85M LOC/s) | Fast whole-repo typecheck pre-check, good JSON output | As fast *pre-check*, not the correctness gate (basedpyright stays the gate) |
| **uv workspace** (one lockfile/venv across the 4 repos) | Kills stale-editable cross-repo `uv.sources` failures | Non-trivial: 4 separate git roots |
| **Claude Code native LSP tool** (`ENABLE_LSP_TOOL=1`, pyright/ty backend) | True cross-file refs/defs grep can't do | Fires only ~1.1% of calls today → needs prescriptive CLAUDE.md routing + measure; flag undocumented, manifests buggy (#15619/#17468) |
| **inspect_swe** (0.2.52, 2026-05) | Wraps Claude Code/Codex as sandboxed Inspect agents — reproducibly verify our OWN harness changes | We already run inspect-ai + Modal |
| **db-schema.md** generated by launchd (mirror `codebase-map-refresh`) | Kills multi-turn schema re-introspection | **Gate on consumption**: confirm in agentlogs that agents actually re-introspect schema across turns before building (our own anti-generation-without-consumption rule) |
| **structlog** (26.1.0) JSONL | Agent-greppable logs | ONLY on long-running/async/launchd workloads, not a blanket retrofit |
| **ast-grep as edit tool** | Precise structural rewrites vs regex | Composite rules need tree-sitter node-kind fluency (MEDIUM cost); pure bans are LOW |

## Tier 3 — SKIP (recorded to prevent re-derivation → vetoed-decisions candidates)

- **Rust test runners** (rtest/rpytest/rustest) — v0.0.x, no/partial fixtures, 1–2 devs.
- **Free-threaded / pytest-run-parallel as a speedup** — it's a thread-safety tool, not a speedup.
- **SlipCover** — neutralized by `COVERAGE_CORE=sysmon`.
- **Mutation testing as a gate or inner-loop** — hours-to-days; opposite of the goal. (Keep mutmut 3.5.0 manual, critical modules only. At our scale, coverage gaps > mutation score for ROI.)
- **ty (Astral)** as the correctness gate — beta, ~15% typing-spec conformance. Re-eval at 1.0 (best latency, 4.7ms).
- **ruff custom-rule hosting** — not supported (issue #283 open); does NOT subsume the custom linters.
- **tach** — unmaintained since ~2025-06; keep import-linter.
- **semgrep** — overkill vs ast-grep for our pattern set.
- **"migrate all 80 linters to ast-grep"** — only ~26 are pure-pattern; ~54 check git state / JSON registries / SHA pins / manifest↔code coverage, which ast-grep/semgrep structurally cannot express. Realistic collapse ~3:1 on the subset, ~1.5:1 overall — NOT "collapse to one."
- **Git-hook managers** (prek 0.4.4 / lefthook 2.1.9 / pre-commit / hk) — bash hooks already emit better agent-parseable output; parallel managers = multiple concurrent blockers = *harder* one-turn self-correction.
- **Watch-mode runners** (pytest-watcher/watchexec/entr/watchfiles) — human inner-loop concept; agents run tests explicitly.
- **mise** — subsumes just+versioning but doesn't improve the agent loop (uv owns python). `just` 1.51.0 stays.
- **nektos/act + cloud CI** — slow async feedback; local-hooks + launchd is the right agent CI.
- **All interactive notebooks/TUI/debuggers** — marimo, harlequin, DuckDB local UI, pudb, pdbr, ptpython, interactive IPython, debugpy. Human-only; an agent can't watch reactive cells or drive a TUI.
- **loguru** — 18mo stale + human-ergonomics niche; structlog wins for JSONL.
- **Serena LSP MCP** — symbolic edit overlaps native LSP tool + ast-grep; adds MCP surface across 5 repos; our 20–50-file repos don't have the grep-flood problem it solves.
- **difftastic for agent review** — control-byte/columnar output is exactly what our `--no-ext-diff` rule exists to avoid. Human-TTY differ only.
- **All code-intelligence + DB-introspection MCPs** — the "200 vs 50K token" pitch only holds for large codebases that flood grep; ours don't. Native `duckdb` CLI + grep win.

---

## Per-repo notes

- **genomics** — biggest beneficiary: 4,779 serial tests (testmon + xsteal), 80 linters (ast-grep the 26), already has hypothesis/syrupy/mutmut/import-linter. Has the per-worker-isolation work to do for xdist.
- **phenome** — 967 tests, 14 slow (full search index). reportlog + testmon + basedpyright. db-schema.md useful given DuckDB claim/todo stores.
- **intel** — 1,114 tests, Makefile (add a `--list`-equivalent), heavy DuckDB (~590 views) → `db-schema.md` + `duckdb -markdown` idiom is the strongest fit here.
- **agent-infra** — owns the shared failure-envelope convention, the ast-grep shared rules dir, and the `verify-diff` recipe pattern; launchd already has the `codebase-map-refresh` template to clone for `db-schema`.

## Cross-cutting sequence (if green-lit)

1. **Failure envelope spec** (meta) → one doc + a tiny helper, then propagate to tests/linters per repo. Biggest lever, but shared (3+) → needs sign-off.
2. **Per-repo, reversible, parallel**: basedpyright swap, agent pytest defaults + reportlog, sysmon, rich-traceback-to-file, stale-pin bumps. These are autonomous-tier.
3. **ast-grep**: stand up the shared YAML rules dir; migrate the 26 pure-pattern linters in genomics as the pilot.
4. **verify-diff** recipe — pilot in one repo, measure the wrong-patch catch rate.
5. **TRIALs** behind measurement: testmon (with the full-run guard), xdist (after isolation), LSP-tool routing.

---

*Inputs: 5 parallel research agents, 2026-06-08. Detail: `.scratch/tooling-research/`.
All Tier-3 SKIPs carry reasons specifically so they aren't re-proposed.*

---

## Revisions

### 2026-06-08 — cross-model review (Gemini 3.5 Flash + GPT-5.5)

Five corrections to *how* (no work item killed; the plan was right on *what*,
naive on *how*). Artifacts: `.model-review/2026-06-08-agent-dev-loop-tooling-e2d878/`.

1. **verify-diff is coverage-only in the inner loop.** Diff-scoped line coverage
   (<5s) is the inner gate; **mutation testing moves to pre-push / explicit deeper
   command** (convergent with the test-speed agent's "never inner-loop mutation").
   Tier-1 item #6 amended.
2. **ast-grep needs a runner, not just rules.** Migrating 26/80 leaves 54 serial
   `uv run` linters (~100-150ms startup each ≈ most of the 25-40s). The latency win
   requires a **consolidated lint runner** that calls ast-grep once for the 26 and
   runs the remaining 54 in **isolated processes** (not threads — shared temp/global
   state). ast-grep is necessary, not sufficient. Tier-1 #5 amended; this is the
   real latency lever.
3. **basedpyright is not a clean drop-in.** It turns on stricter defaults that would
   flood dynamic code (intel ~590 views). Ship a **locked config reproducing current
   pyright-basic noise level + pinned version + zero-noise baseline**, then opt into
   strict incrementally. Tier-1 #2 amended.
4. **Don't hide failures in JSONL.** Concise traceback on **stdout stays the primary
   agent channel** (`--tb=line`); pytest-reportlog is supplementary and
   consumption-gated (add only where an agent demonstrably needs structured parsing).
   Tier-1 #3 amended; reportlog demoted to opt-in.
5. **ast-grep rules need a validation gate** — agents hallucinate tree-sitter
   node-kinds. The pilot includes `ast-grep test` / schema validation before any rule
   goes live. Tier-1 #5 amended.

Partial-adopt: failure-envelope `fix:` lines reference **deterministic `just`
targets**, not free-form generated shell (the review's "command injection" framing
is overstated — it's advisory text an agent reads, not an auto-executor input — but
the design advice holds). Schema-cache (`db-schema.md`, Tier-2) stays gated: verify
in agentlogs that agents actually re-introspect schema across turns before building.

### 2026-06-08 — implementation (genomics pilot), measured ground truth

Three items landed + verified in genomics; measurement corrected two plan claims.

- **verify-diff** (item 4) — shipped (`scripts/verify_diff.py`, `just verify-diff`
  / `verify-diff-deep`). Line-coverage inner loop via diff-cover (maintained dep,
  not hand-rolled); RED/GREEN/tests-failed paths verified; sysmon confirmed
  warning-free on LINE coverage but **cannot do branch coverage before coverage
  3.14** (so `--branch` opts out of the fast core). Genomics' own contract suite
  (`SUBPROCESS_ALLOWED` ratchet) correctly caught the new `subprocess.run` — used
  the blessed allowlist, didn't route around it.

- **lint-runner** (item 3, runner half) — shipped (`scripts/lint_runner.py`,
  `just lint-all`). Auto-discovers the 31 no-arg lint recipes from the justfile,
  runs them as parallel `sys.executable` subprocesses (one uv resolution, not 31).
  **Measured: serial 69.7s → parallel 49.6s = only ~1.4x.** The plan over-credited
  parallelism. Ground truth: the lint phase is dominated by 2-3 **subprocess-storm
  outliers** — `lint_modal_import_smoke` 18.8s (nested `uv run python3 -c import`
  per script), `lint_modal` 9.4s — while the other 29 sum to ~41s serial and
  parallelize to ~6s (~7x). **The real next lever is fixing the outliers**
  (nested `uv run` → `sys.executable`), not more parallelism. Runner now prints
  the slowest-3 each run so the targets stay visible.

- **ast-grep** (item 3, structural half) — shipped (`sgconfig.yml`, `lint-rules/`,
  `lint-rule-tests/` snapshot gate, `just lint-sg` / `lint-sg-test`). Whole-repo
  scan **~0.8s**. First rule `no-stray-debugger` (global ban, no allowlist) verified
  catching an injected `breakpoint()`. **The 26-of-80 estimate is too high:** a
  ground-truth read of the "pure_ast" linters shows nearly all carry allowlists /
  directory scoping / relational logic (`lint_canonical_json_imports` enforces
  *which files MAY import a helper*) that ast-grep can't express — that logic is
  their value, so they stay Python. ast-grep grows one genuinely-global rule at a
  time; its bigger payoff is as the agent's structural search/replace tool.

Net: the verify-diff idea and the ast-grep-as-edit-tool held up; the "migrate the
linters to ast-grep for speed" framing did not — speed comes from the runner plus
killing the nested-`uv run` outliers, and ast-grep's lint role is narrow.
