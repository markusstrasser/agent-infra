# Symphony Mining — Reference Study (NOT a dependency)

Target: github.com/openai/symphony (OpenAI, Apache-2.0, Elixir, 25.3k★, pushed 2026-06-09)
Pitch: "turn project work into isolated, autonomous implementation runs — manage work instead of supervising coding agents."
Studied: 2026-06-12. Sources: README.md, SPEC.md (language-agnostic Draft v1), elixir/WORKFLOW.md, elixir/lib/symphony_elixir/{orchestrator,path_safety}.ex.

Bottom line: Symphony is a **central, single-authority orchestrator daemon** (an Elixir GenServer) that polls a **Linear board** as its work queue and dispatches **bounded-concurrent** Codex workers into **per-issue persistent workspaces**. It is the architectural OPPOSITE of OUTER-LOOP (no central process, git-as-bus, one-LLM, launchd restart-loop). It does NOT validate our no-orchestrator stance — it is a serious, well-specified counter-example we should engage honestly. But its design context differs from ours in ways that mostly preserve our decision. Details + the one honest reconsideration trigger below.

---

## 1. Core abstraction: task / manager / worker

(a) **What it does.** The unit of work is a **Linear issue** (SPEC §4.1.1) — Symphony has no internal task model; the tracker IS the queue and the source of truth. The "manager" is a single `Orchestrator` GenServer (SPEC §3.1.4, orchestrator.ex:1 `use GenServer`) that owns the poll tick and ALL scheduling-state mutation. A "worker" is one `AgentRunner`-launched `codex app-server` subprocess bound to one issue's workspace. Decomposition is **NOT done by Symphony** — humans (or upstream agents) decompose work into Linear tickets; Symphony only *dispatches* tickets. Assignment = poll → filter eligible → sort by (priority asc, created_at oldest, identifier) → dispatch until concurrency slots exhausted (SPEC §8.2).

(b) **Non-obvious mechanism.** Policy is **externalized into an in-repo `WORKFLOW.md`** with YAML front-matter (tracker/polling/workspace/hooks/agent/codex config) + a Liquid prompt body (SPEC §5). The prompt template uses *strict* rendering — unknown var/filter = hard fail (SPEC §5.4). The workflow is **hot-reloaded** on file change without restart (SPEC §6.2). So the entire agent behavior contract (prompt, concurrency, sandbox, states) is version-controlled with the code. The worker is told to maintain ONE persistent Linear comment ("## Codex Workpad") as externalized scratch/plan/acceptance/validation state across turns (WORKFLOW.md "Workpad template").

(c) **VALIDATES** our externalize-policy-to-a-file instinct strongly (their WORKFLOW.md ≈ our OUTER-LOOP.md + WORKFLOW prompt). It is orthogonal to the orchestrator question.

(d) **Lift even if we reject the whole:** the **Workpad-as-single-mutable-comment** pattern — one durable, in-place-edited progress doc that is plan + acceptance criteria + validation + handoff notes, never append-spam. This is exactly our "externalize recoverable bookkeeping, leave policy semantic decisions" (Harness-1) realized as a discipline the prompt enforces.

## 2. Orchestration mechanism — THE part we care about (we removed ours)

(a) **What it does.** A central GenServer poll loop (default 30s, WORKFLOW.md uses 5s). Each tick (SPEC §8.1): reconcile running → preflight-validate config → fetch candidates → sort → dispatch. State is a single in-memory `%State{}` struct (orchestrator.ex:28): `running` map, `claimed` MapSet, `retry_attempts` map, `completed` MapSet, `codex_totals`, `codex_rate_limits`. **Stall detection** (SPEC §8.5 Part A; orchestrator.ex:303 `reconcile_stalled_running_issues`): if now − last_codex_event_ts > `stall_timeout_ms` (default 300s), kill worker + queue retry. **Failure backoff**: `delay = min(10000 * 2^(attempt-1), max_retry_backoff_ms=300s)` (SPEC §8.4). **Continuation**: a clean worker exit schedules a ~1s "is the issue still active?" re-check retry (SPEC §7.1) — the worker itself loops up to `max_turns=20` on one live thread before exiting.

(b) **Non-obvious mechanisms — three worth noting:**
   - **No durable DB.** "Support restart recovery without requiring a persistent database; exact in-memory scheduler state is not restored" (SPEC §2.1, §7.4). Recovery is **tracker-driven + filesystem-driven**: on restart it re-reads Linear (the queue) and the workspace dirs (the work product), and reconciles. The *queue itself is durable because it's Linear*; the orchestrator's own state is disposable. This is the key insight — they got queue durability for free by making an external SaaS tracker the queue.
   - **Crash-detection via BEAM `Process.monitor`** (orchestrator.ex:194 `{:DOWN, ref, :process, ...}`) — worker death is an OTP message, not a polled health-check. This is OTP supervision doing what our launchd restart-loop does, but in-process and per-worker.
   - **`claimed` set distinct from `running` map** (SPEC §4.1.8) — a claim is taken at dispatch-decision time to prevent the same tick (or a retry timer) from double-dispatching an issue that's reserved-but-not-yet-running. Idempotency primitive.

