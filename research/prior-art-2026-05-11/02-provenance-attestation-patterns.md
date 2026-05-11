# Provenance & Attestation Patterns for ML/Data Pipelines — Fit Assessment for `annotations.jsonl`

**Date:** 2026-05-11
**Question:** Does our hand-rolled `annotations.jsonl` schema reinvent an already-standardized pattern? If yes, which one?
**Use case:** Per-source append-only JSONL recording "agent/model/human processed source S with prompt/config C at time T producing output O (URI+hash), with idempotency key K and supersession chain SC." Single-user, local filesystem, projected into DuckDB for queries.

---

## TL;DR

**Stay bespoke, but borrow the field vocabulary from RO-Crate Process Run Crate.** None of the surveyed standards is a clean fit:

- **RO-Crate Process Run Crate** comes closest to the *semantics* (agent + input + instrument + result + endTime is exactly our model), but its JSON-LD packaging assumes a per-output crate directory, not a per-source append-only event log. Its `@context` adds ~150 bytes per entry of pure ceremony for a single-user system that will never federate.
- **OpenLineage** is the right *architecture* (small JSON events written to a file transport, ~300 bytes minimum) but its data model is `Job` → `Run` → `Dataset` — a pipeline-orchestration mental model. A model annotating a source isn't a "Job"; it's an assertion. The required `eventType` (START/COMPLETE) and runId/UUID don't match append-once semantics.
- **W3C PROV-O** is the abstract foundation everyone else maps to. Adoption in raw form (Turtle/RDF) is rare; in practice it appears as RO-Crate or as a schema in domain-specific extensions. Implementing PROV-O directly for a single-user system is the canonical academic over-engineering trap.
- **SLSA/in-toto** is for software supply chain artifacts. Zero ML-specific predicates registered as of 2026-05. Wrong domain — applying it to ML annotations means inventing a new predicate type and writing a spec, not adopting one.
- **OpenTelemetry GenAI** is the converging *agent observability* standard (Dec 2025 AAIF founding adds momentum) but is fundamentally a **tracing layer** — spans live in tracing backends, not on-disk per-source. No supersession, no asserted_at vs recorded_at, no hash-keyed outputs.
- **DVC** versions files, not records about files. Wrong layer.

The honest recommendation: **keep the JSONL design, but rename fields to align with RO-Crate Process Run Crate vocabulary (`agent`, `instrument`, `object`, `result`, `endTime`).** This costs nothing and buys an exit ramp if you ever need to export to a standards-compliant crate. Don't adopt the JSON-LD `@context`/`@graph` wrapper — that's tax with no current return.

What the bespoke design legitimately gets right that no standard captures: **(a) per-source append-only with `recorded_at` ≠ `asserted_at`, (b) idempotency key for deduplication on replay, (c) supersession chain as a first-class field rather than a derived graph property.** These are not academic; they are workflow needs that the standards punt to convention.

---

## Standard-by-standard fit assessment

### 1. W3C PROV-DM / PROV-O — the abstract foundation
**Verdict: don't adopt directly.** PROV provides the conceptual triple `Entity ← Activity ← Agent` with `wasGeneratedBy`, `wasDerivedFrom`, `used`, `wasAssociatedWith`. Every downstream standard (RO-Crate, the Information Systems 2025 ML-provenance paper, the Common Provenance Model BY-COVID profile) maps to it. But raw PROV-O is RDF/Turtle/SPARQL, and the literature treats it as a *reference model*, not a wire format. Soiland-Reyes et al. (2024, PLOS ONE) and the Information Systems 2025 paper both explicitly map their JSON-LD schemas *to* PROV-O via SKOS — meaning the practitioners themselves stopped at "compliant by mapping," not "implement PROV directly." For a single-user JSONL pipeline, this would mean writing Turtle, running a triple store, and querying with SPARQL. Order of magnitude more infrastructure than DuckDB-on-JSONL, and zero query advantage at our scale.

