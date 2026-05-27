-- DuckDB schema for the canonical paper graph index.
-- Rebuilt by `corpus maintain --rebuild-graph` from per-paper JSONL files.

-- Phase G0: DB-resident schema version. Every connection that runs this
-- schema_sql is brought up to at least graph schema 1.0.0. Bumps land via
-- corpus_core.schema_version.bump_schema(...) inside migration commits.
CREATE TABLE IF NOT EXISTS corpus_schema_meta (
    artifact             VARCHAR PRIMARY KEY,
    schema_version       VARCHAR NOT NULL,
    min_reader_version   VARCHAR NOT NULL,
    min_writer_version   VARCHAR NOT NULL,
    updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes                VARCHAR
);

INSERT INTO corpus_schema_meta
    (artifact, schema_version, min_reader_version, min_writer_version, notes)
VALUES ('graph', '1.0.0', '1.0.0', '1.0.0', 'pre-bitemporal substrate v2.x')
ON CONFLICT (artifact) DO NOTHING;

CREATE TABLE IF NOT EXISTS edges (
  citing_paper_id  TEXT NOT NULL,
  cited_paper_id   TEXT NOT NULL,
  citance_id       TEXT NOT NULL,
  stance_class     TEXT NOT NULL CHECK (stance_class IN ('supporting','contrasting','mentioning')),
  stance_cito      TEXT,
  stance_confidence REAL,
  stance_source    TEXT NOT NULL,
  snippet          TEXT NOT NULL,
  citing_section   TEXT,
  citing_page      INTEGER,
  providers        TEXT[],
  fetched_at       TIMESTAMP,
  PRIMARY KEY (citing_paper_id, cited_paper_id, citance_id)
);
CREATE INDEX IF NOT EXISTS edges_by_cited  ON edges(cited_paper_id);
CREATE INDEX IF NOT EXISTS edges_by_stance ON edges(cited_paper_id, stance_class);

CREATE TABLE IF NOT EXISTS papers (
  paper_id          TEXT PRIMARY KEY,
  doi               TEXT,
  pmid              TEXT,
  title             TEXT,
  fabio_class       TEXT,
  wikidata_qid      TEXT,
  openalex_id       TEXT,
  retrieved_at      TIMESTAMP,
  retraction_status TEXT,
  used_by_repos     TEXT[]
);

