# Astra prompt and skill cleanup — 2026-09-05

**Verdict:** Applied the user's two requests to shared guidance, selected skill workflows, three conflicting repository rules, and existing Codex/llmx callers. The measured result is smaller entry-point context and corrected contracts; this is not a measured improvement in model accuracy or supervision rate.

## Authority and sources

The user supplied “Rethinking skills and prompts for GPT-6 Astra,” approved the proposed cleanup with “ok do,” then supplied the full model guidance and asked to apply it “in general and for relevant repos.” The shared changes and their propagation fall within that authorization.

- [Skills article supplied by the user](/Users/alien/.codex/attachments/3c2fa1fe-1142-4fe8-817e-27c0584965d2/pasted-text.txt).
- [Model guidance supplied by the user](/Users/alien/.codex/attachments/7476431b-7e52-4367-8a9c-27c8646ad6c7/pasted-text.txt), checked against the [official guide](https://developers.openai.com/api/docs/guides/latest-model).
- Installed `codex exec --help`, actual dispatch builders/callers, and offline request captures establish compatibility claims.
- The correction separating biomedical evidence type from certainty follows [Cochrane Handbook chapter 14](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-14).

The option record is `.claude/plans/01a07099-astra-context-pruning.md`. Five alternatives were considered: delete skills, advertise every mode separately, keep focused native routers, build a custom context compiler, or replace everything with generic prompts. Selected focused routers plus targeted corrections: existing consumers remain identifiable, and no new loader or runtime service is required.

## Measured context change

| Entry points | Before words | After words | Reduction |
|---|---:|---:|---:|
| Shared global + agent-infra root instructions | 6,036 | 2,664 | 55.9% |
| Observe + critique + research skill roots | 17,105 | 1,973 | 88.5% |

Reproduce current sizes:

```sh
wc -l -w ~/.claude/CLAUDE.md ~/Projects/agent-infra/CLAUDE.md
wc -l -w ~/Projects/skills/{observe,critique,research}/SKILL.md
```

Before snapshots were taken before editing. Final root sizes are global 101 lines/1,507 words; repo 95/1,157; observe 76/707; critique 54/644; research 48/622. These are entry-point sizes, not total words across all references or measured tokens for a complete task. Specialized detail and incident history remain available on demand. The operator's existing `Short > long responses.` edit remains byte-exact and outside these commits.

## Result and scope

- Shared guidance carries authorization through completion, states user precedence over skill guidelines, requires transparent explanations for skill-driven pauses, favors concise prose, delegates useful independent work, and scopes verification to the change. The existing approval boundary is reconciled rather than replaced.
- Observe, critique and research now route to the selected workflow. All 20 observe manifest modes, the `sweep` alias, raw-transcript authority, backpressure, source verification, real external-action boundaries and numbered constitutional principles remain. Existing callers, manifests, anchors, tests and the incident-appending helper were migrated.
- Research dispatch references now use the current CLI and actual artifact contracts. They no longer prescribe a universal old-model error rate, fixed file/lane quotas, minimum report length, repeated approval for authorized work, or full-suite repetition for every fix. Historical text is retained separately.
- An inventory covered 33 other project directories, 21 with the requested active instruction surfaces and 111 distinct resolved files. Candidate clauses were read in context; unrelated files were screened rather than all read in full. Targeted edits: genomics checks artifact completeness before recovery; intel follows existing Law 6 authority throughout rule evolution; anim-workbench runs GROW only under an authorized GROW charter. Their scientific, financial, provenance, evaluation and iteration gates remain.
- Existing Codex callers now use `-s` and `-C`. llmx permits Astra on its existing subscription route, maps `none`/`minimal` to `low`, preserves `max`, omits unsupported sampling parameters, and shares request construction across Python chat/stream paths. Streaming now passes the existing spending guard before SDK construction.
- The source extraction correction distinguishes a healthy empty window from a missing/broken source. Failures propagate without overwriting prior artifacts, and drift retains Codex-only evidence. This was verified at both producers and their actual consumers.

## Input and finding dispositions

| Input | Result |
|---|---|
| User's skills article and initial approval | Focused routers and smaller always-loaded instructions; preserved operational/history references. |
| User's model guide and wider repo request | Five shared behaviors, three local override repairs, current Codex guidance and actual caller fixes. |
| Skill caller explorer | Followed manifest, incident-helper, reference, test and governance-parser consumers before moving content. |
| Observe implementation and source-contract follow-up | Integrated selected-mode references and producer/consumer corrections; retained source coverage and all modes. |
| Critique implementation | Integrated focused review routes, corrected moved callers, retained deterministic gate/manifest behavior and single diff-review routing. |
| Research implementation | Integrated bounded-depth research routes, relevant source checks, source-grade pointers and history; later removed contradictory active dispatch references. |
| Initial premise scout and four review axes (structure, gaps, correctness, contracts) | Accepted preservation of backpressure, routes, constitutional markers, authority distinctions, moved references and semantic checks. Rejected a new uppercase loader, compulsory catalog expansion, blanket permission re-asking, and unverified heading-parser claims. Existing native validators are useful but do not prove semantic closure. |
| Independent nine-case routing review | Resolved all eight concrete findings below. This was a forward source-reading probe, not an executed-agent benchmark. |
| Repo guidance audit and implementation | Three targeted edits; full source comparisons preserved unrelated gates and dated incident text. Other screened repos inherit shared guidance without duplicate policy copies. |
| Integration audit and llmx implementation | Reproduced removed flags, effort mapping and unsupported request fields; repaired existing callers. Optional API features without consumers were not built. |
| Five-reference research-ops audit | Resolved active quotas, output assumptions, repeated approvals/testing and historical-rate generalizations in the actual canonical files behind tracked symlinks. |
| Incident-helper code review | Rejected alleged printf injection: the format is constant `%s`; literal-input and path validation tests passed. |
| Final Cursor code review | All eleven requested source/test files included with nonempty diffs and full numbered source; `NO_ISSUES`, independently checked against the implementation. |

Independent routing findings, all resolved:

1. **F1:** maintain health pipelines obscured status/findings — inspect complete health results and preserve failure status.
2. **F2:** maintain prose implied broader self-directed authority — bind it to the canonical scope and existing user authorization.
3. **F3:** noop could stop before required priority/artifact work — finish the sweep and parent outputs before closing.
4. **F4:** prose exempted high-severity findings from recurrence — remove the unsupported exception; actual gate has none.
5. **F5:** same-line join matches counted as proof — require both declarations and the actual mapping/caller or an empirical probe.
6. **F6:** biomedical reference forced irrelevant quantitative/practical sections and duplicate recitation — apply checks only to relevant claims and requested outputs.
7. **F7:** document type was an ordinal certainty grade — separate source design from outcome-specific support and underlying evidence.
8. **F8:** small modules automatically acquired all-provider review — choose scope/preset by requested recall and actual risk.

The generated review extraction contains locator-based `CONFIRMED`/`HALLUCINATED` labels. Those are not principal adjudication, and its reported hallucination percentage is not used here. An apparent missing-reference finding was rejected after resolving the tracked research-ops symlinks. Mere grep absence, line co-occurrence, report length and model agreement are not substitute verifiers.

## Validation and practical limits

- Final `just harness-eval`: PASS — hooks smoke 215; contract group 29; pytest group 13; observe gates 7; extractor tests 9; inventory and architecture fresh; 57 hooks/20 global pretools covered; no stale infra pointers.
- Source extraction producer/consumer regressions: 27 passed. They cover empty versus failed sources, retained previous output, and all Claude/Codex source-presence combinations.
- llmx: 137 tests and 58 subtests passed; one opt-in live Cursor-registry test skipped. Ruff, compile, offline effort/request captures and installed CLI parser checks passed.
- Agent-infra Codex wrappers/autoresearch: 8 tests passed. Shared CLI contracts: 5 passed, 4 live smokes skipped. No paid Astra request was made.
- Native core-skill validators and manifests passed. The integrated active-document check verified 54 local links/anchors, two shell blocks in bash and zsh, five complete reference snapshots, and the superseded research dispatch root preserved verbatim. The follow-up research-reference check also verified five complete old bodies, 19 canonical/alias link contexts and four unchanged symlinks.
- Maintained 15 numbered constitutional principle titles and validated their existing generated index. No new skill/checklist enforcement instrument was introduced.

Astra's native API route remains fail-closed because verified pricing is not registered. Offline request compatibility does not establish paid API admission or live model success. Tiered defaults, historical evaluation pins, API pricing/key configuration, optional async/WebSocket/cache machinery and production workload execution were not changed.

A separate unresolved evidence-authority question remains: `observe_gates_lib.py` accepts supplied `recurrence >= 2` OR two distinct listed session prefixes. The scope of this correction was the false severity exception. Whether the numeric count independently proves distinct-session evidence requires tracing its producers and raw sources before changing the grader; no recurrence-policy change or calibration claim is made here.

The nine routing cases are a limited source audit, not held-out retrodiction or measured false-positive/false-negative rates. Reduced root size alone cannot establish better behavior; representative live-task comparison remains future evaluation.

## Commits and ownership

Core changes are granular commits on main. Entry-point pruning: skills `ae6149e`, `55a794a`, `bb0a506`; shared global `4e4ceed`; repo `0257083`. Follow-up behavior and current dispatch guidance: global `af16c4e` through `7ecb4fb`, skills `63a950c`, `e285d51`, `e885567`, `ff8cb39`, `be23f63`, `7e2972a`. Runtime repairs: agent-infra `ed76ebf`, `03f7e18`; skills `dc95ace`, `40bf31f`, `38043bc`; llmx `59cd030`. Relevant repo rules: genomics `65f93f52f`, intel `d524ab70`, anim-workbench `07503ce`.

Genomics' ownership guard initially blocked the scripted integration because it lacked this Codex session's write credit. Before integration, the target was byte-identical to the worker's base; after integration it matched the reviewed patch. The existing `write_intent.py` recorded the actual edit using this session's resolved identity, and the unchanged guard then passed. No tracker was manually forged, peer file reverted, or hook disabled. Peer dirt elsewhere was preserved and excluded from path-scoped commits.