(c) **Does it CONTRADICT our no-orchestrator stance? Honest answer: partially, and worth stating plainly.**
   - The thing we eradicated in 2026-06 was a **queue-backed orchestrator with its own durable DB** (`agent-state.json`, StopFailure backoff, the parked `archived_orchestrator.py`) that had **0 invocations in 9 months** of indexed agentlogs. Symphony is NOT that: it is a *live, load-bearing, externally-queued* daemon whose queue durability is outsourced. Our orchestrator died of **disuse**, not of being architecturally wrong for a fleet workload.
   - **The honest reconsideration trigger:** Symphony's whole reason to exist is **bounded-concurrent fan-out over MANY independent tickets** (max_concurrent_agents=10). OUTER-LOOP is **ONE serial RSI loop on ONE artifact** (the hutter compressor). If our workload ever becomes "N independent improvement tasks running in parallel with retry/stall/concurrency caps," then a Symphony-shaped coordinator becomes the right tool — and our git-as-bus + launchd-restart pattern would NOT scale to that cleanly (no concurrency cap, no per-worker stall kill, no claim set). **Flag:** the no-orchestrator decision is correct *for a single-artifact serial loop*; it is NOT a general truth. If hutter (or anything) spawns a multi-task parallel queue, re-open it.
   - For the CURRENT one-artifact loop: Symphony VALIDATES our choice by contrast — it carries a poll loop, claim set, retry map, stall timer, concurrency accounting, reconciliation, and a tracker adapter (≈59 .ex files) entirely to manage *fan-out we don't have*. Adopting it for a serial loop would be config-for-divergence.

