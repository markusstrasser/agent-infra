from pathlib import Path

import autoresearch


def test_patch_signature_normalizes_whitespace_not_constants():
    diff_a = """diff --git a/x.py b/x.py
@@ -1 +1 @@
-value=1
+value = 1
"""
    diff_b = """diff --git a/x.py b/x.py
@@ -9 +9 @@
- value=1
+ value    =    1
"""
    diff_c = """diff --git a/x.py b/x.py
@@ -1 +1 @@
-value=1
+value = 2
"""

    assert autoresearch.patch_signature(diff_a) == autoresearch.patch_signature(diff_b)
    assert autoresearch.patch_signature(diff_a) != autoresearch.patch_signature(diff_c)


def test_archive_parent_selection_mixes_best_failures_and_recent(tmp_path: Path):
    log = autoresearch.ExperimentLog(tmp_path)
    entries = [
        {"experiment_id": 1, "status": "keep", "metric_value": 0.5, "description": "baseline", "node_type": "seed"},
        {"experiment_id": 2, "status": "keep", "metric_value": 0.9, "description": "best", "node_type": "mutation"},
        {"experiment_id": 3, "status": "discard", "metric_value": 0.4, "description": "worse", "node_type": "ablation"},
        {"experiment_id": 4, "status": "holdout_discard", "metric_value": 1.0, "description": "overfit", "node_type": "mutation"},
        {"experiment_id": 5, "status": "crash", "metric_value": None, "description": "crashed", "node_type": "debug"},
        {"experiment_id": 6, "status": "skipped_duplicate", "metric_value": None, "description": "repeat", "node_type": "mutation"},
    ]
    for entry in entries:
        log.log_experiment(entry)
    log.save_patch(2, "diff --git a/x.py b/x.py\n+best\n")
    log.save_patch(4, "diff --git a/x.py b/x.py\n+overfit\n")

    parents = log.select_archive_parents("higher", k=5)
    ids = [p["experiment_id"] for p in parents]

    assert ids[:2] == [2, 1]
    assert 4 in ids
    assert 5 in ids
    assert 6 in ids


def test_build_prompt_includes_node_guidance_and_archive_parent(tmp_path: Path):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / "target.py").write_text("def score():\n    return 1\n")

    log = autoresearch.ExperimentLog(tmp_path / "run")
    parent = {
        "experiment_id": 7,
        "status": "keep",
        "metric_value": 0.75,
        "description": "tighten evaluator",
        "node_type": "replication",
    }
    log.log_experiment(parent)
    log.save_patch(7, "diff --git a/target.py b/target.py\n+assert stable\n")

    prompt = autoresearch.build_prompt(
        {
            "metric_name": "score",
            "metric_direction": "higher",
            "editable_files": ["target.py"],
            "readonly_context": [],
            "archive_patch_chars": 200,
        },
        worktree,
        log,
        node_type="red_team",
        parent_entries=[parent],
    )

    assert "Current node type: red_team" in prompt
    assert "Add or improve adversarial checks" in prompt
    assert "# Archive Parents" in prompt
    assert "Parent #7 patch" in prompt
    assert "+assert stable" in prompt


def test_node_selection_and_generalization_predicate():
    cfg = {"node_types": ["mutation", "debug", "red_team"]}

    assert autoresearch.select_node_type(cfg, 1, 0) == "mutation"
    assert autoresearch.select_node_type(cfg, 2, 0) == "debug"
    assert autoresearch.select_node_type(cfg, 3, autoresearch.DEFAULT_STALL_THRESHOLD) == "red_team"

    assert autoresearch.generalization_worse(1.0, 2.0, "lower")
    assert not autoresearch.generalization_worse(1.0, 1.2, "lower")
    assert autoresearch.generalization_worse(1.0, 0.4, "higher")
    assert not autoresearch.generalization_worse(1.0, 0.8, "higher")