### 2. RO-Crate (1.2) + Workflow Run Crate profiles — the closest fit
**Verdict: borrow the vocabulary; don't adopt the packaging.** The Process Run Crate profile (lightest of three: Process Run / Workflow Run / Provenance Run) requires:
- `CreateAction` with `instrument` (the tool/model/agent), `object` (inputs), `result` (outputs), `endTime`
- `SoftwareApplication` for the tool, `Person` for the human agent
- Root `Dataset` with `conformsTo` pointing at the profile URI

This *is* our schema, with different names: our `processor_id` → `agent`/`instrument`, our `inputs[]` → `object`, our `output_uri` → `result`, our `asserted_at` → `endTime`. The minimal valid Process Run Crate entry is ~300-400 bytes including the `@context` ceremony. We could literally adopt the field names with zero structural change.

The packaging assumption is the catch. RO-Crate's mental model is "a crate is a folder, containing files and a `ro-crate-metadata.json` describing them." It's designed for *handoff* — publishing a reproducible bundle for archiving (Zenodo, WorkflowHub). It's not designed for append-only per-source event logs. Galaxy, COMPSs, StreamFlow, WfExS, Sapporo, Autosubmit, and nf-core all emit RO-Crates *at the end of a workflow run*, as a wrap-up artifact. None of them stream incremental events to a per-source JSONL.

Adopting RO-Crate as-is for our case would mean: one crate per source (millions of folders), or one giant aggregate crate that has to be rewritten on every append (kills append-only). Both are pathological.

**What to borrow:** Rename fields to match `agent`, `instrument`, `object`, `result`, `endTime`. Document the mapping. If you ever need to export to a real crate, you write a transform, not a refactor.

### 3. OpenLineage — right shape, wrong noun
**Verdict: structurally close, semantically off.** The OpenLineage `RunEvent` is ~5 fields and ~300 bytes minimum (eventType, eventTime, run.runId UUID, job.namespace, job.name, producer). It has a `file` transport for local JSONL emission (config: `transport: {type: file, log_file_path: ...}`) and a `console` transport. It's the only surveyed standard explicitly designed around small JSON events written to local files.

The mismatch is the data model. OpenLineage thinks in:
- **Job** = a stable, versioned recipe ("run nightly ETL for table X")
- **Run** = one execution of that Job (UUID-keyed)
- **Dataset** = input or output table/file

A model annotating a source isn't a "Job" — it's an assertion about that source. The `eventType` enum (START / RUNNING / COMPLETE / ABORT / FAIL / OTHER) presumes a lifecycle that doesn't apply to a one-shot annotation record. The UUID-keyed runId presumes ephemeral execution identity; our idempotency keys are content-derived and meant to *prevent* recording duplicate work.

Could you shoehorn an annotation as `Job=model-id, Run=hash(prompt+source), Dataset[input]=source, Dataset[output]=output, eventType=COMPLETE`? Yes. Would it be clearer than a flat record with the names we already use? No. OpenLineage is built for pipeline orchestrators (Airflow, dbt, Spark, Flink) emitting events to a lineage backend (Marquez, DataHub, Atlan); using it for a personal corpus is a category error.

**What's worth knowing:** OpenLineage is the *de facto* enterprise standard for pipeline lineage in 2026 (per OvalEdge's 2025 survey: dominant in Gartner's data governance MQ). If we ever need to interoperate with an enterprise pipeline, we emit OpenLineage events as a translation layer. We don't store them.

### 4. SLSA + in-toto — wrong domain
**Verdict: not applicable.** SLSA provenance is explicitly for *software build artifacts*: `buildDefinition` (buildType, externalParameters, resolvedDependencies) + `runDetails` (builder, metadata). The in-toto attestation envelope (`_type`, `subject`, `predicateType`, `predicate`) wraps SLSA provenance, SPDX/CycloneDX SBOMs, vulnerability scans, test results — none of which describe an ML annotation.

Vetted predicates in the in-toto spec as of 2026-05: SLSA Provenance, CycloneDX, SPDX2/3, VULNS, Link, Test Result, Release, Runtime Traces, Simple Verification Result, SLSA VSA. **Zero ML-specific predicates.** Using in-toto for our case would mean inventing a new predicate type, drafting a spec, getting it vetted — work that benefits the world but not us at one user.

