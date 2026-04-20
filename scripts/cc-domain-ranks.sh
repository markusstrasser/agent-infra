#!/usr/bin/env bash
# Download Common Crawl domain-ranks for a release and transform to parquet.
# Idempotent: skips download + transform if the parquet already exists.
#
# Usage:
#   scripts/cc-domain-ranks.sh [refresh|lookup <domain>]
#   CC_RELEASE=cc-main-2026-jan-feb-mar scripts/cc-domain-ranks.sh refresh
#
# Data source: https://data.commoncrawl.org/projects/hyperlinkgraph/
# Ranks file columns: harmonicc_pos, harmonicc_val, pr_pos, pr_val, host_rev, n_hosts
# host_rev is reverse-labeled (com.google), lower *_pos = more authoritative.

set -euo pipefail

RELEASE="${CC_RELEASE:-cc-main-2026-jan-feb-mar}"
CACHE_ROOT="${HOME}/.cache/cc-domain-ranks"
RELEASE_DIR="${CACHE_ROOT}/${RELEASE}"
RANKS_GZ="${RELEASE_DIR}/ranks.txt.gz"
RANKS_PARQUET="${RELEASE_DIR}/ranks.parquet"
LATEST_LINK="${CACHE_ROOT}/latest.parquet"

BASE="https://data.commoncrawl.org/projects/hyperlinkgraph/${RELEASE}/domain"
RANKS_URL="${BASE}/${RELEASE}-domain-ranks.txt.gz"

mkdir -p "${RELEASE_DIR}"

if ! command -v duckdb >/dev/null; then
    echo "error: duckdb not installed. Run: brew install duckdb" >&2
    exit 1
fi

cmd_refresh() {
    if [[ -f "${RANKS_PARQUET}" ]]; then
        echo "✓ parquet cache exists: ${RANKS_PARQUET}"
        echo "  delete to force rebuild"
    else
        if [[ ! -f "${RANKS_GZ}" ]]; then
            echo "▸ downloading ~2.4 GB ranks file (one-time per release) ..."
            curl -L --fail -C - -o "${RANKS_GZ}" "${RANKS_URL}"
        fi
        echo "▸ transforming to parquet (sorted by host_rev for fast lookup) ..."
        duckdb :memory: <<SQL
COPY (
    SELECT harmonicc_pos, harmonicc_val, pr_pos, pr_val, host_rev, n_hosts
    FROM read_csv('${RANKS_GZ}', delim='\t', skip=1, header=false,
        ignore_errors=true,
        columns={'harmonicc_pos':'BIGINT','harmonicc_val':'DOUBLE',
                 'pr_pos':'BIGINT','pr_val':'DOUBLE',
                 'host_rev':'VARCHAR','n_hosts':'BIGINT'})
    ORDER BY host_rev
) TO '${RANKS_PARQUET}' (FORMAT PARQUET, COMPRESSION ZSTD);
SQL
        echo "✓ wrote ${RANKS_PARQUET} ($(du -h "${RANKS_PARQUET}" | cut -f1))"
        # Keep the gzip for re-transforms; delete manually if space is tight.
    fi
    # Update latest.parquet symlink for consumers.
    ln -sfn "${RANKS_PARQUET}" "${LATEST_LINK}"
    echo "✓ ${LATEST_LINK} -> ${RELEASE}/ranks.parquet"
}

cmd_lookup() {
    local domain="${1:?usage: cc-domain-ranks.sh lookup <domain>}"
    if [[ ! -f "${RANKS_PARQUET}" ]]; then
        echo "error: parquet cache missing. Run: just cc-ranks-refresh" >&2
        exit 1
    fi
    local rev
    rev=$(awk -F. '{for(i=NF;i>0;i--) printf "%s%s", $i, (i>1?".":"")}' <<<"${domain}")
    duckdb :memory: <<SQL
.mode box
SELECT
    '${domain}' AS domain,
    harmonicc_pos,
    pr_pos,
    n_hosts,
    printf('%.3e', harmonicc_val) AS harmonicc_val
FROM read_parquet('${RANKS_PARQUET}')
WHERE host_rev = '${rev}';
SQL
}

case "${1:-}" in
    refresh) cmd_refresh ;;
    lookup)  shift; cmd_lookup "$@" ;;
    *) echo "usage: $0 refresh | lookup <domain>" >&2; exit 2 ;;
esac
