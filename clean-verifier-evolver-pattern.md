# The Clean-Verifier Evolver Pattern

> Generalized from hutter (instance #1, 2026-06-08..10) on Markus's call. hutter's CLAUDE.md /
> PRIZES.md define the strategy and target portfolio; THIS doc is the reusable architecture +
> the operational patterns and anti-patterns that earned their keep, for the next evolver
> (ARC-AGI-2, AIMO, SAT/superoptimization, MoE-pruning — anything passing the three conditions).

## When this pattern applies — three conditions, all checkable upfront

- **C1 — clean global verifier:** cheap, ungameable, independent (bit-exact round-trip + byte
  count; exact grid match; answer match; equivalence checker + cycle count). If verification is
  expensive, contested, or model-judged, STOP — the loop degrades to gameable proxies.
- **C2 — exact objective decomposition:** the score sums over parts (S = Σ −log₂ p per bit;
  score = Σ tasks; P&L = Σ positions). Buys exact local attribution, not estimates.
- **C3 — mixture/portfolio structure:** components whose marginal value is replayable offline
  (model ensemble, solver portfolio, DSL primitive set).

C1 alone → the basic ratchet works. C1+C2+C3 → the full move-set below. No C1 → different
playbook entirely (corpus/attestation substrates, cross-model critique).

## Architecture — two loops, one git bus

- **Grinder** (cheap tireless model, e.g. codex/GPT-5.5 on subscription): the object-level
  `propose → build → verify → ratchet → ledger` loop. **No skills, no LLM-judge, no memory
  beyond the ledger.** The verifier IS the judge; the ledger IS the memory. Restart-loop
  wrapper (rc-aware backoff), never a watcher process; a long session's context is disposable.
- **Dreamer** (frontier model, skilled): steers via the bus only — diagnoses stalls, refills the
  queue with SHARP grounded moves, gates discovery-tier jumps, builds harness/instrumentation.
  Decides+acts autonomously on technical/strategy; escalates only money / taste / irreversible /
  model-class.
- **Bus = git files:** `queue/` (Dreamer→Grinder moves; grinder re-reads EVERY iteration),
  `ledger.db` (every trial: S, RSS, time, verdict, lineage, predicted-vs-actual), `IDEAS.md`
  (ripe-when-ready backlog with execution gating + consumption status), `proposals-pending/` /
  `decisions-pending/` (human gates). The loops never call each other.
- **Search ↔ discovery boundary:** parameter/component-level change = autonomous; model-CLASS
  change = human-gated, flagged to proposals-pending while the loop keeps grinding.

## The core moves (evidence: one night, 2026-06-09→10)

1. **Second truth machine when dev ≠ target.** The dev box (M3/macOS) silently lied about the
   binding constraint for the project's whole history — macOS memory compression masked ~2× of
   real RSS; the verifier-platform box exposed 10.16 GiB (over the 10 GB cap) within two hours
   of existing, then 16.8 GB @100KB, 20.0 GB @1MB. Timing fields were swap-garbage too.
   *Measure on the platform that judges. Budget ~$0.12/h; first-hour ROI.*
2. **Pre-registered cheap probes before expensive bets.** Lock prediction + decision rule
   BEFORE the result. Three elegant theses refuted by probes in 48h ("GLN completes cmix",
   "match recall pays", "PPMd pool is inert below exhaustion" — the last one mine, +5B says no);
   each negative redirected days of work for minutes of cost. A confident foreclosure claim
   is the tell that a probe is overdue.
3. **Decompose the verifier, not the codebase.** When the global gate is expensive (70 min/eval)
   and lanes are scarce, the bottleneck is verifier latency — N parallel idea-generators just
   queue N proposals behind one gate. Instrument ONE run to log what the system already computes
   and discards (per-component predictions + weights per step), then: exact per-component loss
   attribution offline + counterfactual replay as a SCREEN (seconds, parallel, off the critical
   path). The gate keeps the gavel — frozen-context replay ignores adaptation, so surrogate-win
   ≠ gate-win, same epistemic rank as any screen. Validation gate for the instrument itself:
   reconstructed objective must equal the measured one (CE ≤ S, fixed overhead — at small scale
   a constant overhead masquerades as a % error; validate in absolute bytes).
4. **Attribution → reallocation under the hard budget.** Components the mixer never pays for are
   pure budget (RAM/time/params); prune and reinvest where attribution says it earns. Converts a
   compliance constraint into an optimization lever. (cmix enwik4 first table: best single paq8
   stream = 97% of the system; the other ~500 streams + 3 mixer layers + SSE net 2.8% — tier-
   caveated, but the hit-list shape is visible.)
5. **Adopt proven recipes before re-deriving.** The record-holder's memory-tuning IS the
   compliance recipe; diff its constants, don't bisect your own (one knob probed: pool 14000→2500
   = +5B @100KB, −64B @1MB — noise-scale both directions, 11.2 GiB freed). Out-invent the
   frontier on the LOOP, not on 20 years of domain tuning.