DSSE signing is technically optional (the `signatures: []` array can be empty), so we could adopt the *envelope* (`payloadType`/`payload`/`signatures`). But the envelope buys us nothing except an extra layer of base64-encoded JSON. Single-user, no signing requirement, no attestation chain to verify — the envelope is performative.

### 5. Sigstore / cosign — overkill
**Verdict: not relevant.** Sigstore solves "I don't want to manage long-lived keys, give me ephemeral OIDC-issued signing." For a single user with no signature verification consumers, this is solving a non-problem. If we later publish a derived corpus and want signed manifests, sigstore is the right tool. Until then, it's noise.

### 6. OpenTelemetry GenAI semantic conventions — adjacent but different layer
**Verdict: not a substitute; potentially complementary.** OTel GenAI defines `invoke_agent` and `execute_tool` spans with attributes like `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.tool.call.arguments/result`. The Linux Foundation's Agentic AI Foundation (AAIF, founded Dec 9, 2025, with MCP/goose/AGENTS.md as founding projects) is consolidating governance. LangChain's 2025 State of Agent Engineering survey: 62% of production agent teams have detailed step-level tracing; OpenLLMetry (Traceloop) is the de facto auto-instrumentation library covering 14 LLM providers and 8 frameworks.

**Why it doesn't fit our case:** OTel is a *tracing layer*. Spans are emitted to a collector (OTLP), forwarded to a backend (Jaeger, Tempo, LangSmith, Honeycomb), and queried by trace ID. They are *transient runtime events*, not *persistent assertions*. Required fields like `gen_ai.usage.input_tokens` make no sense for human-authored annotations. There is no concept in OTel of `asserted_at ≠ recorded_at`, no idempotency key, no supersession chain. Adding these would mean inventing custom attributes — at which point we've reinvented a flat schema with extra steps.

**Complementary use:** If we instrument the *creation* of an annotation (the live model call that produces it), OTel GenAI spans are the right tool. The annotation record itself is downstream — it's what survives after the span is shipped. The annotation is the *truth*; the span is the *transcript*.

### 7. MLflow / DataHub / Marquez — wrong scale
**Verdict: heavy, multi-user, server-required.** All three are server-backed metadata catalogs designed for ML teams with shared infrastructure. MLflow tracks experiments (run params, metrics, artifacts) keyed by experiment ID; DataHub is a metadata platform; Marquez is the OpenLineage reference backend. Adoption for a single user means standing up Postgres + a service for queries that DuckDB-on-JSONL handles in 10ms. Maintenance burden >> value at 1 user.

### 8. DVC — wrong layer
**Verdict: solves a different problem.** DVC versions large files (datasets, models) by content hash and stores them in remote object storage. It's git-for-data. It does not record "agent processed source with prompt." Our annotations could describe a DVC-tracked source's hash, but DVC itself doesn't capture the annotation. Acquired by lakeFS in Nov 2025 (now in maintenance mode-ish); not the right ladder to climb.

### 9. RO-Crate vs Bioschemas vs JSON-LD/schema.org — same family
**Verdict: covered under RO-Crate.** Bioschemas is a schema.org profile for life sciences; RO-Crate already incorporates Bioschemas extensions in Workflow Run Crate. Vanilla JSON-LD/schema.org/CreativeWork is too generic — without a profile (which is what RO-Crate is), there's no shared vocabulary for "Action" lineage. If you want JSON-LD, you want RO-Crate.

### 10. Information Systems 2025 paper (Werder et al., "Capturing end-to-end provenance for machine learning pipelines")
**Verdict: validates the bespoke approach.** This recent (2025) academic paper extends PROV-O specifically because PROV-O wasn't enough for ML pipelines. They added concepts the standards don't have. They map back to PROV-O via SKOS as a courtesy. This is exactly the pattern I'm recommending: **own the schema, document the mapping**, don't surrender to a standard that doesn't cover your needs.

