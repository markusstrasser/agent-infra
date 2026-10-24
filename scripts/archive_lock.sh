# Sourced by the agentlogs-archive recipes: one writer at a time on the 2TBPNY archive tree.
# On 2026-10-24 a StartOnMount run started beside a manual one and began a second .backup over
# the same snapshot path; the compressor must never rewrite a file the archiver is still copying.
# A dead holder's lock is reclaimed. Returns 1 when a live holder exists.
archive_lock_acquire() {
    lock="$HOME/.claude/logs/agentlogs-archive.lock"
    if ! ( set -o noclobber; echo $$ > "$lock" ) 2>/dev/null; then
        holder=$(cat "$lock" 2>/dev/null || true)
        if [ -n "$holder" ] && kill -0 "$holder" 2>/dev/null; then
            echo "skip: agentlogs archive tree busy (pid $holder)"
            return 1
        fi
        echo $$ > "$lock"
    fi
    trap 'rm -f "$lock"' EXIT
}