6. **Mine the ledger for free differences before dispatching.** When one measured config is a
   SUPERSET of another (same base, same tier), their difference prices the delta-component at
   zero cost — check for embedded supersets before any new run. (hutter: move1's patch embedded
   move2 ⇒ rows 9−11 priced verification at +20; a planned 3 h probe cancelled by subtraction.)
7. **Redundancy is created by improvement — re-ablate neighbors after every structural win.**
   In an adaptive ensemble, strengthening one component makes others deletable that weren't
   before (four-candidate strengthened Word's embedded matches ⇒ the AddMatch family became a
   FREE deletion worth 1.85 GB, hours after winning −54 through it). Deletion opportunities are
   downstream of wins; a static prune list goes stale the moment you accept a change.
8. **Cheap-tier ablations are sign-and-existence screens, NOT prices.** Value magnitudes scale
   ×3-10 (heterogeneous) from lab-slice to truth tier (paq8: +347 @100KB → ~+3,568 @1MB; Direct:
   −14 → −38). Never budget a trade from small-tier numbers; only direction and existence survive
   the tier jump.

## Operational patterns that earned their keep

- **Monitor-primary, heartbeat-fallback, cache-aware:** an event monitor polls the ledger
  (fires on records / ERROR / grinder-down / stall); ScheduleWakeup heartbeats at 1200-1800s+
  are the fallback only. Stall windows must model the SLOWEST phase (a swap-stretched round-trip
  fired a false STALL at 76%-done; benign, but alarm windows ≠ happy-path estimates).
- **Detached self-sequencing remote pipelines:** on a flaky link, deliver once into ANY window
  (retry loop, idempotent phases, sha-verify, sentinel files, `setsid nohup`), then the remote
  box sequences itself (build → wait-for-RAM → run → score). Never stream a long job through a
  live SSH session. Dual-port sshd (22+443) routes around ISP filtering of hosting ranges.
- **QUEUE_LOW is a diagnosis trigger, not auto-refill.** Stall ⇒ check gate health, slice
  discipline, and WHERE the plateau is (scale-gated? slot-tapped?) before writing moves. The
  right refill is a diagnosed sharp move; blind volume lengthens the queue, not the record.
- **Generator rotation when all slots read tapped:** attribution data → code-grounded read of an
  untouched subsystem → external frontier scan → pretraining-dedupe (grep the idea stock BEFORE
  claiming novelty) → only then divergent volume. Idea stock carries provenance + grade +
  consumption status (`CONSUMED → queue id` / `DEAD → gate evidence`) to block cross-session
  re-generation of refuted ideas. **Rotate FRAMES, not just sources** — the move vocabulary
  itself inherits corpus blind spots (FM27-31 one level up): audit which dimension no move
  touches (time/order/phase), write each constraint's quantifier (a max-over-X invites
  scheduling over X), invert the data exhaust (owned measurements ⇒ unasked questions), and
  steelman naive outsider questions. Evidence: hutter's mid-run-retirement miss (2026-06-10) —
  three stated facts composable into a new move axis, found by the human, not the loop.