---

## If we adopt one, which one? (Or: why none)

**Recommendation: keep `annotations.jsonl` bespoke, with RO-Crate Process Run Crate as the *naming* anchor.**

Concretely:
| Current field | RO-Crate Process Run Crate equivalent | Action |
|---------------|---------------------------------------|--------|
| `processor_id` / `model` | `instrument` (SoftwareApplication) or `agent` (Person) | Rename to `agent` for human, `instrument` for tool/model — disambiguates |
| `inputs[]` / source URI | `object[]` | Rename |
| `output_uri` + `output_hash` | `result` (could nest URI + hash) | Rename `output_uri` → `result.uri`, `output_hash` → `result.hash` |
| `asserted_at` | `endTime` | Keep both; `endTime` is RO-Crate's name for the same field |
| `recorded_at` | (none — no analogue) | Keep as bespoke field; document why |
| `prompt` / `config` | (no direct analogue; RO-Crate uses `parameter` entities) | Keep flat; RO-Crate's structural overhead isn't worth it |
| `idempotency_key` | (none) | Keep as bespoke field |
| `supersedes[]` / `superseded_by` | Could map to PROV `wasRevisionOf` | Keep flat; flat is faster for DuckDB |

**Why this is not a cop-out:** The honest situation is that scientific-corpus provenance for a single user is a niche the standards never targeted. RO-Crate aims at FAIR archive handoff. OpenLineage aims at enterprise pipeline observability. OTel GenAI aims at agent debugging. None aimed at "I run a personal scientific corpus and want to record every model run reversibly on local disk." Picking one and contorting our use case to fit it would cost more in cognitive overhead than it would save in interop.

**What changes if you ever need to publish:** Write a Python script that maps `annotations.jsonl` → a Process Run Crate. ~50 lines. The aligned vocabulary makes it trivial.

---

## What our schema gets right vs. wrong relative to convergent practice

### Right
- **Append-only JSONL**: aligns with how OpenLineage emits events (`file` transport writes JSONL). The wire convention "one JSON event per line" is the convergent practice across observability standards.
- **Hash-keyed outputs**: in-toto's `subject` is identified by `digest`, RO-Crate uses `contentSize`/`sha256` properties, OpenLineage `Dataset` facets include hash. Universal practice.
- **Distinguishing agents (human vs model vs service)**: matches RO-Crate's `Person` / `SoftwareApplication` / `Organization` distinction at the type level.
- **Timestamps**: ISO 8601 strings are universal.
- **Local-first**: matches the AAIF founding ethos (goose is "local-first"), matches OpenLineage's file transport, matches the AGENTS.md convention. Not a standards violation.

### Wrong (or weakly conventional)
- **Flat structure**: every standard nests (RO-Crate: graph of entities; OpenLineage: nested facets; OTel: span attributes namespaced). Flat is faster to write/query but loses the implicit grouping. Mitigation: keep flat but namespace keys (`agent.id`, `result.uri`, `result.hash`) — this is the OTel pattern.
- **No JSON-LD `@context`**: every standards-aligned format includes a `@context` pointing at a vocab URL. Adding one to each annotation costs ~80 bytes and zero behavior change today, but it gives consumers (including future-you) a stable referent for what `agent` means.
- **Idempotency key is bespoke**: no standard models this. It's a legitimate workflow need — but worth documenting *why* (replay safety, dedup on resume) so future agents don't think it's a missing standard term.
- **`asserted_at` vs `recorded_at` split**: no standard captures this. It's legitimate (model says output is "as of T1", you record at T2). Worth documenting; could map to PROV's `invalidatedAtTime` for the inverse but no clean analogue exists.
- **Supersession chain as field rather than derived**: PROV models this as `wasRevisionOf`/`wasDerivedFrom` edges in a graph. We materialize as a direct field for query speed. Defensible at small scale; document the trade-off.

