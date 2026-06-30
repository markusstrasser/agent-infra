---
id: 2026-06-30-cross-repo-loop-transfers
concept: cross-repo-rsi-loop-transfers
repo: agent-infra
decision_date: 2026-06-30
recorded_date: 2026-06-30
provenance: contemporaneous
status: accepted
initial_leaning: "port hutter's launchd autonomous-loop machinery into genomics to close its autonomy gap; symmetric steal-from-each-other matrix"
relations:
  - type: depends_on
    target: 2026-06-18-hutter-anim-rsi-comparative-report
  - type: relates_to
    target: 2026-06-09-shared-extraction-proven-common-test
---

# 2026-06-30: Cross-repo loop/tooling transfers — direction by verifier-gradient, form by lightest-enforcing

## Context

Asked what genomics, hutter, anim-workbench can learn from each other (tooling + loops).
Three Explore profiles + the prior comparative memo (`research/2026-06-18-…`, which covered
hutter/anim/intel but **not** genomics) established the landscape. The first framing —
"symmetric steal-from-each-other; port hutter's launchd portfolio into genomics" — was wrong
on two counts the operator corrected and probing confirmed.

## The real axis

Not *"which transfers"* but **the FORM and DIRECTION of each transfer**, because:

- The three repos sit on a **verifier-strength gradient**: hutter (clean — bit-exact bytes)
  → genomics (partial — evidence-graded attestation) → anim (weak — determinism/golden-match,
  no visual oracle). Each built exactly the discipline its regime *forces*.
- High-value transfers flow **against** the gradient (rigor from the strong-verifier repo into
  the weak one), not symmetrically.
- "Build shared infrastructure" is **already vetoed** (`2026-06-18` loop-core probe; the
  proven-common test, `2026-06-09`). So form ranges over: discipline-note → recipe → copy-port
  → enforced-gate → vendor-with-drift-test — never a package.

## Hard constraints (operator, 2026-06-30)

1. **CLI/`just`/hook over cron.** Standing daemons only where genuinely-unattended overnight
   progress is needed (hutter's search; anim's `$0`-idle-skip hourly outer-loop). Everything
   else is recipe/sessionstart-hook shaped. ([[genomics-telos-cli-not-cron]])
2. **genomics is export-only.** Winding down to *stable*; nothing scheduled or built *into* it.
   It exports its rigor; it imports nothing.
3. **No shared `loop-core` package** (standing veto). Copy patterns, copy ports.

## Alternatives considered

