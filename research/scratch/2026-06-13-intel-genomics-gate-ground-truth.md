# Intel & Genomics Accept-Gate Probes: Consumption Ground Truth

## REPO 1: ~/Projects/intel

### 1. The "resolve-heartbeat" healthcheck

**What it checks:** Freshness of source-calibration resolve loop (tools/source_eval.py resolve). Detects deadlock in the weekly opinion-claim resolver.

**Where it's written:**
```python
# tools/source_eval.py — after successful resolve run:
hb = ROOT / "analysis" / "sources" / ".resolve_heartbeat"
hb.parent.mkdir(parents=True, exist_ok=True)
hb.write_text(datetime.now(timezone.utc).isoformat())
```

**What it emits (verbatim):**
From `.claude/hooks/pretool-tier1-pipeline-liveness-gate.py` line 128:
```python
f"resolve-loop heartbeat {rh_age_h / 24.0:.0f}d stale (>= {RESOLVE_LOOP_FAIL_DAYS}d) — loop is dead"
```

**CONSUMED or LOGGED:** **CONSUMED** — The gate `pretool-tier1-pipeline-liveness-gate.py` actively blocks file writes (exit 2):

- Lines 182-185: `if mode == "block" and hard: exit_block(...)` — **blocks when resolve heartbeat is >= 35d stale**
- Triggers on Tier-1 entity/research/theme writes; gate runs at pre-commit
- Consumer: any git commit attempting to assert a Tier-1 cross-domain claim

**Ledger path + tables:**
- State: `analysis/sources/.resolve_heartbeat` (single file, mtime only; gitignored)
- Claim ledger: `datasets/sources/claims.csv` (CSV, columns: claim_id, source_id, ticker, deadline, event_type, resolved)
- Verdict logs: `intel/indexed/theses.duckdb` → table `current_predictions` (rows: ticker, direction, resolved, resolution_type, resolver_spec)

**Bus/queues:** None identified; resolve loop is standalone weekly cron (tools/launchd/com.intel.source-quality-audit.plist runs weekly).

---

### 2. Ingestion & resolve loop

**Verifier:** `tools/source_eval.py` — `check_resolve_loop_liveness()` in tools/healthcheck.py (lines 517-602)
- Checks: heartbeat staleness + overdue price-resolvable claims (PRICE_TERMINAL/PRICE_TOUCH only; BINARY_EVENT excluded)
- Outputs: FAIL if worst overdue > 35d; WARN if heartbeat 8-35d stale or any overdue
- Consumed by: healthcheck CLI exit code (but not by downstream pipeline until the gate wraps it)

---

### 3. Intel's state/ledger

- **SQLite DB:** None. intel uses **DuckDB** (`intel/indexed/theses.duckdb`, `intel.duckdb` for prices/daily_returns/etc.)
- **Main corpus:** `intel.duckdb` (path: `tools/lib/db.DB_PATH`, see line 21 tools/healthcheck.py)
- **Key tables:**
  - `current_predictions` (ticker, direction, resolved, resolution_type)
  - `prices`, `daily_returns` (from CSVs)
  - `sec_form4`, `house_ptr_trades`, `senate_ptr_trades` (entity graph data)
  - `entity_edges`, `entities` (the research graph)

---

### 4. The bus

- **Flag files:** `.claude/shadow_log/pipeline_liveness_*.jsonl` (if mode=shadow; gitignored)
- **Beacon files (retired 2026-06-07):** `analysis/daily.{success,critical_failure}` (OLD; replaced by `data_plane_live()` physical probe)
- **No message queue identified**

---

### 5. The ~5 live agents

Identified processes/loops in intel (from launchd):
1. **com.intel.source-quality-audit** (weekly Mon 11:00 UTC)
   - `tools/build_source_correlation_matrix.py` → `tools/source_quality_audit.py` → `tools/resolvers/price.py`
   - Runs the resolve-heartbeat write

2. (Others not explicitly visible; likely daily_update.sh + ad-hoc research runs)

---

## REPO 2: ~/Projects/genomics

### 1. The "canary_gate" (70 sentinels)

**What it checks:** Regression test on 70 curated variants against `auto_classify()` output (label, confidence, reportability). Catches silent classification drift.

**Where it runs:** Pre-commit hook, `scripts/canary_gate.py` (lines 105-176)
```python
def run_canary_gate() -> int:
    with open(CANARY_FILE) as f:
        data = json.load(f)
    variants = data["variants"]
    ...
    if label_ok and confidence_ok and reportability_ok:
        n_pass += 1
    else:
        n_fail += 1
        failures.append(...)
    print(f"Canary gate: {n_pass}/{total} passed")
    return 1 if failures else 0
```

