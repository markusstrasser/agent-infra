# Knowledge Futures / Underlay autopsy, and whether phenome's KG generalizes beyond biomedicine

**Date:** 2026-06-08
**Author:** agent-infra session (Markus-prompted)
**Status:** research memo — no architecture change proposed; confirmatory of existing scoping vetoes
**Scope:** (1) why Knowledge Futures / the Underlay never achieved broad impact; (2) whether any of their ideas beat the phenome KG; (3) whether phenome's KG architecture is domain-general (chemistry / physics / biophysics) and where it would have to change.

---

## TL;DR

1. **Knowledge Futures didn't fail — its *knowledge graph* did.** PubPub (the publishing platform) got real adoption and survives; the Underlay (the distributed public KG) was quietly abandoned ~2022–2023, years before the 2025 funding crisis. It died of the textbook open-KG failure mode: protocol-first, no consumption loop, decentralization tax, out-competed by centralized Wikidata/Google. The org itself nearly died in 2025 from single-funder dependency, then stabilized in 2026 by driving cost/maintenance toward zero.

2. **No idea in their stack should be ported into phenome.** Phenome's KG is *operationally far ahead* of anything the Underlay actually shipped (byte-level evidence verification, append-only certificate ledger, working cross-repo consumer vs. archived prototypes). The single piece of genuine intellectual depth they had — the **algebraic / functorial schema** (`underlay/apg`, `underlay/tasl`) — is better as theory, worse as fit, and earns its weight only in one deferred scenario (the S4 base⊕overlay fusion), as reading-material, not a dependency.

3. **Phenome's *substrate* is domain-general and arguably best-in-class for its regime; its *predicate/ontology/linking layer* is biomedically bound.** The substrate (content-addressed append-only assertion+evidence ledger, contradiction-preserving, **agent-populated, single-curator, consumer-coupled**) structurally sidesteps the crowdsourcing/adoption bottleneck that kills nanopublications, ORKG, and the Underlay. But to reach chemistry it must add **n-ary reaction/process records** (binary assertions don't model reactions), and to reach physics it must add a **first-class quantitative-value-with-uncertainty type** — which phenome *explicitly does not have today* (its grades are evidence weights, "NOT probability"). Biophysics is the natural first extension; physics is the hardest.

---

## 1. Knowledge Futures / Underlay — autopsy

