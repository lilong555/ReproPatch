"""配对统计与独立阶段执行顺序的合同验证。"""

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
analysis = importlib.import_module("analyze_cross_repo")
campaign = importlib.import_module("cross_repo_campaign")


def test_exact_paired_test_and_holm_correction():
    assert analysis.exact_mcnemar(6, 0) == 0.03125
    assert analysis.exact_mcnemar(3, 3) == 1.0
    assert analysis.exact_mcnemar(0, 0) == 1.0
    assert analysis.holm([0.03, 0.04]) == [0.06, 0.06]


def test_pending_oracle_stays_visible_and_repeated_attempts_are_separate():
    rows = [
        {"instance_id": "repo__project-1", "arm": "full", "score": {"accepted": True}},
        {"instance_id": "repo__project-1", "arm": "shell-only", "score": {"accepted": False}},
        {"instance_id": "repo__project-1", "arm": "no-checks", "score": {"accepted": None}},
    ]
    result = analysis.analyze({"attempts": rows})
    assert result["pending_scores"] == 1
    assert result["primary_comparisons"][0]["wins"] == ["repo__project-1"]
    assert result["primary_comparisons"][1]["pending_pairs"] == 1
    with pytest.raises(ValueError, match="SEPARATE_REPORTS"):
        analysis.analyze({"attempts": [*rows, rows[0]]})


def test_frozen_order_keeps_each_task_arm_and_repeat_identity():
    tasks = ["repo__project-1", "repo__project-2"]
    first = campaign.execution_order(tasks)
    repeat = campaign.execution_order(tasks, replicate="repeat")
    assert campaign.execution_order(tasks) == first
    assert len({(r["instance_id"], r["arm"]) for r in first}) == 10
    assert sum(r["request_cap"] for r in first) == 240
    assert {r["attempt_id"] for r in first}.isdisjoint(r["attempt_id"] for r in repeat)
