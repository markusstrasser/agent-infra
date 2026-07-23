# Raycast snippets as a shadow harness — copyCount is a ranked failure-list for "architecture over instructions"

**Date:** 2026-07-23
**Source data:** decrypted V2 `.rayconfig` export (470 snippets w/ per-snippet `copyCount`, 82,761 activity events). Scrubbed prompt-library: `data/raycast/snippets-scrubbed.json`. Prune list: `data/raycast/prune-candidates.md`.
**Method:** decrypt export (scrypt+AES-GCM, passphrase from login Keychain) → categorize 470 snippets → cross-reference the agent-workflow subset against always-loaded CLAUDE.md rules and installed slash-commands.

## The finding

Markus's most-fired Raycast snippets are a **hand-typed second copy of this repo's own constitution**, and the copy is fired thousands of times. The snippets that most redundantly restate an *already-always-loaded rule* form a ranked list of where **"architecture over instructions" (constitution principle 1) is empirically failing** — because a rule that fires reliably would not get manually reinforced 200–700 times.

This is the telemetry stream agent-infra never had: not "what rules did we write" but "which behaviors does the operator not trust the harness to perform, measured by how often he re-types them by hand."

## Headline: two always-on rules get manually boosted hundreds of times

| Behavior | Snippet(s) | Manual fires | Already in harness as | Enforcement today |
|---|---|---|---|---|
| **Granular semantic commits** | `;gc` 432 · `;gb` 21 · `;kco` 11 | **464** | `<git_rules>` "After completing a task, commit without being asked… granular semantic commits" | **instruction only** |
| **Breaking refactor, no compat cruft** | `;adev` 142 · `;break` 91 | **233** | principle 14/16 + `<technical_pushback>` "Default to breaking" | **instruction only** |

Both are supposedly *automatic / always-on*. The operator still types them by hand 464× and 233×. Per principle 1 ("instructions alone = 0% reliable; if it matters, enforce with hooks/tests/scaffolding"), that manual-boost frequency is the strongest evidence in the system that these two behaviors are under-architected. They are the **highest-priority hook candidates**, ranked by real demand:

- **Auto-commit (464):** the auto-commit rule is instruction-level, so on any given task it fires <100% of the time; the operator compensates by re-typing it. A Stop-hook that detects "task complete, uncommitted changes present" and either commits or nags would absorb most of these fires. (There is already a commit-message *format* hook; there is no "did you commit at all" gate.)
- **Breaking-refactor (233):** harder to hook (semantic), but the demand is real. Candidate: a PostToolUse advisory when an edit introduces a compat shim / wrapper / `// removed` comment — the exact anti-patterns `;break` exists to suppress.

## The three graduation buckets

Agent-workflow snippets (130 of 470, 2,477 total fires) sort cleanly:

### 1. Redundant with an existing RULE — the instruction-vs-architecture gap (fix by hooking, not documenting)
| Snippet | Fires | Rule it restates |
|---|---|---|
| `;subst` "session end: what can we improve/eradicate/rethink with tooling/hooks/goals" | 653 | the RSI/observe ritual (`/observe`, `/rsi close`) |
| `;epl` "execute the plan fully, use subagents/llmx" | 488 | `<execution>` "Execution After Plans" |
| `;gc`+`;gb`+`;kco` | 464 | `<git_rules>` auto-commit |
| `;break`+`;adev` | 233 | principle 14/16 breaking-refactor |
| `;rsi` "why did you not figure this out, metaimprove next loop" | 68 | the pair-rule / RSI governance |

These don't need new features — they need the *existing* instruction promoted to architecture (the whole point of this repo). copyCount ranks them.

### 2. Redundant with an existing COMMAND — the discoverability/trust gap (interface problem)
| Snippet | Fires | Command that already exists |
|---|---|---|
| `;tweb`+`;tres`+`;ures` "use research tools, exa deep research in parallel, arxiv/biorxiv/tavily" | 359 | `/research` |
| `;simpler` "first principles, minimize cognitive load, elegant refactorings" | 141 | `/simplify` |
| `;cl` "ask clarifying questions, top 5, multiple choice" | 75 | `AskUserQuestion` tool |

The capability exists; the snippet wins because typing `;tres` is faster and more *trusted* than remembering the slash-command fires with axis diversity. This is a `/interface-thinking` problem (muscle-memory + trust), **not** a missing-capability problem. Do **not** rebuild `/research` etc. — close the gap by making the command as reflexive as the snippet (or by having these snippets *invoke* the command).

### 3. No harness twin — genuine graduation candidates (build)
| Snippet | Fires | What it does | Candidate |
|---|---|---|---|
| **`;ag`** "{clipboard} — pasted from another AI agent, be critical, it might be slop, cosign/reject/complement" | **471** | pull clipboard → critically evaluate another model's output | **top candidate**: a `/cosign` command that reads clipboard and runs the `<ai_text_policy>` protocol. Highest-use no-command snippet by 3×. |
| `;asp` "exact reasoning + step-by-step plan, what to test at each step — the spec for the agent" | 33 | structured agent-spec generation | maps toward `/doe` / Plan skill |
| `;minv` "given this output, what prompt would have produced it" | 10 | meta-prompt inversion | novel; park unless it recurs |

`;ag` at 471 fires with zero command twin is the clearest "principle 11 (the Raycast heuristic — literally named for this): 10+ uses → architecture" violation in the set.

### Out of scope for agent-infra (different telos — leave alone)
A large spaced-repetition/Anki cluster (`;srs`, `;2srs`, `;p-srs`, `;ankib`, `;anki`, `;t-anki`, `;p-decl` — flashcard generation) and personal expanders (`;em`, `;phone`, banking). Not this repo's domain; noted so a future sweep doesn't try to "graduate" them here.

## Prune

220 of 470 snippets have never been expanded (`copyCount==0`). 208 are safe-delete (non-secret); 12 are API-key/reference stores kept *for lookup*, not expansion — do not bulk-delete those. Full list: `data/raycast/prune-candidates.md`.

## Security aside (not the point of this memo, but load-bearing)
[Security details removed 2026-10-07.]

## What this implies for "what do we build next"
1. The RSI loop should ingest `copyCount` as a **demand signal for graduation**. The bins above are actionable now; #1 (auto-commit hook, breaking-refactor advisory) is the highest-value because it's this repo's exact telos and the data ranks it.
2. Do **not** build Raycast sync infrastructure — no recurring pain, the decrypt→export round-trip covers re-reads (pre-build #1/#3).
3. Snippet↔rule mapping is worth re-running when the corpus shifts materially — it's a cheap read over an export, not standing infra.

## Revisions
_(none)_
