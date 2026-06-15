# /critique — what makes it slow and what makes its findings less reliable (2026-06-15)

Forensic read of `~/Projects/skills/critique/` (SKILL.md, references/, lenses/adversarial-review.md,
scripts/model-review.py) + agentlogs timing. Question C: does delegating fan-out to a local fast CLI
agent (cursor-agent / composer-2.5) fix each factor?

## Timing ground truth (agentlogs.db, n=611 `model-review.py` tool_calls)

Durations computed from `ts_start`/`ts_end` (no `duration_ms` column exists).

| Slice | n | median | p90 | max |
|---|---|---|---|---|
| Real runs (>30s) | 244 | **178s** | 243s | 1132s |
| — without `--verify` | 193 | (mean 178s) | | |
| — with `--verify` | 51 | (mean 143s) | | |
| Sub-5s (failures/`--help`/setup churn) | 358 | — | — | — |
| `llmx chat` calls (any) | 222 | mean 12.2s | | 376s |

Key reads:
- A normal `/critique model` dispatch costs **~3 min wall-clock** (median 178s), p90 ~4 min, with a
  ~19-min tail (1132s — almost certainly a `formal`/xhigh axis or a hung `--verify`, see Known Issue 2026-04-13).
- `--verify` does NOT dominate (143s < 178s) — the verify pass is parallelized via `ThreadPoolExecutor`
  (model-review.py:1546), so the old "serial verify hang" is the tail risk, not the median cost.
- **358 of 611 calls finished in <5s** — these are failures, `--help`, Python-version-mismatch bootstraps,
  and credential/`Credit balance too low` aborts (multiple Known Issues). The retry/setup churn around
  the script is itself a large fraction of invocations.

## A. SPEED — ranked by wall-clock cost

The axes themselves ARE already parallel (ThreadPoolExecutor, max_workers=n_axes, model-review.py:1143).
So the cost is dominated by the *slowest single axis* + the agent turns wrapped around the script.