- **Single-writer trees.** One grinder per working tree, ever. Dreamer experiments happen on a
  separate clone/box; analysis subagents are read-only; results route back through the bus.
- **Verify the edit before believing the result.** A silent no-op edit produces a prediction-
  confirming result (sed that didn't match + "S unchanged" = fake pass). Echo the changed line
  in the dispatch; check the diff before interpreting.

## Anti-patterns (all observed, all cost something)

- **Pumping idea volume when verifier-bound** — 7 unconsumed proposal docs while the gate had a
  9-hour queue. Generation is almost never the constraint; check which resource is actually idle.
- **Locally-better ≠ globally-better** (id210: a strictly-better-information component lost
  bytes through the mixer). Cuts both ways: surrogate screens inherit the same caveat.
- **Narrating mid-flight** — calling a slot "tapped" while its eval runs; the gate then prints
  the opposite. Wait for the row, then speak.
- **% thresholds on fixed-absolute overheads** — a 38-byte constant read as "1.35% BROKEN" at
  2.7KB scale. Validate in the unit the mechanism lives in.
- **pgrep -f with a pattern your own wrapper's cmdline contains** — self-match deadlock (a
  heredoc dispatch carrying the literal string it later greps for). Use `pgrep -x`.
- **Trailing `&` swallowing a verification chain** — `fix && verify && launch & echo OK`
  backgrounds ALL of it; the echo lies. Verify synchronously, launch detached separately.
- **Two grinders / shared tree** — corrupts variant attribution and the ledger. Hard invariant.
- **Source reverted, binary stale** — a dispatch that edits/reverts source but skips the rebuild
  runs the PREVIOUS config and writes a mislabeled ledger row (hutter box Move-0: "baseline-stock"
  ran the capped binary; caught because the S exactly reproduced the other config's number).
  Every config-change dispatch rebuilds before eval; ledger rows should carry binary provenance
  (binary hash), not just source SHA.
- **Building the corpus/substrate reflex** — a clean-verifier domain needs NO claim graph; the
  ledger + bus already are the epistemics (see `decisions/`-vetoed knowledge-substrate pattern:
  generation without consumption). Re-check C1 before reaching for the usual infrastructure.
- **Predicting from text priors instead of the ledger** — the model's pre-registrations run
  systematically hot: corpus over-reports successes, under-reports interactions, mis-prices
  selected systems, and presents toy-scale lessons as general. Band-set from the project's own
  calibration views (reference class FIRST), apply measured correction factors, and treat
  small-tier verdicts as hypotheses. Full catalog with evidence: `agent-failure-modes.md`
  FM27-FM31 (hutter calibration night: 4/11 hits, all misses in the predicted directions).

## Bootstrap checklist for evolver #2

1. Verify C1/C2/C3 in writing; pick the truth tier ladder (cheap lab slice → real target).
2. Provision the verifier-platform box day one (don't trust dev-platform measurements of the
   binding constraint). Red-team the enforcement rail (canary that MUST fail).
3. Stand up: ledger schema (predicted_ds column — calibration is data), justfile gates with
   compliant flags, restart-wrapped grinder, queue/bus dirs, Monitor + heartbeat.
4. Write LOOP.md for the grinder: gate-is-only-truth, slice discipline, parking lot with
   falsifiable revisit conditions, stall protocol, search/discovery boundary.
5. Build instrumentation EARLY (move 3) — it's measurement infra, not innovation; it steers
   everything else. Validate it against the global verifier before trusting any table.
6. Find the domain's fx2 — the existing best-practice recipe to adopt before tuning.

Evidence: hutter@{9df950e..63a9ec2} session 2026-06-09→10 — box stand-up + RSS truth (16.8GB@100KB),
two negative pre-registered probes (id210 match, id3-box PPMd), instrumentation e2e + first
attribution table (commits 54828cc, 68c3da4), PPMd sign-flip (+5B/−64B), QUEUE_011 scale batch.
