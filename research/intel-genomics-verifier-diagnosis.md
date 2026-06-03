---
title: "Intel & Genomics: Verifier Diagnosis — Goal → Setpoint → System"
date: 2026-06-03
tags: [intel, genomics, verification, observability, reliability, setpoints]
status: active
---

# Intel & Genomics: Verifier Diagnosis

*Applies `research/closed-loop-boundary-and-system-awareness.md` to the two repos. Grounded
in fresh read-only infra inventories (2026-06-03). Decision: `decisions/2026-06-03-verifier-bound-autonomy.md`.*

## TL;DR — it's not a detection gap

Both repos already have serious verifier infrastructure. Intel: `freshness_policies.yaml`,
`dataset_registry.py` (+ ingestion ledger), a ~1,200-line `healthcheck.py` (200+ assertions,
incl. a resolve-loop liveness check and a `RESOLVE_HEARTBEAT`), 100+ pre-tool gates. Genomics:
`modal_utils.emit_step` heartbeats, `controller_reconcile` dead-letter repair, `canary_gate`
(70 sentinels + Wilson-CI stats), the mutation-gateway outbox, five `lint_no_direct_*` guards.

The failures happen **despite** this, in exactly the three shapes the closed-loop frame
predicts:

1. **Report, not gate / not consumed.** Detectors fire into stdout/logs/event-stores nobody
   reads. (Smoking gun below.)
2. **Correlated verifiers.** Same-lineage checks (canaries written by the same reasoning as
   the code) share the blind spot — green and wrong.
3. **Descriptive, not prescriptive, expected-state.** The registry/DAG records *what exists /
   what ran*, not *what must be true* — so a thing that silently stops or was never wired is
   invisible (absence-blindness).

So the answer to "better systems, or better goals?" is: **mostly the same move** — convert
each implicit goal into an explicit **setpoint** with a reality-touching differ whose alert is
actually **consumed or gated**. A few are pure goal (objective/reward) changes only you can
set. Each fix below is tagged `[SYSTEM]`, `[GOAL]`, or `[BOTH]`, and names the existing infra
it **extends** (not greenfield).

### The smoking gun (verify, don't trust)
Intel *has* a resolve-heartbeat check: `healthcheck.py` FAILs when `RESOLVE_HEARTBEAT` is
>35 days stale, run daily. The resolve loop was dead ~87 days. So that check was almost
certainly emitting a **daily FAIL for ~50 days** — as a non-blocking `run_important` step,
into a log nobody read. **The detector worked; the alert was never consumed.** *Verification
step before building:* `grep -c "RESOLVE_HEARTBEAT\|resolve.*stale\|resolve.*overdue"` the
intel healthcheck logs for Mar–May 2026. If present, this is confirmed and is the canonical
example for the whole diagnosis.

---

## Intel

Cluster A — **silent staleness** (thediff 19d, source_eval 87d, opensanctions 101d). Slipped
via *report-not-gate* + *descriptive-state* + the `run_soft` handler **swallowing** the crash.

Cluster B — **silent partial pulls** (thin form4 etc.). The ingestion ledger *can* detect
<95% of `api_reported_total`, but downloaders don't all populate it → 30%-row pulls exit 0.

Cluster C — **orphan tools / unwired features** (~770 uncalled `.py`; 5 built-not-wired). No
dead-code/integration check (though `hook_registry.py` already does this *for hooks*).

Cluster D — **aging human-blocked TODOs** (EDINET/WHO, 26d). Not an LLM failure; a queue with
no escalation.

| Cluster | Implicit goal → Setpoint | Fix | Extends |
|---|---|---|---|
| A | "sources stay fresh" → *each tracked source updated ≤ SLA; each scheduled job writes a success-beacon ≤ cadence* | `[BOTH]` Promote critical freshness checks from `run_important`→**gating** (a pre-tool beacon-age gate blocks Tier-1 decisions on stale data); route **one** consumed brief; stop `run_soft` swallowing — a failed job writes a *loud* failure-beacon | `healthcheck.py`, `freshness_policies.yaml`, `RESOLVE_HEARTBEAT` |
| B | "data is complete, not just present" → *each pull ≥ min_rows AND ≥95% of api_reported_total* | `[SYSTEM]` Contract/lint that every downloader populates `api_reported_total`; min-rows assertion in healthcheck | `dataset_registry.py` ingestion ledger |
| C | "code gets integrated or deleted" → *each tool referenced by recipe/cron/import within N days, else flagged* | `[BOTH]` Tool→caller dead-code lint (same shape as hook drift check); objective = "wired + produces signal," not "built" | `hook_registry.py` |
| D | "blocked work surfaces, doesn't rot" → *HUMAN_TODO age ≤ N days, else escalates* | `[SYSTEM]` TODO-aging watcher → consumed brief | `HUMAN_TODOS.md` |

**The prescriptive flip (root fix for A+C):** today the registry learns coverage *post-hoc*
from heartbeats. Add a **declared manifest** — "these N sources MUST refresh every X days;
these tools MUST have a caller" — so *absence becomes a violated invariant* instead of a thing
no one declared. This is the goal→setpoint conversion at the data layer.

---

## Genomics

Cluster E — **cpsr false dead_letter**. `emit_step` exists but `modal_cpsr.py` omits it;
`lint_modal_scripts` *mentions* `emit_step` but doesn't enforce it; `controller_reconcile`
nominates dead_letter on age+liveness **without** first checking the receipt/volume.

