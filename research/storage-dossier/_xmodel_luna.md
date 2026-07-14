## 1. Decision policy

| Class | Default disposition | Deciding test |
|---|---|---|
| Derived `.duckdb`/`.sqlite` indexes | Symlink to `/Volumes/2TBPNY/repos/<repo>/indexed`; retain small manifests locally | From a clean checkout, run the pinned build recipe against pinned source and validate schema, row counts, and checksums |
| Public reference data | Symlink external; keep URL/version/checksum fetch metadata in Git | Can the fetch script reproduce the exact bytes without credentials, undocumented steps, or a fragile/disappearing URL? |
| Extracted-paper corpora | Shared external content-addressed store; repo keeps manifests and symlinks/views | Given the PDF hash, extractor version, and parameters, can the exact extracted output be reproduced and verified? |
| Service/account exports | External, preferably compressed and immutable | Restore one export into its consumer and pass parse/import/checksum validation |
| Git-history blob bloat | History rewrite, then local garbage collection | `git filter-repo --analyze` proves the large blobs are unreachable from the intended current state |
| Vendored dependencies / benchmark environments | Externalize first; fetch-script-only only when pinned installation is proven | Fresh environment from lockfile/commit passes the relevant tests or benchmark without network assumptions beyond the documented fetch |

Use external storage for artifact trees, not whole repositories: keep source, manifests, recipes, and small metadata local; symlink only `indexed/`, `data/`, `reference/`, `exports/`, `vendor/`, etc. Never symlink `.git`. Make missing external mounts fail loudly rather than silently rebuilding or using stale local copies.

## 2. Highest-leverage cross-repo moves

1. **Standardize an external artifact root.**  
   Adopt `/Volumes/2TBPNY/repos/<repo>/<class>/` plus a repo-local symlink convention. This immediately targets phenome indexes/MCP data, anki’s `crowdanki/`, corpus references/extractions, intel datasets/indexes, and arc-agi vendor/data/envs—likely 15–20GB with little semantic risk.

2. **Build one shared paper blob store.**  
   Store PDFs by SHA-256 and extracted outputs by `(pdf_hash, extractor_version, parameters)`. Each repo retains a manifest mapping DOI/source IDs to hashes and a derived view. This deduplicates overlapping corpus/genomics/intel holdings without conflating incompatible extraction versions.

3. **Make generated-data boundaries enforceable.**  
   Standardize `data/`, `indexed/`, `tmp/`, `exports/`, and extraction directories; add repository-specific `.gitignore` rules and a pre-commit check that rejects large generated files or database files unless explicitly allowlisted. This prevents the next multi-gigabyte recurrence.

4. **Move regeneration knowledge into manifests, not prose.**  
   Every external/deletable artifact should have source URL or accession, version, checksum, build command, and expected validation counts tracked in Git. This preserves functionality while keeping the working tree small.

## 3. Regeneration-cost trap

Do not blindly delete:

- **UMLS and other licensed/credentialed reference datasets:** retrieval may require access approval, take substantial time, or change versions.
- **Extracted corpora whose PDFs came from paid, rate-limited, or disappearing sources:** extraction is cheap; reacquiring the source is not.
- **Service/account exports:** the account may be deleted, exports may be rate-limited, or historical state may no longer be available.
- **Benchmark datasets and environments tied to discontinued URLs or exact versions:** “public” does not mean reproducible.
- **Manually curated or provenance-bearing databases:** a rebuild may reproduce rows but lose corrections, annotations, or historical identity.

For these, externalize and compress before considering deletion.

## 4. Safe history rewrite

1. Make a mirror backup and record all branches, tags, remotes, and protected refs.
2. In a disposable clone, run `git filter-repo --analyze`; identify dead paths/blobs rather than deleting by size alone.
3. Remove only confirmed unwanted paths/blobs with `git filter-repo`.
4. Run tests, inspect current-tree contents, verify tags/releases, then measure the new pack.
5. Coordinate a maintenance window. Rewritten commits have new IDs; every branch and affected tag must be force-pushed, and collaborators must reclone or hard-reset rather than merge old history.
6. After verification, expire reflogs and run garbage collection locally; old clones still retain the original storage.

Rewrite genomics and publishing: together they reclaim roughly 1.25GB of Git pack space. It is not worth doing if the repositories are widely cloned, external consumers depend on immutable commit IDs, or the large blobs are still needed through historical tags/releases. Git compression alone will not solve dead historical blobs.

## Top five

1. Externalize large repo artifact directories — highest immediate return, low risk.  
2. Rewrite confirmed dead Git history — ~1.25GB, moderate coordination risk.  
3. Shared content-addressed PDF/extraction store — potentially multi-GB, moderate implementation risk.  
4. Externalize exports, references, vendor trees, and benchmark environments — broad return, low-to-moderate risk.  
5. Enforce generated-data boundaries with conventions, ignore rules, and pre-commit checks — little immediate savings, but prevents recurrence across all repositories.