| # | Slow factor | Evidence | ~Cost |
|---|---|---|---|
| 1 | **Slowest-axis API latency on a high-effort reasoning pass** (GPT-5.5 high/xhigh on `formal`). The parallel pool waits on the max, not the sum. xhigh "runs 30-45 min"; the 1132s tail is this. | SKILL Known Issue 2026-04-09/06-11; lens `formal`=GPT-5.5 high; global timeout 720s (model-review.py:1146) | 60-1100s |
| 2 | **Orchestrator packet-assembly turns** — the agent reads/greps/Writes `context.md` BEFORE the script runs (context-assembly.md: "Use Read/Grep to gather, then Write"). Pure agent-thread time, invisible to the script's own timer. | context-assembly.md; SKILL routing/triage (`review_gate.py triage`) | 30-180s |
| 3 | **Median dual-family round-trip** (2× Gemini-flash + 2× GPT-medium in parallel). The irreducible API latency floor. | agentlogs median 178s; `llmx` mean 12.2s/call but axes are the long ones | ~120-180s |
| 4 | **Retry/setup churn** — 358 sub-5s aborts: Python-version mismatch bootstrap, `Credit balance too low` (bare-mode auth), tail-truncation re-runs, `--sibling-roots` re-runs. Each forces a re-dispatch. | Known Issues 2026-04-11/04-25/06-03; 358/611 sub-5s | +1 full run each |
| 5 | **Verify-pass tail hang** — one stuck verification network call silences the whole process; no per-finding timeout helps. | Known Issue 2026-04-13 | up to global timeout |
| 6 | **Orchestrator synthesis + extract + verify-before-fold turns** — extraction is parallelized (1546) so cheap; the agent-side disposition/synthesis prose is the residual. | dispatch.md extraction defaults | 20-60s |
| 7 | **Escalating rounds** (standard→deep→full, or audit-plan's 8 parallel lanes + 2 critics). Multiplies #1-3 by axis count / lane count. | lens depth presets; Known Issue 2026-06-15 | ×2-×4 |

## B. RELIABILITY — ranked by frequency/severity

| # | Reliability factor | Evidence (quoted) | Severity |
|---|---|---|---|
| 1 | **Packet-only blindness — the 0-for-5 finding.** Packet reviewers critique the design but cannot falsify its *premises* (does the converted function have callers? does the cited join key exist?). | "3 packet-only axes … all 3 missed that the plan's Phase-3 conversion target had ZERO production dispatch sites … The Fable SUBAGENT axis (repo tools, grepped dispatch sites) found all three, verdict REJECT." Confirmed 2-for-2 same day (emb plan). Genomics audit-plan: packet-only 4-axis "missed or drowned in noise (76 findings)." | **Highest** — causes confident-but-wrong design approval |
| 2 | **Hallucinated anchors (model-asserted file/line/symbol).** 3 distinct inflation classes found, each ~38-56% raw "HALLUCINATED": `.js`/`.json` ext-swap, cross-repo siblings, code-symbols-as-files. | "18-finding review on genomics PRS plan, 10 flagged HALLUCINATED (56%); … semantic-hallucination rate was ~10%." Cross-repo: "50.8% hallucinated … 2 of the 3 real bugs were in the sibling repo, nearly buried." | High — but mostly MITIGATED in-verifier (ext-swap, `--sibling-roots`, symbol-grep). Residual: cross-repo needs manual flag, and the verifier can't catch a *plausible-but-wrong* anchor that resolves. |
| 3 | **Convergent over-engineering / wrong-scale.** Both families share a production-grade bias → converge on heavier fixes exactly where a constraint you hold makes them unnecessary; convergence reads as high-confidence because convergence is normally the trust signal. | "both models converged on an immutable release-manifest + latest.json symlink … a 2-line same-run check sufficed — adopting the convergent fix would have rebuilt the exact machinery the refactor was deleting." (phenome 2026-06-01) | High — silent; the trust signal itself is the trap |
| 4 | **Hand-applying model VALUE/IDENTIFIER corrections.** Models confidently "fix" tickers/symbols/numbers/dates from stale training data. | "review flagged STMPA.PA/TKMS.DE/RSGN.SW as broken tickers at conf 0.70-0.90 — ground-truth proved 3 of 4 still price fine; hand-applying the fixes would have BROKEN valid symbols." (intel 2026-06-01) | High where outputs are auto-applied |
| 5 | **Cosigner mis-calibration / wrong tier as cosigner.** `gemini-3-flash-preview` & GPT-5.3 ≈ 42% hallucination — "the cheap classification tier, never a cosigner. Distinct from gemini-3.5-flash, the clean primary cosigner." Easy to mis-route. | biases-and-antipatterns.md | Med — guarded by PROFILES but a silent footgun if overridden |
| 6 | **Correlated/shared-blind-spot convergence false-positives.** ~60% shared wrong answers when both err (Kim ICML 2025); scale-ambiguous context → "both models converge on the same wrong answer from shared misleading context." | biases table; anti-patterns "Scale-ambiguous context" | Med |
| 7 | **Composite-score-through-the-back-door / over-parameterization** — review blesses a plan that secretly re-blends N signals into one number. | anti-patterns over-parameterization entry | Med, domain-specific |
| 8 | **Uncalibrated confidence field** — conf 0.70-0.90 attached to findings that are 75% wrong (see #4). Confidence is model-asserted, not evidence-derived. | intel ticker case | Med — drives bad auto-disposition |

## C. THE REFRAME — does local fast CLI fan-out (cursor-agent / composer-2.5) fix each factor?

Premise: composer-2.5 ≈ ~20× throughput, gathers its OWN repo context locally, native parallel
read-only Task subagents, NOT an llmx/API round-trip. critique already has a `composer` axis hook
(model-review.py composer_review profile; dispatch.md "Add composer or claude as third lineage") and a
VOI Composer scout (dispatch.md). So this is a known lever, partially wired.

### Speed factors

| Slow factor | Local-CLI verdict | Why |
|---|---|---|
| 1 slowest-axis high-effort latency | **PARTIAL FIX** | Composer is fast locally, but you still need ≥1 *frontier* family for the formal/adversarial cross-check (martingale risk if all same-family). Composer replaces a SLOW axis only if you accept it as a lineage, not as the sole reasoner. The xhigh-formal tail stays if you keep GPT-5.5 high. |
| 2 packet-assembly turns | **FIXES** | Composer "gathers its own repo context locally" — eliminates the agent's Read/Grep/Write-context.md turns entirely. This is the cleanest win. |
| 3 median dual-family round-trip | **FIXES / shifts** | Local inference replaces the API floor for the axes you move onto Composer. Net win on axes delegated; frontier cosigner axis still pays API latency. |
| 4 retry/setup churn (358 sub-5s) | **PARTIAL FIX** | Removes llmx-bootstrap / bare-auth / Python-version classes for delegated axes. But adds a NEW transport (cursor-agent install/auth/sandbox — see cursor-agent skill) with its own failure surface. Net: fewer of the *known* aborts, new unknown ones. |
| 5 verify-pass hang | **NEUTRAL** | Verify is a separate step against code; running it under Composer's local Task subagents could even remove the network-hang failure mode (local file reads don't hang on a round-trip) — lean POSITIVE but unproven. |
| 6 synthesis/extract turns | **NEUTRAL** | Still an orchestrator-thread cost; unaffected by where axes run. |
| 7 escalating rounds | **FIXES the cost multiplier** | 20× throughput is exactly where lane/axis multiplication hurts; audit-plan's 8 parallel lanes are the target use case. Biggest leverage. |

### Reliability factors

| Reliability factor | Local-CLI verdict | Why |
|---|---|---|
| 1 packet-only blindness (0-for-5) | **FIXES — the headline win** | This is *literally* the documented fix: "dispatch at least one axis with repo access … the Fable SUBAGENT axis (repo tools, grepped dispatch sites) found all three." Composer navigates the repo natively and verifies premises (callers, join keys, dead targets). Local CLI = repo-access axis by construction. |
| 2 hallucinated anchors | **PARTIAL FIX** | Composer reading real files reduces invented paths/symbols at the SOURCE (it cites what it opened). BUT it can still misremember/paraphrase; the `--verify`-against-code pass stays mandatory. Does NOT remove the need to verify — reduces the rate, not the requirement. |
| 3 convergent over-engineering / wrong-scale | **WORSENS unless intent injected** | Composer is *still a production-pattern-biased model*; adding a same-bias reviewer can deepen false convergence. Repo access does NOT inject the *constraint you hold* (the refactor is DELETING that machinery). Needs explicit intent/constraint injection — same as before. Flag: throughput tempts running MORE same-bias axes → more spurious convergence. |
| 4 hand-applying value/identifier corrections | **NEUTRAL→PARTIAL** | Repo access lets Composer check identifiers that live IN the repo (symbol names, paths) — fixes those. But external values (tickers, API endpoints, live prices) are NOT in the repo; still need the actual API/DB ground-truth check. Composer doesn't fix the stale-training-data class. |
| 5 cosigner mis-calibration | **NEUTRAL / new risk** | Doesn't fix family-calibration; introduces a NEW family (Cursor's Composer) whose hallucination rate on critique work is **unmeasured here** — must be benchmarked before trusting as a cosigner, not assumed. (Uncertain — flag for measurement.) |
| 6 correlated/shared-blind-spot convergence | **NEUTRAL→WORSENS** | If Composer shares a base family or training lineage with an existing axis, correlation rises. Diversity, not throughput, is the cure. Use Composer as a DIFFERENT lineage, never as a second copy of an existing one. |
| 7 composite-score back-door | **NEUTRAL** | Semantic/intent judgment; repo access helps spot it (can read the scoring code) but the catch is conceptual, not navigational. Mild positive. |
| 8 uncalibrated confidence | **NEUTRAL** | Confidence stays model-asserted regardless of transport. Only evidence-derived (verify-pass) confidence fixes this. |

### Bottom line on C

- **Local fast CLI is a strong, evidence-backed fix for the TWO biggest problems: packet-only premise
  blindness (Reliability #1, the 0-for-5) and packet-assembly + escalation-multiplier latency (Speed #2,#7).**
  These are exactly where it's already being adopted (Fable-subagent axis, composer scout, audit-plan lanes).
- **It does NOT replace:** verify-against-code (anchors #2), external-value ground-truth checks (#4),
  intent/constraint injection against convergent over-engineering (#3,#6). Those are orthogonal to transport.
- **New risk it introduces:** an unmeasured cosigner family (#5) and the temptation to run MORE same-bias
  axes (cheap throughput) → *more* false convergence (#3,#6). Throughput must buy *diversity + repo-grounding*,
  not *volume of the same view*. Cross-family discipline (biases-and-antipatterns.md) still binds.

## Net recommendation (not asked to implement — research only)
Move the **repo-grounding / premise-falsification axis** to local CLI by default (it's already the
documented fix), keep ≥1 *frontier cross-family* axis on API for the adversarial/formal cross-check,
and keep the `--verify`-against-code pass mandatory regardless of transport. Measure Composer's
critique-hallucination rate before promoting it from "repo-grounding lane" to "cosigner."
