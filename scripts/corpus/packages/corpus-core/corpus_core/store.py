"""Canonical corpus store helper module.

The store at $CORPUS_ROOT (default ~/Projects/corpus) is the SINGLE authority
for every source's bytes, parse, citation context, and annotations. This module
exposes the read/write primitives. Higher-level commands live in `ingest.py`,
`maintain.py`, `graph_cli.py`.

Key functions:
    get(paper_id) -> dict                  read metadata.json
    paper_path(paper_id) -> Path           directory for a paper_id
    derive_paper_id(doi, pmid, pdf_sha)    deterministic id (raises on collision)
    compute_parsed_sha(parsed_dir) -> str  content sha over parsed/ contents
    register_revision(paper_id, pdf)       archive current + bump to new pdf
    iter_papers() -> Iterator[str]         walk store
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from . import SCHEMA_VERSION


class PaperStoreError(Exception):
    """Base for store errors."""


class DOICollisionError(PaperStoreError):
    """Two distinct DOIs slug-collide. Operator must disambiguate."""


class PaperNotFoundError(PaperStoreError):
    """get() called for an unknown paper_id."""


# ---------------------------------------------------------------------------
# Roots
# ---------------------------------------------------------------------------


def store_root() -> Path:
    """Return the configured store root, defaulting to ~/Projects/corpus."""
    return Path(os.environ.get("CORPUS_ROOT", str(Path.home() / "Projects" / "corpus")))


def paper_path(paper_id: str) -> Path:
    return store_root() / paper_id


def graph_db_path() -> Path:
    return store_root() / "graph.duckdb"


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def _slug_doi(doi: str) -> str:
    """Normalize a DOI into a filesystem-safe slug.

    Lowercase, then replace non-alphanumerics with `_`, then collapse consecutive
    underscores, then strip trailing `_`.

    >>> _slug_doi("10.1097/FPC.0000000000000456")
    '10_1097_fpc_0000000000000456'
    """
    s = doi.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def derive_paper_id(
    doi: Optional[str] = None,
    pmid: Optional[str] = None,
    pdf_sha: Optional[str] = None,
    *,
    check_collision: bool = True,
) -> str:
    """Derive a deterministic paper_id.

    Precedence: DOI > PMID > pdf_sha. Raises DOICollisionError if a DOI slug
    collides with an existing paper that has a *different* DOI.
    """
    if doi:
        slug = _slug_doi(doi)
        pid = f"doi_{slug}"
        if check_collision:
            _check_doi_collision(pid, doi)
        return pid
    if pmid:
        pmid_clean = str(pmid).strip()
        if not pmid_clean.isdigit():
            raise PaperStoreError(f"PMID must be numeric, got: {pmid!r}")
        return f"pmid_{pmid_clean}"
    if pdf_sha:
        prefix = pdf_sha.replace("sha256:", "")[:16]
        if len(prefix) < 16:
            raise PaperStoreError("pdf_sha must be at least 16 hex chars")
        return f"sha_{prefix}"
    raise PaperStoreError("derive_paper_id requires at least one of doi, pmid, pdf_sha")


def _check_doi_collision(pid: str, raw_doi: str) -> None:
    """Fail closed if pid already exists with a different DOI in metadata.json."""
    p = paper_path(pid)
    meta_path = p / "metadata.json"
    if not meta_path.exists():
        return
    try:
        existing = json.loads(meta_path.read_text())
    except (json.JSONDecodeError, OSError):
        return  # corrupt or unreadable; treat as no collision for now
    existing_doi = (existing.get("doi") or "").strip().lower()
    if existing_doi and existing_doi != raw_doi.strip().lower():
        raise DOICollisionError(
            f"DOI slug collision on {pid!r}: existing DOI {existing_doi!r} != new DOI "
            f"{raw_doi!r}. Disambiguate by appending __sha_<prefix> to the new id."
        )


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_parsed_sha(parsed_dir: Path) -> str:
    """Content-address a parsed/ directory.

    Hashes the sorted list of (relpath, sha256) entries for all regular files
    inside parsed_dir, excluding any pre-existing `parsed.sha256` file.
    """
    if not parsed_dir.is_dir():
        raise PaperStoreError(f"parsed_dir does not exist: {parsed_dir}")
    entries = []
    for sub in sorted(parsed_dir.rglob("*")):
        if not sub.is_file():
            continue
        rel = sub.relative_to(parsed_dir).as_posix()
        if rel == "parsed.sha256":
            continue
        entries.append((rel, sha256_file(sub)))
    h = hashlib.sha256()
    for rel, file_sha in entries:
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(file_sha.encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


@dataclass
class PaperRecord:
    paper_id: str
    metadata: dict
    path: Path

    @property
    def pdf_path(self) -> Path:
        return self.path / "paper.pdf"

    def parsed_dirs(self) -> list[Path]:
        """Every parser-addressed parse dir (``parsed.<parser_id>/``), sorted."""
        return sorted(d for d in self.path.glob("parsed.*") if d.is_dir())

    def parsed_dir_active(self) -> Path | None:
        """The active parse dir: the ``parsed.<parser_id>/`` whose
        ``parsed.sha256`` matches ``metadata['parsed_sha256']`` (else the
        lexicographically-last, else ``None``).

        Parses are immutable and parser-addressed (``ingest._write_parsed``);
        the active one is pinned by ``metadata['parsed_sha256']``.
        """
        want = (self.metadata or {}).get("parsed_sha256")
        dirs = self.parsed_dirs()
        if want:
            for d in dirs:
                sha = d / "parsed.sha256"
                if sha.exists() and sha.read_text().strip() == want:
                    return d
        return dirs[-1] if dirs else None

    def parsed_markdown_path(self) -> Path | None:
        """The active parsed markdown (``parsed.<parser_id>/page.md``), or
        ``None`` if unparsed. The sole entry point for reading parsed text —
        consumers MUST use this, never a hand-built path."""
        d = self.parsed_dir_active()
        if d is None:
            return None
        md = d / "page.md"
        return md if md.exists() else None


def get(paper_id: str) -> PaperRecord:
    p = paper_path(paper_id)
    meta_path = p / "metadata.json"
    if not meta_path.exists():
        raise PaperNotFoundError(paper_id)
    return PaperRecord(paper_id=paper_id, metadata=json.loads(meta_path.read_text()), path=p)


def exists(paper_id: str) -> bool:
    return (paper_path(paper_id) / "metadata.json").exists()


def iter_papers() -> Iterator[str]:
    root = store_root()
    if not root.is_dir():
        return
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and (entry / "metadata.json").exists():
            yield entry.name


# ---------------------------------------------------------------------------
# Write — metadata + paths
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_metadata(paper_id: str, metadata: dict) -> None:
    p = paper_path(paper_id)
    p.mkdir(parents=True, exist_ok=True)
    metadata.setdefault("schema_version", SCHEMA_VERSION)
    metadata.setdefault("paper_id", paper_id)
    (p / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")


def update_metadata(paper_id: str, **fields) -> dict:
    """Read-modify-write metadata.json. Returns the new dict."""
    rec = get(paper_id)
    rec.metadata.update(fields)
    rec.metadata["last_updated"] = _now()
    write_metadata(paper_id, rec.metadata)
    return rec.metadata


# ---------------------------------------------------------------------------
# Revisions
# ---------------------------------------------------------------------------


@dataclass
class RevisionResult:
    paper_id: str
    prior_pdf_sha256: str
    prior_parsed_sha256: Optional[str]
    new_pdf_sha256: str
    archived_pdf: Path
    archived_parsed: Optional[Path]


def register_revision(paper_id: str, new_pdf_path: Path) -> RevisionResult:
    """Archive current paper.pdf + parsed/ and install new PDF.

    Does NOT run the parser — the caller (ingest.py) re-parses after this and
    writes the new parsed/ + updates metadata fields.
    """
    rec = get(paper_id)
    if not rec.pdf_path.exists():
        raise PaperStoreError(f"no current paper.pdf for {paper_id}")
    prior_pdf_sha = rec.metadata.get("pdf_sha256") or sha256_file(rec.pdf_path)
    prior_parsed_sha = rec.metadata.get("parsed_sha256")
    prior_parser_id = (rec.metadata.get("parser", {}) or {}).get("parser_id", "unknown")

    new_pdf_sha = sha256_file(new_pdf_path)
    if new_pdf_sha == prior_pdf_sha:
        raise PaperStoreError(
            f"register_revision called but new PDF has same sha as current ({prior_pdf_sha[:16]}); "
            "use ingest's idempotency path instead"
        )

    # Archive current PDF
    archived_pdf = rec.path / f"paper.{prior_pdf_sha[:8]}.pdf"
    shutil.move(str(rec.pdf_path), str(archived_pdf))

    # Archive the active parse before a re-parse can clobber it. Parses are
    # parser-addressed (parsed.<parser_id>/), so the same parser+config on the
    # new PDF reuses the dir name — rename the old one to carry the prior PDF sha.
    archived_parsed = None
    active_parse = rec.parsed_dir_active()
    if active_parse is not None:
        archived_parsed = rec.path / f"parsed.{prior_parser_id}.{prior_pdf_sha[:8]}"
        shutil.move(str(active_parse), str(archived_parsed))

    # Install new PDF
    shutil.copy2(str(new_pdf_path), str(rec.pdf_path))

    # Record revision in metadata
    revisions = list(rec.metadata.get("revisions", []))
    revisions.append(
        {
            "retired_at": _now(),
            "prior_pdf_sha256": prior_pdf_sha,
            "prior_parsed_sha256": prior_parsed_sha,
            "prior_parser_id": prior_parser_id,
        }
    )
    rec.metadata["revisions"] = revisions
    rec.metadata["pdf_sha256"] = new_pdf_sha
    # parsed_sha256 / parser will be rewritten by re-parse
    rec.metadata.pop("parsed_sha256", None)
    rec.metadata["last_updated"] = _now()
    write_metadata(paper_id, rec.metadata)

    return RevisionResult(
        paper_id=paper_id,
        prior_pdf_sha256=prior_pdf_sha,
        prior_parsed_sha256=prior_parsed_sha,
        new_pdf_sha256=new_pdf_sha,
        archived_pdf=archived_pdf,
        archived_parsed=archived_parsed,
    )


# ---------------------------------------------------------------------------
# parser.json helpers
# ---------------------------------------------------------------------------


def make_parser_id(marker_version: str, surya_version: str, llm: Optional[str], config_md5: str) -> str:
    llm_part = llm or "none"
    return f"marker-{marker_version}+surya-{surya_version}+llm-{llm_part}+cfg-{config_md5[:8]}"


def make_config_md5(config: dict) -> str:
    blob = json.dumps(config, sort_keys=True).encode("utf-8")
    return hashlib.md5(blob).hexdigest()
