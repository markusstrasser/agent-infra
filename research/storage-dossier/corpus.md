# Storage dossier — `/Users/alien/Projects/corpus`

Profiled 2026-07-14. Repo total **9.0G**, `.git` **30M** — confirms this is
working-tree data bloat, not git history. `.gitignore` header spells out the
project's own policy: "track the belief-change ledger, ignore heavy
derivatives" (`corpus/.gitignore:1-4`).

## TOTAL & breakdown

| Chunk | Size | % of repo |
|---|---:|---:|
| `doi_*/sha_*/pmid_*/pmcid_*` source dirs (21,198 dirs) | 6.7G | 74% |
| &nbsp;&nbsp;— of which `*.pdf` (2,581 files) | 4.26G | 47% |
| &nbsp;&nbsp;— of which `parsed.*/` dirs (20,124 dirs) | 1.26G | 14% |
| &nbsp;&nbsp;— of which ledger text (`metadata.json`, `annotations.jsonl`, `citances_*.jsonl`, `source.html/xml`) | ~1.2G | 13% |
| `reference/` | 2.1G | 23% |
| `_staged_extractions/` | 113M | 1% |
| misc (`_abstract_cache`, `.DS_Store`, etc.) | <8M | ~0% |

Reconciliation: 6.7G (sources) + 2.1G (reference) + 0.113G (staged) + small ≈ 9.0G. ✓.

## Per-chunk verdict table

