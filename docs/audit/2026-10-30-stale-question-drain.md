# Stale-question drain — 2026-10-30

_One revalidation scout per stale item (backend: codex; `just questions-drain --dispatch`). Scouts recommend; disposition is orchestrator/operator work — see plan 17d2a35c-middle-manager-harvests._

## Scope-bound RECOMPUTE_REQUIRED heads — kill the strand treadmill
- ref: `/Users/alien/.claude/steward-proposals/2026-09-01-scope-bound-recompute-heads.md` · created 2026-09-01 (59d)
- scout: ok=True wall=84s tok(in/out/reason)=269529/1123/31

VERDICT: MOOT
EVIDENCE: genomics commit f00090150 (2026-09-02) implemented scope-bound recompute judgments through the store, lease and drive.
genomics/scripts/stage_semantic_judgment.py:146 matches recompute heads by semantic scope; scripts/genome_kernel.py:1771 includes those heads in current selection.
genomics/tests/kernel_slice/test_semantic_judgment.py:356 covers authorization after mechanical rekey; :389 covers invalidation after semantic change.
RECOMMENDED: resolve-moot — the proposed fix is implemented and current selection preserves recompute authority across mechanical rekeys.

## 🟢 2026-06-29 ~08:05 — dogfood epoch complete: 2 VERIFIED "KG-worse" cases found (your bar, answered)
- ref: `/Users/alien/Projects/substrate/HUMAN.md:92` · created 2026-06-29 (123d)
- scout: ok=True wall=54s tok(in/out/reason)=193000/882/26

VERDICT: SUPERSEDED
EVIDENCE: 5fbe9e7 removed substrate’s claimcore/corpus-extract stack on July 6, including the criticized KG read and entity-resolution paths; current substrate/pyproject.toml excludes them.
genomics/config/penetrance_estimates.json:158–182 supplies sex-specific HFE estimates; scripts/condition_risk_components.py:887 resolves penetrance by endpoint and sex.
4e40b33 fixed dbSNP canonicalization before retirement; e279b9e added the set-returning gene→disease read.
RECOMMENDED: resolve-superseded — the criticized KG route was retired, and current genomics uses explicit penetrance data.

## 🔴 2026-06-29 ~04:50 — DECISION NEEDED: personal data in dogfood memos (your reserved domain)
- ref: `/Users/alien/Projects/substrate/HUMAN.md:129` · created 2026-06-29 (123d)
- scout: ok=True wall=82s tok(in/out/reason)=343852/1259/53

VERDICT: STILL-VALID
EVIDENCE: substrate/docs/research/kg-verification/2026-06-29-verify-bilirubin_interaction.md:38–42 still records the subject’s metabolizer status and lab findings.
~/Projects/skills/hooks/pre-commit-deid-guard.sh:55–64 checks identifiers only; unnamed personal findings can still enter tracked memos.
substrate@efa1508 documents an October history redaction, addressing historical exposure but not the remaining personal-data channel.
RECOMMENDED: keep — history cleanup occurred, but personal findings remain tracked and the broader policy question persists.

## 2026-06-29 ~00:30 — overnight autonomous run (you went to bed; codex paused for your budget)
- ref: `/Users/alien/Projects/substrate/HUMAN.md:154` · created 2026-06-29 (123d)
- scout: ok=True wall=74s tok(in/out/reason)=274453/1198/41

VERDICT: SUPERSEDED
EVIDENCE: substrate commit 5fbe9e7 removed claimcore/corpus-extract, retiring the replay, faithfulness-gate and RxNorm-mint execution paths; current pyproject.toml excludes them.
substrate commit c035146 parked the repository and removed live jobs; README.md:3–6 identifies it as a dormant archive.
genomics commit 8cddacf31 replaced inheritance defaults with bound facts; scripts/offspring_acmg_sf.py:1183–1210 withholds unbound inheritance rather than assuming AD.
RECOMMENDED: resolve-superseded — the KG workflow was retired and the highlighted offspring inheritance failure now has a different safeguard.

## 🌙 2026-06-28 (autonomous KG-build /goal — Front 1 META done; GRIND needs you)
- ref: `/Users/alien/Projects/substrate/HUMAN.md:224` · created 2026-06-28 (124d)
- scout: ok=True wall=42s tok(in/out/reason)=127414/667/9

VERDICT: SUPERSEDED
EVIDENCE: substrate/HUMAN.md:241–261 already resolves the RAM blocker; the remaining ask was KG gap priorities versus corpus-order extraction.
5fbe9e7 (2026-07-06) deleted claimcore and corpus-extract, including the extraction driver and ingest pipeline, after the KG kill-switch.
substrate/pyproject.toml:6–8 confirms retirement; README.md:3–6 identifies today’s repository as a dormant archive.
RECOMMENDED: resolve-superseded — the KG extraction workflow requiring this decision was retired.

## Token cost
- scouts: 5 · out_tok: 5129 · reason_tok: 160 · wall_sum: 337s

## Dispositions applied 2026-10-30T03:36:53+00:00

- resolved: 1
- deleted: 0
- manual: 3
- kept: 1
  - MOOT → `/Users/alien/.claude/steward-proposals/2026-09-01-scope-bound-recompute-heads.md`
  - MANUAL (ref missing on disk) `/Users/alien/Projects/substrate/HUMAN.md:92` — 🟢 2026-06-29 ~08:05 — dogfood epoch complete: 2 VERIFIED "KG-worse" cases found 
  - MANUAL (ref missing on disk) `/Users/alien/Projects/substrate/HUMAN.md:154` — 2026-06-29 ~00:30 — overnight autonomous run (you went to bed; codex paused for 
  - MANUAL (ref missing on disk) `/Users/alien/Projects/substrate/HUMAN.md:224` — 🌙 2026-06-28 (autonomous KG-build /goal — Front 1 META done; GRIND needs you)