Cluster F — **clinical false-clear** (keystone). `canary_gate` (70 sentinels) is
*assertion-level* and *same-lineage*; it was green. The bug was an evidence-vs-assertion
count divergence. Caught only by **manual** `/critique close` (cross-lab). Already fixed in
code (`2014cfe2`); the gap is preventing the **class** from shipping silently again.

Cluster G — **silent corpus-attestation abandon**. `cron_stale_evidence` freezes the manifest
pointer on transport failure and emits no alert; `audit_corpus_sync` (in agent-infra) reports
abandoned counts daily but nothing **consumes** that report.

Cluster H — **deferred root-cause** (the cpsr heartbeat fix was diagnosed then shelved as
"non-blocking") and **zero-length logs**.

| Cluster | Implicit goal → Setpoint | Fix | Extends |
|---|---|---|---|
| E | "control plane matches reality" → *every long-warmup stage emits a heartbeat; no dead_letter without a receipt/volume check* | `[SYSTEM]` Wire `emit_step` into cpsr (trivial); make `lint_modal_scripts` **enforce** per-stage heartbeat; reconciler validates receipt/output **before** nominating dead_letter | `modal_utils.py`, `lint_modal_scripts.py`, `controller_reconcile.py` |
| F | "no clinical false-clear ships" → *n_positive(evidence) == n_positive(assertion) per panel; high-stakes output passes a decorrelated check* | `[SYSTEM]` **(1) evidence-vs-assertion count-delta as a deterministic gate** — would have caught this bug with *no model needed* (highest leverage, reality-anchored); (2) evidence-level canary for the domain-fold case; (3) auto cross-lab gate on the clinical render stage (gated on the decision's pre-registered eval — delta-check may suffice without a model) | `canary_gate.py`, `clinical_panel_projection.py`, `/critique` |
| G | "verdicts propagate" → *abandoned count == 0, else alert* | `[SYSTEM]` Route `audit_corpus_sync` abandoned-count to a consumed brief; auto-retry transient (rate-limit) vs. permanent (missing source) | `cron_stale_evidence.py`, `audit_corpus_sync.py` |
| H | "root fixed, not just symptom" → *every dead_letter post-mortem fixes root or files an owned ticket*; "logs are diagnostic" → *log non-empty after run* | `[GOAL]` objective change (below); `[SYSTEM]` log-nonempty assertion | — |

**Highest-leverage single fix (F-1):** make the two independent counts agree. The clinical
false-clear was *exactly* `n_positive(evidence) ≠ n_positive(assertion)`. A differential
consistency check (two derivations must match) is a **decorrelated verifier that needs no
second model** — it's reality-anchored, deterministic, and would have failed the panel
before render. This is the cheapest possible version of "decorrelation," and it generalizes:
wherever a number can be computed two independent ways, make their agreement a setpoint.

---

## The one goal-level change (only you can set)

Every `[GOAL]` tag and the deferred-fix pattern trace to one objective gap, named in the
research: the agent optimizes for **"appears done / tests green / wedge cleared"**, not for
**"true state visible / root fixed / decorrelated-verified."** RLHF rewards
completion-as-judged, not robustness-left-behind. Encode the corrected objective as a
session/stage-end setpoint the agent must satisfy:

- Did every long-running job leave a success-beacon (or a loud failure)?
- Is each diagnosed root cause fixed, or filed as an owned ticket — not silently deferred?
- Did high-stakes output pass a decorrelated/differential check before ship?
- Is every new tool wired to a caller and producing signal?

A self-score against this is itself a correlated verifier (see vetoed scored-quality-gate) —
so anchor it to **reality** (beacon files exist? receipt present? counts agree? caller grep
non-empty?), not to model judgment.

## Build order (prioritized; autonomy boundary noted)

**Tier 1 — cheap, deterministic, within-repo `[autonomous]`:**
1. Genomics E: wire `emit_step` into `modal_cpsr.py` + enforce in `lint_modal_scripts` + receipt-pre-check in reconciler.
2. Genomics F-1: evidence-vs-assertion count-delta gate in `clinical_panel_projection` render path.
3. Intel B: min-rows / `api_reported_total` assertion.
4. Intel A (gating half): pre-tool beacon-age gate; stop `run_soft` swallowing.

**Tier 2 — more design, mostly within-repo:**
5. Intel A/C prescriptive manifest + tool dead-code lint; route one consumed brief.
6. Genomics G: route abandoned-count + auto-retry.

**Tier 3 — `[propose-and-wait]` (shared infra, 3+ repos):**
7. The cross-lab decorrelated-review gate on high-stakes outputs (gated on the decision's
   pre-registered eval) and any **shared** setpoint/beacon framework spanning intel + genomics
   + phenome. Per constitution, building in one repo is autonomous; a shared framework is
   propose-and-wait.

**Caution:** ~5 intel agents are active. Intel changes should be done in a worktree or while
agents are quiet to avoid commit collisions; the genomics Tier-1 items are the safest start.

## See also
`research/closed-loop-boundary-and-system-awareness.md`,
`decisions/2026-06-03-verifier-bound-autonomy.md`,
`research/rsi-verification-bound.md`, `research/agentic-hygiene-plateau-reward-hacking.md`.