### What it was
Boston 501(c)(3), spun out of **MIT Media Lab + MIT Press (2018)** as the Knowledge Futures Group; incorporated independently 2019–2020. Two flagships:
- **PubPub** — open-source academic publishing platform (thousands of journals/books; the thing people actually used).
- **The Underlay** — "a global, distributed graph of public knowledge," explicitly pitched as a public, decentralized counter to private KGs (Google Knowledge Graph, Scopus, Wolfram, Apple's Siri KG). Provenance-native data model, IPFS content-addressing, federated nodes at universities, "overlays" as curated interpretive lenses.

### Why the KG never got anywhere
The Underlay was **abandoned ~2022–2023, separate from and earlier than the 2025 org crisis**:
- `underlay` GitHub org is dormant — core repos (`apg`, `tasl`, `overview`, `percolate`, `n3.ts`) last touched 2021–2023, many **archived**; `underlay.org` itself is now an archived repo.
- It was prominent in the 2020 and 2022 annual reports (Apple Siri KG partnership, Sloan-funded "Innovation Information Initiative" on patents/citations, Pine Wu building an alpha for "end of 2022"), then **vanishes from reporting**.
- The **current knowledgefutures.org homepage does not mention the Underlay or knowledge graphs at all** — only PubPub and PubPlatform.

Structural causes (these recur across *every* public-KG attempt — see §3):
- **Protocol-first / solution-in-search-of-users.** Led with ARC/Assertion/Collection protocols + R1 registry rather than a population with a felt pain. Protocols "expected to have a finite lifetime" — architecture as the product.
- **Cold-start × decentralization tax.** IPFS + multi-institution federation + provenance chains is enormous engineering for benefits (censorship-resistance, no single owner) early users don't value. A public KG is worthless until populated; nobody populates infra with no users.
- **Centralized competitors won.** Wikidata ate the open-public-KG niche pragmatically; Google/Apple owned the private side. "Distributed + provenance-native" was a researcher's value, not a user's.

### Why the org nearly died (different failure)
- **2025-06** — a critical funder withdrew the promised second half of a grant after a year of moving goalposts. KF announced wind-down: sunset PubPub Legacy (extended to **2026-12-31**), pause hosted Platform, lay off staff. Notably: revenue was *working* (they exceeded H1-2025 targets, signed custom-build contracts). Killed by **single-funder dependency**, not lack of demand. Their own line: *"there is nowhere else to go."*
- **2026-01** — "A Path Forward." An infrastructure refactor cut server cost/maintenance enough that a modest **PubPub Sustainability Fund** keeps it online "indefinitely." Migration to the new Platform **no longer required**; **PubPub** (turn-key hosted site builder) and **PubPlatform** (`github.com/pubpub/platform`, GPL-2.0, ~78★, alpha) formally split into independent paths.
- **2026-04** — infra transition complete; co-founder **Travis Rich returned as Executive Director**; Jeff Pooley joined the board. Net: alive, much smaller, stabilized.

**Org-level lesson:** survivability came from driving *ongoing drag* (server cost, maintenance, supervision) toward zero — the organizational-scale version of "filter by maintenance, not effort."

---

## 2. Are any of their ideas better than the phenome KG?

**No — with one genuine exception that is nonetheless the wrong fit.**

Phenome's KG (mapped from source 2026-06-08: `~/Projects/phenome`, `~/Projects/genome-toolkit/packages/claimcore`) is a **correctness-maximal, append-only relational system on DuckDB** — not a semantic graph DB. It already has, *shipped and consumed*, everything the Underlay merely *claimed*:

| Underlay claim | Phenome reality |
|---|---|
| content-addressed | `span_hash`, `content_sha256`, deterministic `identity_key` across rebuilds |
| provenance-native | byte-level verbatim evidence spans + `upstream_checks` (verifies quoted text is byte-equal to source) + extraction prompt SHA |
| contradiction handling | `contradiction_pairs` + GA4GH direction-safety (benign/refuted edges *kept and marked*, not hidden) |
| append-only belief | `claim_closure_certificates` + `claim_certificate_events` + diagnostic event log with compensation (retract/correct) |
| overlays (curated lenses) | query-time composition (source groups, tiers, recomputed support links) — grounded in a real consumer |

The Underlay had vision docs and archived prototypes; phenome has **315K+ live assertions** with working certs and a cross-repo consumer (the genomics bridge). The accurate framing is the *inverse* of the question: **phenome is what the Underlay wanted to be, scoped to one owner with a real consumer instead of a decentralized public-good protocol with none.**

### The one transferable idea: algebraic / functorial schema (`apg` + `tasl`)
The Underlay's real intellectual asset was **Algebraic Property Graphs** (`underlay/apg`) and **tasl, "the algebraic schema language"** — a category-theoretic foundation where schema mappings are functors and data migration/merge carries formal composition guarantees (functorial-data-migration tradition).

- As CS: unambiguously deeper than phenome's hand-rolled DuckDB schema + 56-predicate registry.
- As fit for phenome: **almost certainly over-engineering** — phenome controls its own schema, operates at DuckDB-trivial scale, and already gets the practical payoff (stable identity across rebuilds) from content hashing. Adopting it is exactly the "architecture as the product" pathology that left those repos archived, and it's cousin to the knowledge-substrate MCP and PageRank-symbol-graph this repo already vetoed.
- **The one place it could matter:** the deferred **S4 base⊕overlay fusion** (science base ⊕ personal/genomics overlay). *If* that fusion ever becomes formally hairy — conflicting schemas, non-obvious merge semantics, needing a provable "the overlay didn't corrupt the base" — functorial data migration is the prior-art to read before hand-rolling it. **Consult-if, not adopt.**

Everything else they conceived (federation/IPFS, datasets-as-social-objects, provenance-to-expose-bias) phenome either does better or correctly doesn't need (single-owner ⇒ no multi-contributor trust layer; decentralization ⇒ the exact cost that killed the Underlay).

---

## 3. Could phenome be better, and does it generalize? (the new research)

I surveyed the closest prior art to phenome's design — the systems that tried to be a "knowledge graph of science" — and the domain schemas chemistry/physics actually use.

### 3a. The cross-cutting finding: substrate is easy, *population* is what kills these

Every general scientific-KG effort dies on adoption, not data model:
- **Nanopublications** (Groth/Gibson/Velterop 2010) — the closest analogue to phenome's assertion+provenance model (RDF named graphs: assertion / provenance / pub-info). **10M+ published**, yet "still not widely used by scientists outside specific circles; they are hard to find and rarely cited" (NanoWeb, PMID 33816986). A 2023 field study concluded "genuine semantic publishing remains a vision … little practical evidence as of now" (PMC10280262).
- **ORKG** (TIB Hannover, Auer et al.) — explicitly needs **crowdsourcing à la OpenStreetMap** and confronts the "knowledge acquisition bottleneck"; founder concedes automated extraction tops out at "50–60% precision, which does not help" and that it "will not work with … a team of ten people, but only if thousands or millions work together."
- **The Underlay** — §1, same disease.

**Phenome inverts this and that is its structural moat.** It is **single-curator, agent-populated** (LLM extraction with byte-level verification gates), with a **real consumer** (Markus's own health/genomics). There is no crowd to mobilize, no incentive problem, no "why would a scientist hand-author RDF." For the **single-operator / agent-populated / consumer-coupled** regime, phenome's substrate is arguably *best-in-class* — better than nanopub/ORKG precisely because it doesn't depend on the thing they all failed at. This is the same bet as the 2026 **"Knows: Agent-Native Structured Research Representations"** preprint (arXiv:2604.17309), which independently argues nanopub/ORKG "adoption has remained limited … because RDF authoring is costly," and proposes an agent-native claim-DAG + provenance + freshness + version-chain spec — i.e. *someone is already building the generalized agent-native version of phenome's philosophy.* Worth tracking as the nearest parallel/competitor.

### 3b. What's domain-general vs. biomedically bound in phenome

**Domain-general (the substrate — port as-is):**
- content-addressed identity (span hash, identity key)
- append-only assertion + evidence-span ledger with byte-level source verification
- contradiction preservation + diagnostic state axes (provisional→supported→refuted)
- certificate ledger + compensation events
- mutation gateway / transactional outbox / sole-writer boundary
- evidence tiers (SOURCE / DATABASE / INFERENCE / TRAINING / SELF-OBS)

**Biomedically bound (must be swapped/extended per domain):**
- the 56 predicates / 9 families (PK, PD, molecular, clinical…) — biomedical
- ontology grounding (HPO, MONDO, RxNorm, HGNC, ClinVar, CPIC, UMLS)
- **HP subsumption (IS-A closure) as the linking metric** (exact=1.0 / subclass=0.9 / superclass=0.6) — this is phenotype-graph-specific and does *not* transfer

### 3c. Two capability gaps that block physics/chemistry (and would help biomedicine too)

These are the genuine "could phenome be better" findings:

1. **No first-class quantitative-value-with-uncertainty type.** Phenome explicitly treats grades as *evidence weight, "NOT probability."* But in physics/metrology the **claim *is* a number with a unit and an uncertainty distribution**. There are mature ontologies for exactly this — **QUDT** (Quantity/Unit/Dimension/Type, v3.2 2026), **PTB's SIS / D-SI** (value + kind + unit + univariate/multivariate uncertainty + coverage interval, BIPM/GUM-conformant), and **OM 2.0**. Phenome has none of this as a primitive. *This gap also bites biomedicine*: lab values, PRS, effect sizes, binding affinities are all value-unit-uncertainty triples currently flattened into prose/grades. **Highest-value upgrade, domain-independent.**

2. **No n-ary / process (reaction) representation.** Phenome's model is entity↔entity assertions (binary-ish). A chemical reaction is irreducibly **n-ary and structured** — the **Open Reaction Database** schema (Kearnes et al. 2021) is a 10-field `Reaction` record (inputs / setup / conditions / observations / workups / outcomes / provenance…), implemented in Protocol Buffers *specifically because RDF triples model it poorly*. Same shape applies to pathways, experimental protocols, multi-arg physical setups. Generalizing phenome to processes needs reified/n-ary records, not more binary predicates. (Phenome's contradiction+support model is actually *ahead* of standard nanopublications on multi-source evidence — cf. the 2025 PROV-K "knowledge provenance" extension that bolts conflicting-evidence aggregation onto nanopubs, something phenome already has natively.)

### 3d. Domain-by-domain generalizability verdict

| Domain | Fit of phenome substrate | What it gains for free | What it must add |
|---|---|---|---|
| **Biomedicine** (current) | native | — | (quant-value type would still help) |
| **Chemistry** | strong | **free content-addressing**: InChIKey / canonical SMILES / InChI are *already* canonical molecular hashes (ORD uses them) — phenome's content-addressing generalizes beautifully; swap ontology to ChEBI/PubChem CID | **n-ary reaction records** (ORD-style); quant-value type for yields/conditions |
| **Biophysics** | strong (natural first extension) | shares molecular entities; **PDB IDs / sequences as content-addresses**; binding affinities = value-unit-uncertainty | quant-value-with-uncertainty type; some n-ary (complexes, MD runs) |
| **Physics** | substrate yes, model no | append-only provenance ledger still valuable | **quant-value-with-uncertainty as the *primary* claim type** (SIS/QUDT); **derivation/computation provenance** (claim = output of a derivation/simulation, not a literature span); the entity-relation model becomes secondary to the measurement model |

**Ordering:** biomedicine → biophysics → chemistry → physics, by increasing distance from phenome's current model. The substrate carries all the way; the **predicate+linking layer is replaced per domain**, and **two new primitive types (quantitative value+uncertainty; n-ary process record)** unlock everything past biomedicine.

---

## 4. Recommendations

1. **Do not adopt anything from Knowledge Futures / the Underlay.** File the `apg`/`tasl` functorial-schema approach as **consult-if** prior art for the deferred S4 overlay-fusion problem only. (Reinforces, doesn't reopen, the standing substrate-MCP / symbol-graph vetoes.)
2. **If phenome generalization is ever on the table, the first real work is two domain-independent primitives**, in priority order:
   - (a) a **quantitative-value-with-uncertainty type** (model on QUDT + PTB SIS/D-SI) — pays off *inside* biomedicine immediately (labs, PRS, effect sizes), independent of any new domain.
   - (b) an **n-ary process/record type** (model on ORD's `Reaction` message) for reactions/pathways/protocols.
3. **Track "Knows" (arXiv:2604.17309)** as the nearest external parallel — agent-native structured research records are being standardized by others right now; it both validates phenome's bet and is the thing to evaluate-as-dependency before building a general version.
4. **The transferable *organizational* lesson from KF's near-death is already this repo's doctrine:** infrastructure survives by minimizing ongoing drag, not by maximizing capability. KF lived by driving maintenance→0; single-funder/single-dependency exposure is the killer.

---

## Sources

**Primary (org / project / schema docs):**
- Knowledge Futures updates: `knowledgefutures.org/updates/2025-06-update/` ("Not Enough: Open Infrastructure Funding," 2025-06-23, **A** — the funder-withdrawal autopsy in their own words); `/updates/2026-01-update/` ("A Path Forward," 2026-01-12); `/updates/` index (Travis Rich returns ED 2026-04-20; infra transition complete 2026-04-06).
- Underlay: `underlay.mit.edu`, `docs.underlay.org`, `github.com/underlay` (`apg`, `tasl` — both archived ~2022); annual reports `notes.knowledgefutures.org/pub/2020report`, `/annual-report-2022`.
- PubPub Platform: `github.com/pubpub/platform` (GPL-2.0, alpha); migration docs `help.knowledgefutures.org`.
- Open Reaction Database schema: `docs.open-reaction-database.org/en/latest/schema.html` + `/guides/compound_identifiers.html` (InChIKey/SMILES/InChI canonical identifiers).
- QUDT `qudt.org` (v3.2.1, 2026-04); PTB **SIS / D-SI** `ptb.de/sis` + scitepress 2025 paper; **OM 2.0** `github.com/HajoRijgersberg/OM`.
- Phenome KG architecture: `~/Projects/phenome` + `~/Projects/genome-toolkit/packages/claimcore` (direct read, 2026-06-08).

**Secondary (peer-reviewed / preprint):**
- Groth, Gibson & Velterop (2010), "The anatomy of a nanopublication," *Information Services and Use* 30(1-2). **A.**
- NanoWeb / life-science nanopublications, PMID 33816986. **A.**
- Nanopublication semantic-publishing field study, PMC10280262 (2023). **B.**
- Provenance-driven / PROV-K nanopublication extension, *Int. J. Digital Libraries* (2025), doi:10.1007/s00799-025-00431-x. **B** (multi-source/conflicting-evidence extension — phenome is already ahead here).
- ORKG requirements analysis, arXiv:2102.06021 (Auer/TIB); "Towards an ORKG," Auer 2018. **B.**
- Kearnes et al. (2021), "The Open Reaction Database," *JACS*. **A.**
- **"Knows: Agent-Native Structured Research Representations," arXiv:2604.17309 (2026)** — nearest parallel to a generalized phenome; agent-native claim-DAG + provenance + version chains; explicitly diagnoses nanopub/ORKG adoption failure as RDF-authoring cost. **B** (preprint; note: its own benchmark sidecars were Claude-Opus-authored → circular-eval caveat stated in-paper).

> Source-grade legend: **A** = primary or peer-reviewed, directly verified; **B** = peer-reviewed/preprint, claims as stated by authors. KF financial/internal claims are self-reported (their own blog) — graded A for "what KF says happened," not independently audited.
