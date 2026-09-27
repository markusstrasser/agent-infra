"""doctor check: archive recency reads the weekly run's dated snapshot."""

import os
import time

from doctor import check_agentlogs_archive_recency


def _snap(root, name, age_days):
    path = root / name
    path.write_bytes(b"")
    stamp = time.time() - age_days * 86400
    os.utime(path, (stamp, stamp))


def test_one_off_copies_do_not_mask_the_newest_weekly_snapshot(tmp_path):
    _snap(tmp_path, "agentlogs-2026-09-27.db.zst", 0)
    _snap(tmp_path, "agentlogs-vacuumed-2026-08-04T2130.db.zst", 54)
    _snap(tmp_path, "agentlogs-legacy-v9-2026-08-20.db.zst", 38)
    [check] = check_agentlogs_archive_recency(tmp_path)
    assert check.status == "pass" and "agentlogs-2026-09-27.db.zst" in check.message


def test_stale_weekly_snapshot_fails(tmp_path):
    _snap(tmp_path, "agentlogs-2026-08-17.db.zst", 41)
    [check] = check_agentlogs_archive_recency(tmp_path)
    assert check.status == "fail"