-- Substrate-v1 annotations table (per Phase 2 of substrate-migration plan).
-- Per-source ~/Projects/corpus/<source_id>/annotations.jsonl is the source of
-- truth; this table is a derived projection rebuildable via
-- `corpus maintain --rebuild-annotations-index`.
CREATE TABLE IF NOT EXISTS annotations (
  annotation_id            VARCHAR PRIMARY KEY,
  source_id                VARCHAR NOT NULL,
  source_type              VARCHAR,                       -- denormalized from metadata.json
  repo                     VARCHAR NOT NULL,
  actor_type               VARCHAR NOT NULL,
  actor_id                 VARCHAR NOT NULL,
  scope                    VARCHAR NOT NULL,
  tool                     VARCHAR,
  prompt_template_hash     VARCHAR,
  output_uri               VARCHAR,
  output_hash              VARCHAR,
  source_content_hash      VARCHAR,
  supersedes_annotation_id VARCHAR,
  status                   VARCHAR NOT NULL,
  asserted_at              TIMESTAMP NOT NULL,
  recorded_at              TIMESTAMP NOT NULL,
  schema_version           VARCHAR NOT NULL,
  -- Phase A: bitemporal `valid_from` (informational; defaults to
  -- asserted_at on writer's behalf). NOT in annotation_stable_tuple
  -- — adding it does not mutate annotation_id. Pure-append-only:
  -- no valid_to; supersession is a NEW annotation that points back
  -- via supersedes_annotation_id.
  valid_from               TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_annotations_source     ON annotations(source_id);
CREATE INDEX IF NOT EXISTS idx_annotations_repo_time  ON annotations(repo, recorded_at);
CREATE INDEX IF NOT EXISTS idx_annotations_scope      ON annotations(scope);

-- Phase A migration for pre-1.1.0 DBs: idempotent ALTER + UPDATE +
-- DROP/CREATE VIEW. Greenfield DBs already have valid_from from the
-- CREATE TABLE above; ALTER IF NOT EXISTS is a no-op for them.
-- The view binding requires DROP-then-CREATE because DuckDB rejects
-- ALTER TABLE while a dependent view is bound (v5 critique #12).
DROP VIEW IF EXISTS annotations_current;
ALTER TABLE annotations ADD COLUMN IF NOT EXISTS valid_from TIMESTAMP;
UPDATE annotations SET valid_from = asserted_at WHERE valid_from IS NULL;

-- Phase A: chain-aware current view. Pure-append-only — "current" is
-- whatever has no successor (no other annotation supersedes it). DuckDB
-- auto-decorrelates NOT EXISTS to hash anti-join (Raasveldt 2023).
-- Multi-agent revision/retraction branches naturally surface as MULTIPLE
-- leaves for the same source — operator UX, not DB constraint.
-- v6: dropped UNIQUE(supersedes_annotation_id) index per critique #7;
-- two annotations legitimately superseding the same prior is a curation
-- signal, not a violation.
CREATE OR REPLACE VIEW annotations_current AS
SELECT a.* FROM annotations a
WHERE NOT EXISTS (
    SELECT 1 FROM annotations s
    WHERE s.supersedes_annotation_id = a.annotation_id
);

-- Phase A bumps the graph artifact to 1.1.0. Bump is MONOTONIC: WHERE
-- guard on EXCLUDED.schema_version > existing prevents an older client
-- (running an older schema_sql) from silently downgrading the meta row
-- on a newer DB (plan-close finding #1 — CONFIRMED).
--
-- String compare assumes single-digit minor.patch — adequate through
-- 1.9.x. If we ever cross 1.10.0, switch to a function-based compare.
INSERT INTO corpus_schema_meta
    (artifact, schema_version, min_reader_version, min_writer_version, notes, updated_at)
VALUES ('graph', '1.1.0', '1.1.0', '1.1.0',
        '+valid_from informational; annotations_current chain-aware view', now())
ON CONFLICT (artifact) DO UPDATE SET
    schema_version       = EXCLUDED.schema_version,
    min_reader_version   = EXCLUDED.min_reader_version,
    min_writer_version   = EXCLUDED.min_writer_version,
    notes                = EXCLUDED.notes,
    updated_at           = now()
WHERE EXCLUDED.schema_version > corpus_schema_meta.schema_version;

-- Phase B: cross-repo source identity crosswalk. Maps repo-local
-- identifiers (intel filing UUIDs, phenome doc_ids, …) to canonical
-- corpus source_ids (doi_*, pmid_*, sha_*).
--
-- Composite PK includes link_type so the same (repo, local_id, corpus_id)
-- triple can carry both 'mainEntityOfPage' (filing is the surface) AND
-- 'cites' (filing cites this paper) if both apply — Schema.org typed
-- linkage avoids the owl:sameAs identity-confusion problem (Raad et al.).
CREATE TABLE IF NOT EXISTS source_identity_crosswalk (
    repo                 VARCHAR NOT NULL,
    repo_local_id        VARCHAR NOT NULL,
    corpus_source_id     VARCHAR NOT NULL,
    link_type            VARCHAR NOT NULL  -- NO DEFAULT; caller specifies
        CHECK (link_type IN ('sameAs', 'mainEntityOfPage', 'about',
                             'subjectOf', 'cites', 'derivedFrom')),
    confidence           VARCHAR NOT NULL DEFAULT 'asserted'
        CHECK (confidence IN ('asserted', 'inferred', 'unverified')),
    asserted_by          VARCHAR NOT NULL,
    asserted_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (repo, repo_local_id, corpus_source_id, link_type)
);
CREATE INDEX IF NOT EXISTS idx_crosswalk_corpus
    ON source_identity_crosswalk(corpus_source_id);
CREATE INDEX IF NOT EXISTS idx_crosswalk_local
    ON source_identity_crosswalk(repo, repo_local_id);

-- Connected-Papers-style similarity views (no embeddings; pure graph).
CREATE VIEW IF NOT EXISTS co_citation_pairs AS
  SELECT e1.cited_paper_id AS paper_a,
         e2.cited_paper_id AS paper_b,
         COUNT(*) AS co_citation_count
  FROM edges e1
  JOIN edges e2 ON e1.citing_paper_id = e2.citing_paper_id
   AND e1.cited_paper_id < e2.cited_paper_id
  GROUP BY 1, 2;

CREATE VIEW IF NOT EXISTS biblio_coupling_pairs AS
  SELECT e1.citing_paper_id AS paper_a,
         e2.citing_paper_id AS paper_b,
         COUNT(*) AS shared_references
  FROM edges e1
  JOIN edges e2 ON e1.cited_paper_id = e2.cited_paper_id
   AND e1.citing_paper_id < e2.citing_paper_id
  GROUP BY 1, 2;