| Chunk | Size | Class | Evidence | Recommended action | Est. GB saved |
|---|---:|:-:|---|---|---:|
| `*.pdf` under `doi_*/sha_*/…` | 4.26G | b (re-downloadable) | `.gitignore:11-13`: `*.pdf` ignored, comment "Re-fetch via `corpus ingest`"; CLI confirmed at `substrate/packages/corpus-core/corpus_core/ingest.py` (`corpus ingest --pdf … [--parser …]`, `corpus ingest --revise`) | Delete-and-refetch-on-demand, or move to `/Volumes/2TBPNY` with symlinks (same pattern already used for `reference/*.duckdb`) | ~4.3G |
| `parsed.*/` dirs under `doi_*/sha_*/…` | 1.26G | b (re-derivable, GPU pipeline) | `.gitignore:11-13`: `parsed.*/` ignored, "re-parse via marker-modal"; build script `agent-infra/scripts/corpus_marker_modal.py` (Modal T4 app, "Marker on Modal — GPU-accelerated PDF → markdown"), invoked via `corpus ingest --parser marker-modal` / `corpus ingest-batch --dir … --max-parallel 10` | Delete-and-reparse-on-demand (cheap: ~$0.005–0.013/PDF cold per script's own cost model) | ~1.26G |
| Ledger text (`metadata.json`, `annotations.jsonl`, `citances_*.jsonl`, `source.html/xml`) | ~1.2G | d (irreplaceable) | `README.md`: "the git history **is** the audit trail of how belief changed — every correction is a commit"; these are explicitly the *tracked* half of `.gitignore`'s split | Must stay on fast local disk (SCHEMA.md: "the corpus store MUST live on a local POSIX filesystem… atomic-append guarantees rely on local kernel POSIX semantics" — NFS/SMB/network mounts unsupported) | 0 (do not touch) |
| `reference/ontology.duckdb`, `ncbitaxon_reference.duckdb`, `umls_reference.duckdb`, `biogrid/biogrid_network.duckdb`, `biogrid/BIOGRID-ORGANISM-LATEST.tab3.zip`, `gwas_catalog/gwas-assoc.zip`, `onsides_v3.1.1/onsides.zip` | 0B locally (already offloaded) | c (already externalized) | `ls -la reference/` shows these as symlinks: e.g. `ontology.duckdb -> /Volumes/2TBPNY/corpus-local-reference/reference/ontology.duckdb`; also `git check-ignore` confirms `*.duckdb` is ignored (`.gitignore:9`) | Already done — no action | 0 (already saved, baseline) |
| `reference/biogrid/BIOGRID-ORGANISM-Homo_sapiens-5.0.258.tab3.txt` | 702M | b (re-downloadable, and literally the unzipped twin of `BIOGRID-ORGANISM-LATEST.tab3.zip`, which is *already* on `/Volumes/2TBPNY`) | Build script `substrate/packages/genomics-read/genomics_read/biogrid.py::build_network(tab3_path, hgnc_path, out_db)` takes this raw tab3 as input and regenerates `biogrid_network.duckdb`; source is BioGRID's public Homo sapiens ORGANISM release | Delete (re-extract from the zip already on 2TBPNY when a rebuild is needed) or move raw .txt itself to `/Volumes/2TBPNY` alongside the zip | 702M |
| `reference/gwas_catalog/gwas-catalog-download-associations-alt-full.tsv` | 683M | b (re-downloadable; unzipped twin of `gwas-assoc.zip`, already on 2TBPNY) | Zip sibling already symlinked out (`gwas-assoc.zip -> /Volumes/2TBPNY/…`); this raw TSV is the public GWAS Catalog "alt-full associations" download | Delete or move to `/Volumes/2TBPNY` | 683M |
| `reference/onsides_v3.1.1/csv/` | 390M | b (re-downloadable; extracted twin of `onsides.zip`, already on 2TBPNY) | `onsides.zip -> /Volumes/2TBPNY/corpus-local-reference/reference/onsides_v3.1.1/onsides.zip` sits right next to this unpacked `csv/` dir; substrate survey (`substrate/docs/research/2026-06-27-source-integration-survey.md`) documents OnSIDES as a public FDA-label-derived reference (drug→ADR) | Delete or move to `/Volumes/2TBPNY` | 390M |
| `reference/goa/goa_human.gaf` + `goa_human.gaf.gz` | 182M (168M+14M) | b/c (re-downloadable + duplicated) | Uncompressed `.gaf` (168M) sits alongside its own `.gz` (14M) — plain gzip re-decompression dedupes this; GOA human annotation file is a public GO Consortium/UniProt download | Delete the uncompressed `.gaf` (keep `.gz`, decompress on demand) | 168M |
| `reference/reactome/NCBI2Reactome_All_Levels.txt` | 92M | b (re-downloadable) | Public Reactome "NCBI2Reactome" mapping download; `genomics/scripts/reactome_core.py` present in the sibling `genomics` repo for Reactome processing | Move to `/Volumes/2TBPNY` or delete/re-download | 92M |
| `reference/mondo_sssom.duckdb`, `synonyms_staging.duckdb` | 14M | c (already gitignored, derived) | `.gitignore:9` `*.duckdb`; too small to bother relocating | Leave | 0 |
| `reference/opentargets/`, `genes_to_phenotype.txt`, `hgnc_complete_set.txt` | 55M | b (re-downloadable, small) | Standard public bulk downloads (Open Targets, HPO gene-to-phenotype, HGNC complete set) | Leave (not worth the operational overhead) | 0 |
| `_staged_extractions/` | 113M | c/b (local scratch, semi-regenerable) | Entirely untracked (`git status`: `?? _staged_extractions/`); referenced as measured fixture data by `substrate/docs/research/2026-06-28-faithfulness-gate-graded.md` ("measured by `scratchpad/measure_discriminators.py`… over real staged extractions under `/Users/alien/Projects/corpus/_staged_extractions`") — regenerable by rerunning the eval sweep against source PDFs, but no single rebuild command exists | Move to `/Volumes/2TBPNY` with a symlink (cheap, avoids breaking the historical-analysis doc's path reference) | 113M |
| `.DS_Store` (7.2M) + misc | 8M | c (gitignored) | `.gitignore:15` `.DS_Store` | Delete freely (regenerates itself) | 7M |

**Caveat found in passing (durability, not storage):** `git log -1` on the repo
shows the last ledger commit was **2026-06-26** ("ledger snapshot 2026-06-26 —
3156 files changed"), 18 days before this audit (2026-07-14). `git status`
shows **18,935 of 21,198** source directories (~89%) as fully untracked (`??`).
The daily `com.agent-infra.corpus-ledger-commit` launchd job exists
(`~/Library/LaunchAgents/com.agent-infra.corpus-ledger-commit.plist`) but
appears stalled — meaning ~3 weeks of `annotations.jsonl`/`metadata.json`
ledger appends have no git-history backup right now. This doesn't change the
PDF/parsed verdicts above (those are gitignored either way, commit status is
irrelevant to them), but **do not treat "not yet committed" as "safe to
delete"** for the ledger text itself — get the commit job healthy before any
bulk file operations near `doi_*/sha_*/`.

**Dedup check:** `/Volumes/2TBPNY/corpus` (281G) exists but is an unrelated
census/CDC/CMS/BLS data-acquisition corpus for a different project — not a
duplicate of `/Users/alien/Projects/corpus`. The correct external counterpart
is `/Volumes/2TBPNY/corpus-local-reference` (6.5G), which already holds the
`.duckdb`/`.zip` files symlinked from `reference/`. No cross-repo duplication
found elsewhere for `doi_*/sha_*/` PDFs.

**External disk headroom:** `/Volumes/2TBPNY` is at 85% capacity (294G free
of 1.8T) — plenty of room for the ~1.9G of reference raw files proposed for
relocation, but not for parking the entire 6.7G of PDFs/parsed output
there "just in case"; prefer delete-and-refetch for those given cheap
re-ingest cost.

## Top 3 recommendations, ranked by GB-saved-per-risk

1. **Delete or externalize the duplicated `reference/` raw source files**
   (`biogrid` tab3.txt 702M, `gwas_catalog` tsv 683M, `onsides` csv 390M, `goa`
   uncompressed gaf 168M, `reactome` txt 92M ≈ **2.0G**). Lowest risk: these
   are byte-for-byte re-derivable from public downloads, and in 3 of 5 cases
   the *compressed original* is already sitting on `/Volumes/2TBPNY` right
   next to the extracted copy — this is pure duplication, not even a
   re-download needed for a rebuild via `genomics_read/biogrid.py::build_network`
   and equivalents. Follow the existing symlink pattern used for
   `reference/*.duckdb`.

2. **Delete-and-refetch `*.pdf` files** (**4.26G**, gitignored, `corpus
   ingest`-refetchable). Biggest single win but slightly higher operational
   risk/cost than #1 (network refetch + possible source-availability drift
   for old DOIs) — do this after confirming the ledger commit job (see
   caveat) is current, since `metadata.json.pdf_sha256` pins are the only
   record of what to refetch.

3. **Delete-and-reparse `parsed.*/` dirs** (**1.26G**, gitignored,
   `marker-modal`-reparseable at ~$0.005–0.013/PDF). Do this together with
   #2 since re-ingest naturally regenerates both; keep as its own line item
   because it can be triggered independently (`corpus ingest-batch --parser
   marker-modal`) without re-fetching PDFs that are still present.

Combined potential savings if all three are executed: **~7.5G of the 9.0G
repo (~83%)**, leaving only the ~1.2G irreplaceable ledger text (class d)
plus small already-optimized reference indexes on the internal drive.
