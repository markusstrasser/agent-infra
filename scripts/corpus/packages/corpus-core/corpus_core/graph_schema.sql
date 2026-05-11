-- DuckDB schema for the canonical paper graph index.
-- Rebuilt by `papers maintain --rebuild-graph` from per-paper JSONL files.

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

CREATE TABLE IF NOT EXISTS annotations (
  event_id          TEXT PRIMARY KEY,
  paper_id          TEXT NOT NULL,
  annotated_at      TIMESTAMP NOT NULL,
  annotated_by      TEXT NOT NULL,
  target_kind       TEXT NOT NULL,
  target_ref        TEXT,
  kind              TEXT NOT NULL,
  body              TEXT NOT NULL,
  linked_claim_ids  TEXT[]
);

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