### What we don't have but should add
- **`conformsTo` field per record**: even if pointing at a local schema doc. This is the single cheapest way to declare "this is our schema version" — RO-Crate uses it, OpenLineage uses `producer` URI similarly. Two-line addition.
- **Stable agent IDs**: not free-text "claude-opus-4-7" but a URI like `https://anthropic.com/models/claude-opus-4-7`. This makes joining across the corpus mechanical when models get renamed.

---

## What I'd say if asked "is the bespoke design wrong?"

It's not wrong. It's appropriately scoped. The fast-cycle observation: **every standard surveyed was built for a multi-party trust scenario** (publish to archive, prove build provenance, federate across enterprise teams, debug shared agents). At one user with local storage and append-only writes, most of the ceremony of those standards is paying for trust assumptions that don't apply.

The trap to avoid is the opposite — assuming bespoke means *idiosyncratic*. Aligning field *names* with RO-Crate Process Run Crate vocabulary is free, makes the schema legible to anyone familiar with the standards, and preserves a clean exit ramp. Refusing to do that just because "we're bespoke" is exactly the kind of NIH that ages badly.

The harder question, not asked but worth flagging: **if you scale this corpus to multi-agent collaborative use, the right move is to emit OpenLineage events alongside the `annotations.jsonl` writes** — same data, different shape, lets enterprise tooling consume it. That's a future-build decision, not a today-build one.

---

## Sources

- Soiland-Reyes, S., et al. (2024). Recording provenance of workflow runs with RO-Crate. *PLOS ONE*. https://doi.org/10.1371/journal.pone.0309210
- Soiland-Reyes, S., Sefton, P., Castro, L. J., Coppens, F., Garijo, D., Leo, S., Portier, M., & Groth, P. (2022). Creating lightweight FAIR Digital Objects with RO-Crate. *Research Ideas and Outcomes*. https://doi.org/10.3897/rio.8.e93937
- Werder et al. (2025). Capturing end-to-end provenance for machine learning pipelines. *Information Systems*, 128, 102492. https://doi.org/10.1016/j.is.2024.102492 [PROV-O extension for ML; maps to RO-Crate via SKOS]
- RO-Crate 1.2 specification — https://www.researchobject.org/ro-crate/specification.html
- Workflow Run RO-Crate Process Run Profile — https://www.researchobject.org/workflow-run-crate/profiles/0.5/process_run_crate
- OpenLineage Object Model — https://openlineage.io/docs/spec/object-model/ (Run/Job/Dataset; file transport supports JSONL)
- OpenLineage Python Client — https://openlineage.io/docs/1.38.0/client/python/ (ConsoleTransport, FileTransport)
- SLSA Provenance v1.0 — https://slsa.dev/spec/v1.0/provenance (software-build scope; no ML predicates)
- in-toto Attestation v1 — https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md (DSSE optional; zero ML predicates as of 2026-05)
- in-toto vetted predicates — https://github.com/in-toto/attestation/tree/main/spec/predicates
- OpenTelemetry GenAI Semantic Conventions — https://opentelemetry.io/docs/specs/semconv/gen-ai/ (invoke_agent, execute_tool spans; tracing layer, not persistence)
- Linux Foundation Agentic AI Foundation announcement — https://aaif.io/ (Dec 9, 2025; MCP/goose/AGENTS.md founding projects)
- OvalEdge (2025). 12 Open Source AI Data Lineage Tools — OpenLineage + Marquez ecosystem state. https://www.ovaledge.com/blog/ai-powered-open-source-data-lineage-tools
- Hugging Face Model/Dataset Cards documentation — https://huggingface.co/docs/hub/en/model-cards (descriptive YAML/README, not per-run provenance)
- BY-COVID Common Provenance Model RO-Crate profile — https://by-covid.github.io/cpm-ro-crate/ (PROV → RO-Crate mapping)
- nf-core ROCrate documentation — https://nf-co.re/docs/nf-core-tools/pipelines/rocrate (workflow-end emission pattern, not streaming)

<!-- knowledge-index
generated: 2026-05-11T07:26:24Z
hash: 3c5c2d6726b0


end-knowledge-index -->
