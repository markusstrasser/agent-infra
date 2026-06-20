[12:53] ## Verdict

**Revise** — high confidence, and the reasons are visible in the memo's own text, not dependent on files I can't read. The *direction* is right: pulse-as-control-plane is already accepted (2026-06-16 ADR), the conservative "don't flip apply yet" posture is mature, and SHADOW→PPV→promote is a genuinely mechanizable rule. But the memo contradicts itself in three load-bearing places — it claims "single ledger" while introducing four new stores, it claims to *reduce* conductors while adding `rsi_tick.py` as a parallel one, and it applies dry-run-parity discipline to the Phase 2 motor but not to the Phase 0 digest cutover it does first. Plus the loop is missing its negative half (no revert→demote path), which makes "earned autonomy" slower-motion Goodhart rather than safe autonomy. None of these are fatal; all are structural and cheap to fix before code. The weakest single link: **`rsi_tick.py` re-scatters the control layer the memo exists to unify.**

## Already handled (don't re-propose)

Flagging uncertainty up front: I can see the memo and its cross-references, **not** the actual repo/ADR files, so this is inferential from the memo's own citations plus the session context.

- **Pulse as control-plane API** — this is the *accepted decision* (`2026-06-16-rsi-unified-control-surface.md`), not a proposal. The memo should frame itself as **executing an accepted ADR**, not re-deciding it. Right now "pulse status + unified digest" reads like a fresh choice.
- **"Human questions VIEW" single-queue** — the `2026-06-16-agent-question-convergence` ADR already established *no 5th queue* and one question VIEW; the wakeup-cadence rule already defines `HUMAN.md` as a **feeder into that VIEW, not a new store**. The memo's `autonomy-exception log` likely duplicates this surface — reconcile, don't add.
- **gov.py report-only, harness-eval, reflect_capture, blindspot miner logic** — memo keeps these as-is; correct, these are shipped. No action, just don't dress "keep" up as work.
- **`/improve maintain` as interactive conductor** — kept; fine.

## Genuinely open gaps the memo misses