(d) **Lift even if we reject the whole:** the **"no orchestrator DB; queue durability is outsourced to an external authoritative store; orchestrator state is disposable and reconstructed by reconciliation"** principle. Our git history already IS such an external authoritative store. If we ever DO need a coordinator, build it stateless-over-git the way Symphony is stateless-over-Linear — never reintroduce a private state DB (that's exactly what we killed). Also liftable: **stall = "no agent event for N seconds," killed by a reconciliation pass, not a separate watcher** (SPEC §8.5 / orchestrator.ex:303) — matches our "QUEUE_LOW is a diagnosis trigger, reconciliation not a watcher" instinct.

## 3. Human-in-the-loop surface

(a) **What it does.** HITL is expressed as **Linear states**, not code gates. The workflow defines a state machine (WORKFLOW.md "Status map"): `Todo → In Progress → Human Review → Merging → Done`, plus `Rework`. The agent runs **fully autonomously** from Todo through to `Human Review`, then **STOPS and polls** — "When the issue is in Human Review, do not code or change ticket content" (WORKFLOW.md Step 3). A **human** moves `Human Review → Merging` (the approval act). Only then does the agent run the `land` skill to merge. So: autonomous implementation + validation + PR; human owns the **merge-approval** transition; agent owns the land mechanics after approval.

(b) **Non-obvious mechanism.** The approval gate is a **tracker state transition a human performs**, and the agent **busy-polls** for it rather than blocking on a callback. Also: `codex.approval_policy: never` + `sandbox: workspace-write` in the live WORKFLOW.md — i.e. *within* the workspace the agent has zero per-action approvals; the ONLY human checkpoint is the board-level Human Review → Merging move. The README is explicit this is a "low-key engineering preview for testing in **trusted environments**."

(c) **VALIDATES** our "money/taste/risk → human, everything else the agent decides" exactly, mapped onto a different risk axis. Their human checkpoint = the irreversible act (merge to main). Our human checkpoint = money/taste/risk. Same shape: autonomous production, retained judgment on the irreversible/high-stakes transition. This is our Constitution's "amplify" regime (reduce production burden, preserve judgment supervision) implemented as a board state.

(d) **Lift:** **make the single human checkpoint a state transition the human performs on an external board, and have the agent poll for it** — cleaner than an inline approval prompt for async, unattended runs. Relevant if OUTER-LOOP ever needs a "Dreamer approves promotion of a candidate" gate: model it as a state flip, not a blocking call.

## 4. Isolation model — does it contradict "soft-isolation-hurts" (CAID)?

(a) **What it does.** **Per-issue persistent filesystem workspace**: `<workspace.root>/<sanitized_issue_identifier>` (SPEC §9.1). Each issue gets its own dir, populated by an `after_create` hook that `git clone`s the repo fresh (WORKFLOW.md hooks). Workspaces are **reused across runs** for the same issue, not deleted on success. Concurrency isolation = **separate working directories + separate Codex subprocess + Codex's own sandbox** (`thread_sandbox: workspace-write`, `turn_sandbox_policy: workspaceWrite`).

(b) **Non-obvious mechanism.** `PathSafety.canonicalize/1` (path_safety.ex) does **symlink-resolving canonicalization** segment-by-segment (`File.lstat` → if symlink, `:file.read_link_all` and re-resolve) so the safety invariant "run the agent ONLY inside the per-issue workspace" (SPEC §9.5 Invariant 1) can't be defeated by a symlink escaping the workspace root. That's a genuinely careful bit — they treat workspace containment as a security boundary, not a convention.

(c) **Does NOT contradict CAID — it AGREES.** This is **hard isolation**: distinct directories + distinct processes + OS/Codex sandbox + symlink-escape defense. It is precisely the "hard filesystem isolation beats soft/verbal isolation by 7.8pp" finding (CAID arXiv:2603.21489) that underpins our worktree-isolation default. Symphony uses *separate full clones* rather than git worktrees, but the principle is identical: physical FS separation per concurrent agent. Nothing here says soft isolation works. If anything it raises the bar (full clone > worktree in isolation strength, at the cost of disk + clone time).

(d) **Lift:** **`PathSafety` symlink-resolving canonicalization as a containment check** before any agent-launched command — stronger than our current worktree boundary (which doesn't defend against symlink escape). Cheap to port the idea into a pre-dispatch guard if we ever run untrusted-ish agent commands.

## 5. State-externalization patterns (Harness-1 lens)

(a) **What it does.** Multiple recoverable-state externalizations:
   - **Queue → Linear** (not in orchestrator memory).
   - **Plan/progress/acceptance/validation → the single "## Codex Workpad" Linear comment** (WORKFLOW.md Workpad template) — the agent's working memory lives outside the agent, in-place-edited.
   - **Work product → persistent per-issue workspace dir** (survives restarts).
   - **Token/turn accounting → `LiveSession` + `codex_totals`** (SPEC §4.1.6/§4.1.8, elixir/docs/token_accounting.md) — input/output/total tokens tracked per session and aggregated.
   - **Policy → WORKFLOW.md** (hot-reloaded).
   The orchestrator's OWN state is deliberately the ONLY non-externalized, disposable part.

(b) **Non-obvious mechanism.** The division of labor is textbook Harness-1: **everything recoverable is externalized to a durable store (Linear / FS / WORKFLOW.md); the policy process keeps only the semantic, in-flight scheduling decisions** — and even those are reconstructable by reconciliation. They explicitly accept "exact in-memory scheduler state is not restored" (SPEC §2.1) because everything that MATTERS is external.

(c) **VALIDATES our state-externalization lens** completely and is a clean independent confirmation from OpenAI. Our memory note [State-externalization lens] (Harness-1: externalize recoverable bookkeeping, leave policy semantic decisions) is the exact design rule Symphony follows.

(d) **Lift:** **the Workpad pattern as the agent's externalized scratchpad** (item 1d) and the **"orchestrator state is disposable, durability is outsourced"** rule (item 2d). Both are direct Harness-1 instances we can cite/reuse.

---

## Verdict on the brief's core question

Does anything here make us reconsider eradicating the orchestrator? **One conditional yes, otherwise no.**
- **No** for the current OUTER-LOOP workload: single-artifact serial RSI loop. Symphony's machinery (concurrency caps, claim set, per-worker stall kill, tracker adapter) exists to manage *parallel fan-out over many tickets* we don't have. Our eradicated orchestrator died of 0-usage disuse, not of being wrong; re-adding one for a serial loop = config-for-divergence.
- **Conditional yes** the moment any workload becomes **N independent parallel improvement tasks** with retry/stall/concurrency needs. Then a Symphony-shaped, **stateless-over-git** coordinator (NOT a private-DB orchestrator like the one we killed) is the right design. Pre-register this trigger: ">1 concurrent independent agent task needing dispatch caps + stall kill" → re-open the orchestrator question, build it stateless over an external authoritative queue.

## Patterns worth lifting (ranked, all cheap, none require adopting Symphony)
1. **"## Codex Workpad" single-mutable-comment as externalized agent scratchpad** (plan+acceptance+validation+handoff, edited in place, never append-spam). Directly portable to OUTER-LOOP / any unattended loop.
2. **Orchestrator-state-is-disposable / queue-durability-outsourced** principle — if we ever need a coordinator, build it stateless over git, never with a private state DB (the thing we killed).
3. **`PathSafety` symlink-resolving canonicalization** as a pre-launch containment guard (stronger than our worktree boundary).
4. **Single human checkpoint = an external-board state transition the agent polls for** (clean async approval gate; relevant if Dreamer ever gates candidate promotion).
5. **WORKFLOW.md = version-controlled policy contract (front-matter config + strict-rendered prompt), hot-reloaded** — validates our OUTER-LOOP.md externalization; strict template (unknown var = fail) is a nice hardening.

## Honest contradictions / things that should give us pause
- Symphony is proof that a **central orchestrator is the right answer for fan-out**, from a credible source (OpenAI). Our "no orchestrator" is a workload-scoped truth, not a universal one. Don't cite the eradication as a general principle.
- It uses **full clones, not worktrees** — slightly stronger isolation than our default; if disk allows, full-clone-per-agent is the safer end of the CAID spectrum.