1. **Symmetric steal-matrix + port launchd into genomics** (initial leaning) — REJECTED.
   Probing: genomics already retired cron by design (`justfile:224` "Replaces the cron-daemon
   pattern; user-invoked") and wires watchers as `just` deps of mutating runs
   (`justfile:1848+`). Operator: genomics winding down, CLI-not-cron. The "autonomy gap" is
   intentional and aligned with its telos — porting autonomy in is anti-goal.
2. **Build a shared `loop-core` package the three import** — REJECTED (standing veto; the
   2026-06-18 deletion probe showed mechanics ≈ trivial wrapper; no ≥3 live loops share a
   ledger contract yet).
3. **Direction-by-gradient, form-by-lightest-enforcing** (chosen) — each transfer gets the
   minimum form that enforces its invariant; direction set by the inverse verifier-gradient;
   genomics export-only.

## Counterevidence sought

- *Does anim already have basis-drift / stale-verdict invalidation?* (would kill the headline
  transfer T1). Grep `mirror_stale|stale_basis|basis_attempt|verdict_status|superseded` over
  `anim-workbench/scripts src evolver` → only hit was a queue **task doc**, no implementation.
  **Gap confirmed.**
- *Does hutter already have the escalation pattern anim would "give" it?* `ls hutter/HUMAN.md
  hutter/decisions-pending hutter/proposals-pending` → **all present.** So "anim → hutter:
  HUMAN.md escalation" is NOT a transfer; it's already universal (it's a global rule). **Dropped.**
- *Does hutter need genomics' verdict_status?* hutter's accept-gate re-measures exact bytes
  every iteration — a stale verdict cannot launder into a finding (the gate re-runs). So the
  state machine is **low-value for hutter** (note-only), high-value for anim (whose self-authored
  goldens are never re-grounded). **Downgraded.**

## Decision

Three transfers survive grounding, each with its enforcing form:

| # | Transfer | Direction | Form | Why this form |
|---|----------|-----------|------|---------------|
| **T1** | **Verdict-grounding gate** — two holes, both closed: **(A) basis drift** (a verdict whose golden later changed is quarantined — the genomics `verdict_status` lesson, `attest_sample.py:65`) AND **(B) co-authored goldens** (code + the golden it's judged against changed in the *same* commit/session → the verdict is circular; `6/33 oracle-backed` is anim's *real* pain). | genomics → **anim** (pattern); independence rule is anim-native | **stamp** `basis_hash`/`basis_files`/`basis_commit` at the ledger write + **enforced gate**: new ACCEPT must carry a basis; ACCEPT invalid if hash drifted (A) OR if golden co-changed with code without manual attestation (B). | The drift port alone "preserves bad evidence more carefully" (cold-critique 2026-06-30) — anim's headline hole is *independence at verdict time* (B), not drift (A). The cheap field-set beats the full 5/6-state port (mirror/superseded machinery is genomics-mirror-specific, doesn't map). |
| **T2** | **Tier-aware calibration** — never kill a lever on a cheap-proxy null; read the per-tier *slope* (hutter: LSTM layers −329B@e6 → −6588B@e7, ~20×). `v_calibration_by_tag_tier`, `ledger_schema.sql:169`. | hutter → **anim** + **discipline everywhere** | **discipline-note (rule)** in both repos; **optional** SQLite-view-over-jsonl in anim (deferred — anim's no-SQL choice) | the *principle* is the transfer; it's a shared invariant ([[state-externalization-lens]] sibling) → one canonical rule, consumers load it. |
| **T3** | **Guardrail-as-`just`-dependency** — a watcher/check fires *on invocation of mutating work*, not on a clock (genomics `pipeline-run: … ensure-crash-loop-watch`, `justfile:1848`). The CLI-first pattern the operator prefers. | genomics → **hutter/anim** (where a daemon is really "do X before the next run") | **recipe pattern + doc** | encodes the operator's CLI-over-cron lean as a reusable shape, not new infra. |

**Dropped:** anim→hutter escalation (already present). **Note-only:** genomics→hutter
verdict_status (exact-replay already invalidates). **Into genomics: nothing** (export-only).

## Evidence

- All transfer sites probed live (commands + outputs in the plan's Phase-3 grounding section).
- Prior comparative memo `research/2026-06-18-hutter-anim-rsi-comparative-report.md`.
- Operator constraints captured 2026-06-30 (this session) → [[genomics-telos-cli-not-cron]].
- **Cross-model cold critique (gpt-5.5 high, 2026-06-30)** folded: rescoped T1 from "port the
  state machine" to "close drift (A) + co-authored-golden independence (B)"; B is anim's real
  hole (`6/33 oracle-backed`), which drift-tracking alone does not address. Dropped the full
  5/6-state port for a cheaper field-set + two rules. Direction (genomics→anim rigor) held; only
  the mechanism deepened — no spine reversal.

## Revisit if

- anim adopts a real generative-objective oracle (its designed-but-not-live escape hatch) —
  then T1's golden-hash gate composes with it rather than substituting for it.
- ≥3 live loops converge on one ledger contract — reopens the `loop-core` package veto.
- genomics telos changes (stops winding down) — reopens "nothing into genomics."

## Supersedes

Nothing. Extends `2026-06-18-hutter-anim-rsi-comparative-report` with the genomics axis.