1. **The negative-feedback arc (biggest).** The memo has SHADOW→promote but no **promote→apply→revert→demote**. A tier-0 auto-apply that gets reverted in the 14d window is your single most valuable signal — a *confirmed false-positive promotion* — and nothing feeds it back to demote the producing pattern. Half the loop is missing. Without it, the apply lane re-promotes the same bad pattern next cycle.
2. **Global kill-switch.** Per-change gating exists; a single external marker-file circuit breaker that halts **all** applies instantly (independent of the tick process) does not. An autonomous apply lane without one is not shippable.
3. **The loop's own token/compute budget.** Per your own eval-token-cost rule: `sense→drain→synthesize→motor→surface` running on launchd with LLM calls has a per-tick cost that compounds. The memo never bounds it. An autonomous loop with no cost ceiling is a runaway vector — add per-tick `reason_tok`/`out_tok` logging and a budget gate.
4. **Tier-taxonomy ownership.** "tier-0 local" gates auto-apply, but who owns the tier boundaries? If the loop can adjust what counts as tier-0, the gate self-loosens. This is exactly a CLAUDE.md-#9 shared invariant: single-source it + drift-test it, externally owned, *not* loop-adjustable.
5. **Named consumer for the supervision direction vector.** "direction vector not scalar SLI" is the right instinct, but a richer number nobody reads is dead code with a plan attached (Pre-Build #3). What *acts* on the direction — the joint-alarm? a regime classifier? Name it or cut it.
6. **Prediction *generation* rate, not just resolution.** 5 registered / 0 resolved — the memo builds `pulse resolve` assuming resolution is the bottleneck. Maybe. But building a verifier for a near-empty stream is low-VOI. Cheap probe: manually resolve the 5 first, confirm they're auto-checkable. If they're semantic, the resolve-stub design changes entirely.
7. **Canary independence / freshness.** `pulse canary` must not read the same `last-tick.json` that `rsi_tick` writes — a hung tick that wrote a stale-but-OK file would pass its own health check (silent-proxy violation, CLAUDE.md #8). Needs an **external freshness clock** (timestamp-age check), not self-report.
8. **Concurrency safety under peer sessions.** This very session fired a peer-clobber warning. The unified ledger writes and digest-merge/lint must be race-safe when the autonomous loop runs concurrently with interactive sessions. Append-only JSONL is fine; the digest merge and frontmatter lint may not be.

## Goodhart / verifier risks

- **"≥95% tick success / 14d" is itself a Goodhart metric.** A tick that does nothing *succeeds*. This is precisely the "hook fire count alone" class the memo's own guard forbids — yet it's the gate for deleting 6 plists. Gate deletion on **work-done parity** (same candidates drained, same drafts produced), not process exit-0.
- **Anti-Goodhart guards are a prose list, not a mechanism.** "Do NOT optimize funnel capture count, [x] closure rate…" lives in a memo and will rot (CLAUDE.md: epistemics are architecture, not instructions). Which of these are *hookable*? "Alarm on supervision↓ AND error-visibility↓ jointly" — is there a detector computing both signals, or is it decorative? Specify the enforcement surface per guard or label it advisory.
- **The joint-alarm is necessary but not sufficient.** A tier-0 auto-apply that silently degrades can pass *both* keys: supervision unchanged (nobody's looking) AND error-visibility unchanged (the error is silent). Two keys that can both be false-negative together aren't a safe interlock. The revert→demote path (gap #1) is what actually backstops this.
- **PPV ≥60% is low for an apply lane** — 40% false-positive promotions. Fine as a *surfacing* threshold; for the earned-apply gate it must be stricter, and the memo doesn't separate the two thresholds. Also: at what firing rate do you hit ≥30 firings? If blindspot flags are rare, 30 firings is months — show the rate math or the gate is theoretical.
- **"consumed" ≠ "outcome-known."** The consumed-alert spine marks a detector signal as acted-on. But PPV needs the *outcome* (did the action turn out right), which arrives later. If you mark-consumed-and-forget, you destroy the data PPV needs. Signals have a 4-state lifecycle (fired→consumed→outcome-known→scored); track the last state, don't collapse it at "consumed."

## Phase ordering critique

The order is roughly right but **two known blockers are misfiled as "limbo" when they're prerequisites**, and Phase 0 violates the memo's own dry-run discipline.

- **Insert Phase -1 (prerequisites):** fix `agentlogs-index exit 1` and bulk-triage legacy `improvement-log` rows *before* step 2. The unified inbox and frontmatter lint build directly on a clean ledger and a working index. Building the lint on legacy rows forces a permanent grandfather carve-out; measuring rsi_tick "parity" (step 4) against a baseline that includes a broken index means **you validate that rsi_tick faithfully reproduces the bug.** These aren't "known blockers," they're step 0.
- **Split step 1.** Ship `pulse status` **additively, alongside the 4 digests**, prove parity over a few sessions, *then* delete them — move the deletion to a later step. As written, build+delete are bundled: if pulse status has a rendering bug, you've deleted all SessionStart situational awareness and the loop goes blind, the worst regression for an RSI system. The memo correctly insists on 7d dry-run parity for the Phase 2 motor — apply the identical discipline to the Phase 0 digest. The inconsistency is the tell.
- **Insert the negative-feedback path between step 5 and step 6.** revert→demote must exist before tier-0 apply, not after.
- Step 3 (`pulse resolve`) — precede with the manual-resolve-the-5 VOI probe.

Reordered: **(-1)** fix index + triage rows + freeze tier taxonomy → **(1)** pulse status additive + parity → **(2)** blindspot_convert + lint on clean ledger → **(3)** resolve-5 probe then pulse resolve → **(4)** delete digests post-parity → **(5)** rsi_tick dry-run against fixed baseline + external freshness canary → **(6)** regime/exception log + consumed spine + **revert→demote + kill-switch + per-tick cost** → **(7)** earned tier-0 apply.

## Breaking changes / blast radius

- **Phase 2 trades scatter for a SPOF.** Six independent plists with independent failure isolation → one `rsi_tick.py`. Before, one plist dying left five running; after, rsi_tick dying takes all six functions down — and per the joint-alarm, error-visibility dropping is *exactly* when you won't notice the loop went dark. Mitigation: external deadman + freshness canary (gap #7), and stage the consolidation function-by-function, not big-bang.
- **Double-act during the 14d parity window.** While rsi_tick runs alongside the 6 legacy plists, both drain the same ledger and (eventually) both could trigger drafts/applies → double-drain / double-draft on one inbox. State the transient launchd peak (12→13 jobs) explicitly and make the parity-mode tick **read-only / shadow-write to a separate egress** so it can't double-act on the live ledger.
- **"Single ledger" is oversold and that's a migration hazard.** The memo names `maintenance-actions.jsonl`, `maintain-candidates.json`, `session-regime.jsonl`, autonomy-exception log, `last-tick.json` — that's one ledger plus **four side-stores**, several of which brush against the repo's "no 5th queue" invariant. Either fold them into the ledger spine with a stated relation, or drop the "single ledger" claim. Proliferating JSONL stores while unifying digests is unifying the cheap surface and scattering the expensive one.

## Disagreements

- **rsi-tick vs pulse-only → I side hard with pulse.** The ADR already picked pulse as the control plane. The phased tick must be `pulse tick` (a module *inside* pulse), **not** a parallel `scripts/rsi_tick.py` with its own launchd. The memo's own diagnosis complains about "3 conductors" — adding a 4th standalone conductor to fix conductor-scatter is self-defeating. If rsi_tick is meant to be pulse's internal implementation, say so and don't expose a parallel script entry or a separate plist; let pulse own the schedule. This ambiguity is *the* load-bearing decision in the memo and it's left unresolved.
- **Earned apply timing → keep the Phase-3 conservatism, but the gate is incomplete, not the timing.** Don't ship it *sooner*; the 5-condition AND-gate is good. But "14d revert" is under-specified: no demote path, no kill-switch, no watcher. More conservative on *mechanism*, same timing.
- **Digest merge vs pulse status first → additive-first, explicitly.** Covered above; the memo bundles, I split. This is the cleanest, lowest-cost fix in the whole review.
- **Minor agreement worth stating:** "never auto-ship a composite RSI health score" is correct and is the #1 RSI Goodhart trap — keep that line load-bearing.

## Top 3 revisions

1. **Make the phased tick `pulse tick`, not `scripts/rsi_tick.py`** — internally a module is fine, but no parallel script entry and no separate launchd. Then *prove* the unification: enumerate post-change conductor count (target: pulse = the one motor, `/improve maintain` = the one interactive conductor; delete `/observe` and maintain-tick). A memo about reducing scatter must show the scatter went down.

2. **Convert every build+delete into additive→parity→cutover, and promote the two parked blockers to Phase -1.** Ship `pulse status` beside the 4 digests, prove parity, then delete (apply the Phase-2 dry-run discipline to Phase 0). Fix `agentlogs-index exit 1` and bulk-triage legacy `improvement-log` rows *before* the lint and parity steps depend on them — they're prerequisites, not "known blockers."

3. **Add the negative half of the loop to Phase 3 before flipping apply:** revert events auto-demote the producing pattern (close SHADOW→promote→**revert→demote**); a single external marker-file kill-switch halts all applies; per-tick token cost is logged and budget-gated; the tier taxonomy is single-sourced + drift-tested and loop-immutable. Also drop the "single ledger" claim or fold the four side-stores into the spine. Earned autonomy without the negative-feedback arc and a kill-switch is just Goodhart in slow motion.

---

One caveat on provenance: the memo is a 4×composer-2.5 synthesis, so treat its file-state claims ("pulse Phase 2–3 not fully shipped," "predictions register 5 / resolve 0") as **unverified until checked against the actual stores** — my "already handled" section inherits that uncertainty. The structural critiques above don't: they follow from contradictions visible in the memo text itself.
