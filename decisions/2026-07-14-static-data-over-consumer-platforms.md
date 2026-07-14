---
id: 2026-07-14-static-data-over-consumer-platforms
concept: static-data-consumer-boundary
repo: agent-infra
decision_date: 2026-07-14
recorded_date: 2026-07-14
provenance: contemporaneous
status: accepted
initial_leaning: Keep a pruned substrate with a thin genome toolkit and on-demand drift command.
relations:
  - type: supersedes
    target: 2026-05-26-cross-attestation-substrate-v2
---

# 2026-07-14: Static data replaces the genomics consumer platform

## Context

The fused public biomedical KG was killed on 2026-06-29/30 after a tooled frontier
agent tied or beat it on current public facts, buried paper facts, and bounded public
multi-hop queries. The surviving proposal retained an indexed genomics results
directory, a thin `genome-toolkit`, scheduled drift, and several shared packages in
`substrate`.

That remainder no longer matches the actual operating model:

- Genomics results are static until the operator explicitly runs `donor-sync`.
- Agents can read the result files directly; there is no automated consumer that
  requires a reader SDK or MCP.
- Phenome's apparent daily sync calls a script that no longer exists.
- `genome-toolkit` has no installed or external user and owns no unique capability.
- `substrate` groups unrelated packages by extraction history rather than by a
  coherent runtime, owner, or consumer boundary.

The requirement is radical simplification without losing scientific computation,
data, integrity checks, or question-answering power.

## Alternatives considered

1. **Prune but retain `substrate`.** Keep the umbrella around the surviving shared
   packages. This minimizes moves but preserves a false architectural boundary.
2. **Retain a thin toolkit and on-demand drift.** This keeps deterministic comparison,
   but two snapshots can differ only during explicit sync; comparison belongs in that
   transaction, not in a second stateful product.
3. **Retain `genomics-read` as a generated contract SDK.** Correct but uncalled after
   the phenome bridge is removed. The data manifest itself is the contract.
4. **Dissolve the umbrella but retain corpus attestation.** This preserves a coherent
   outbox design, yet current relation volume and decision usage do not justify the
   cross-repo writers, lints, daily drainer, and graph APIs.
5. **Split every package into its own repository.** Clean namespaces but more
   maintenance surfaces than semantic owners.
6. **Vendor every library into every caller.** Eliminates dependencies but introduces
   correctness drift for genuinely shared storage semantics.
7. **Static donor data plus owner-local code.** One explicit update event, one owner
   per retained capability, no consumer platform. This is the selected direction.

## Counterevidence sought

The leading option was initially a pruned substrate plus thin toolkit. We searched
for facts that would require preserving either boundary:

- A real toolkit user, installed skill/plugin, release, deployment, clone, or external
  collaborator. None was found; the private remote is behind the local checkout and
  recent traffic is zero.
- A functioning scheduled donor consumer. The phenome launchd job is loaded but its
  target script is absent.
- More than one semantic owner for each surviving package. `bio-reference` is
  phenome-only; `evalcore` belongs to evals; the full `plan-core` engine belongs to
  genomics; `corpus-testing` has no consumer; `genomics-read` has only the bridge that
  this decision removes.
- A reason to delete the paper corpus. Counterevidence was found: research-mcp uses it
  in the user-facing fetch flow and the corpus has more than 20,000 live sources.
  Therefore the paper store and its bytes must survive under research-mcp.
- A load-bearing use of cross-repo corpus relations. The current audit reports two
  active phenome relations and zero genomics relations. That does not justify the
  current architecture, but its data will be exported before retirement.

The search changes the proposal from “delete substrate wholesale” to “move the live
paper store and single-owner utilities first, then archive the emptied boundary.”

## Decision

The target architecture is:

```text
genomics producer -> immutable results/** + manifests -> direct agent reads
                                  ^
                         explicit donor-sync
```

1. **Genomics remains the producer and scientific authority.** Preserve stage
   computation, internal typed contracts, sample-canonical storage, publication
   authorization, complete byte manifests, and atomic recipient validation.
2. **The donor surface is data, not a product.** Results change only through explicit
   `donor-sync`. Any before/after comparison happens inside that command. Remove
   standing sync, drift state/cron, bundled skill/plugin, MCP, and separate toolkit.
3. **Phenome does not mirror genomics.** Delete the resync job, genomics-consumer MCP,
   bridge/parser/registry/report plane, `genomics-read`, and shadow genomic exports
   after a fact-level coverage gate prevents data loss.
4. **Useful single-owner code returns to its owner.** UMLS/RxNorm to phenome,
   `evalcore` to evals, full plan engine to genomics, and the paper store to
   research-mcp. Delete unused package code and fixtures.
5. **Retire cross-repo corpus attestation after preserving its evidence.** Drain all
   outboxes, export final annotations/relations/audit state, then remove gateway side
   effects, lints, daily audit/drainer, live outbox tables, and graph APIs. The active
   paper/source store remains untouched in place and gains one API owner.
6. **Delete `genome-toolkit`; park `substrate`.** Preserve `genome-toolkit` once as a
   verified cold git bundle, then delete its checkout and private remote. Keep the
   good `substrate` repository/history intact but frozen and disconnected from every
   active dependency. No compatibility shims or path aliases survive.

The executable migration and acceptance contract is
`.claude/plans/019f6268-static-data-simplification.md` (gitignored working plan).

## Evidence

- Substrate kill-switch: public fact currency 9/9; buried facts 12/12 with zero
  confabulation; bounded public multi-hop KG precision 92% with the agent comparable
  or better. The benchmark did not evaluate the utility packages, so package
  dispositions come from live consumer audits rather than benchmark extrapolation.
- `genome-toolkit`: private; no releases or deployments; zero recent views/clones;
  no installed plugin/skill; no unique asset after genomics donor-bundle work.
- Genomics detached donor candidate:
  `4200742fc72d6885fd8ec5546bad6f85ec657052`, not yet on main.
- Phenome genomics resync calls missing
  `/Users/alien/Projects/markus-genotype/sync.py`.
- Package-level caller audit across agent-infra, genomics, phenome, intel,
  research-mcp, evals, genome-toolkit, and substrate.
- Active corpus evidence: more than 20,000 sources and current paper-store writes;
  relation evidence: two active phenome relations and zero genomics relations in the
  current audit.

## Consequences

- Cross-domain genomic/phenomic questions remain possible, but the agent performs the
  join over two direct data sources rather than consuming a prebuilt bridge.
- Integrity moves to the only mutation boundary: producer publication and explicit
  donor-sync. Static reads require no runtime validation service.
- The corpus paper cache remains a first-class capability. Its low-use annotation
  substrate does not. The historical `substrate` code remains available but dormant.
- Execution is necessarily cross-repo and breaking. Each move must land only after a
  principal before/after test, and dirty peer work must remain untouched.

## Revisit if

- A named automated consumer cannot use the manifest-backed static result contract.
- A real scheduled source update makes proactive donor drift notification valuable.
- Cross-repo source overlap or annotation-driven decisions become measured production
  behavior rather than architectural possibility.
- A regulatory/audit requirement specifically needs persisted cross-repo attestation
  rather than the producer manifests and domain-local records.

## Supersedes

- `2026-06-30-genome-toolkit-thin-consumer-no-kg.md`: preserves direct typed-result
  reading and the producer, but drops the separate toolkit, skill/plugin, scheduled
  drift, and sync assumptions.
- `2026-05-26-cross-attestation-substrate-v2.md`: preserves the historical export and
  paper sources, but retires the live gateway/outbox/drainer architecture after final
  drain and archival capture.