**What it emits (verbatim):**
```python
# Line 159: f"Canary gate: {n_pass}/{total} passed"
# Line 162-165: if failures — prints each (vid, expected, got, reasons)
```

**CONSUMED or LOGGED:** **CONSUMED** — The hook `.claude/hooks/precommit-qa-gate.sh` **blocks on exit != 0**:

```bash
# Lines 57-68:
if uv run python3 "$REPO_ROOT/scripts/canary_gate.py" >"$CANARY_LOG" 2>&1; then
    rm -f "$CANARY_LOG"
    CANARY_LOG=""
    : # pass
else
    cat "$CANARY_LOG" >&2
    rm -f "$CANARY_LOG"
    CANARY_LOG=""
    echo "BLOCKED: Canary gate failed — classification regression detected." >&2
    exit 2  # <-- BLOCKS GIT COMMIT
fi
```

**Lineage/re-derive:** The canary tests the SAME `auto_classify()` function that processes real variants downstream (generate_review_packets.py). It is re-derived from the same source every commit — **same-lineage, can be green-and-wrong if the source classification logic has a latent bug**, but the test itself is regression-only (does not validate correctness, only consistency).

---

### 2. MutationGateway.write_verdict

**Verdict shape (verbatim from scripts/knowledge/mutation_gateway.py, lines 658-738):**
```python
def write_verdict(self, verdict: ClaimVerdict, *, supersedes_event: VerdictSupersedingEvent | None = None) -> None:
    con.execute("""
        INSERT INTO claim_verdicts
            (verdict_id, claim_id, support_state, review_status,
             model_version, prompt_template_hash, canary_window_id,
             asserted_at, valid_from, evidence_event_id,
             verdict_projection_hash, evidence_projection_hash,
             claim_binding_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [verdict.verdict_id, verdict.claim_id, verdict.support_state,
              verdict.review_status.value, verdict.model_version, ...])
```

**Is it consumed?** **YES, HEAVILY CONSUMED:**
- Verdicts are written atomically into `claim_verdicts` table (data/knowledge/knowledge.duckdb)
- **Post-commit outbox drain** (lines 314-331): `_drain_pending_corpus_attestations()` routes verdicts to corpus attestation
- **Downstream consumers** read `review_status='current'` verdicts to compute support_state (scripts/knowledge/compute_support_state.py implied)
- Contradict verdicts enqueued as `claim_relation` rows in corpus (lines 573-656: `_enqueue_contradiction_relation`)
- Verdicts block mutations if they have `review_status='superseded'` (line 763-767 update)

---

### 3. Differential count-delta gate

**Status:** **Does NOT exist as a named gate** (grep found none matching "count.*delta" as a gate; only in test names like test_orientation_resolved_dosage.py, test_replay_policy_baseline.py). The only baseline comparator mentioned is in `test_replay_policy_baseline.py` (replaying verdicts against a baseline), but no live decorrelated verifier gate found in the pipeline.

---

### 4. Genomics ledger/store

**Path:** `data/knowledge/knowledge.duckdb`

**Key tables + columns:**
- `claim_verdicts` (verdict_id, claim_id, support_state, review_status, model_version, asserted_at, valid_from, ...)
- `source_observations` (observation_id, source_id, canonical_source_id, status, evidence_depth, fetched_at, ...)
- `evidence_bindings` (binding_id, verdict_id, observation_id, asserted_at, valid_from)
- `pending_corpus_attestations` (verdict_id, canonical_source_id, annotation_status, supersedes_annotation_id, relation_json, ...)
- `canary_windows` (window_id, model_version, started_at, baseline_window_id)
- `canary_results` (result_id, window_id, prompt_id, parsed_support_state, raw_text)

---

## MIGRATION VERDICTS

### Intel: resolve-heartbeat → PARTIAL PORT

**Current state:** The gate EXISTS and IS CONSUMED (blocks Tier-1 writes). However, the gate only fires when heartbeat is stale—it does NOT:
- Block on OTHER pipeline failures (only data_plane_live + heartbeat staleness)
- Track claim resolution outcomes (only reads claims.csv at healthcheck time)

**Migration path:** FAITHFUL PORT — the gate's consumption structure (exit_block at commit time) already exists; just wire additional signals and refactor the override mechanism for the LOOP.md contract.

---

### Genomics: canary_gate → FAITHFUL PORT

**Current state:** The gate EXISTS, IS CONSUMED (blocks commits on exit 2), and is the canonical regression test for the classify pipeline. No missing piece.

**Migration path:** FAITHFUL PORT — already blocks on failure; just formalize the LOOP.md contract around when it runs and what triggers a re-baseline (update tests/fixtures/canary_variants.json with human approval).

---

