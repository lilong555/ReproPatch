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


def test_development_oracle_completeness_controls_difficulty():
    tasks = [f"dev__repo-{n}" for n in range(4)]
    rows = [
        {"instance_id": task, "arm": arm, "score": {"accepted": True}}
        for task in tasks
        for arm in campaign.ARMS
    ]
    decision = campaign.development_selection({"attempts": rows}, tasks)
    assert decision["difficulty_counts"] == {"complex": 24, "medium": 4, "compile_control": 2}
    rows[0]["score"]["accepted"] = False
    decision = campaign.development_selection({"attempts": rows}, tasks)
    assert decision["difficulty_counts"] == {"complex": 18, "medium": 8, "compile_control": 4}
    rows[0]["score"]["accepted"] = None
    with pytest.raises(ValueError, match="ORACLE_PENDING"):
        campaign.development_selection({"attempts": rows}, tasks)
    with pytest.raises(ValueError, match="RESULTS_INCOMPLETE"):
        campaign.development_selection({"attempts": rows[:-1]}, tasks)


def test_formal_selection_requires_cross_repo_quotas_and_distinct_defects():
    ids = [f"new{n % 5}__repo-{n}" for n in range(25)] + [f"old__repo-{n}" for n in range(5)]
    levels = ["complex"] * 18 + ["medium"] * 8 + ["compile_control"] * 4
    review = {
        task: {
            "repository": task.rsplit("-", 1)[0].replace("__", "/"),
            "semantic_kind": "defect",
            "historical_model_exposure": "UNEXPOSED",
            "rationale": "状态流转遗漏",
            "issue_key": str(index),
            "difficulty": level,
        }
        for index, (task, level) in enumerate(zip(ids, levels, strict=True))
    }
    development = {
        "tasks": [f"dev__repo-{n}" for n in range(4)],
        "difficulty_counts": {"complex": 18, "medium": 8, "compile_control": 4},
    }
    selection = campaign.selection_review(review, ids, development, ["old/repo"])
    assert selection["new_repository_tasks"] == 25
    review[ids[5]]["issue_key"] = review[ids[0]]["issue_key"]
    with pytest.raises(ValueError, match="SEMANTIC_DUPLICATE"):
        campaign.selection_review(review, ids, development, ["old/repo"])


def test_infrastructure_revalidation_keeps_original_attempt_and_budget(monkeypatch):
    import freeze_cross_revalidation as recovery

    monkeypatch.setattr(recovery, "validate_protocol", lambda value: None)
    original = {
        "attempt_id": "batch/repo__project-1/full/first",
        "instance_id": "repo__project-1",
        "arm": "full",
        "request_cap": 24,
    }
    source = {
        "attempts": [original],
        "qualification_contracts": {"repo__project-1": {"identity": "fixed"}},
    }
    row = {**original, "score": {"classification": "infrastructure", "accepted": None}}
    result = recovery.revalidation(source, {"attempts": [row]}, [original["attempt_id"]])
    assert source["attempts"] == [original]
    assert result["formal_request_cap"] == 24
    assert result["attempts"][0]["original_attempt_id"] == original["attempt_id"]
    assert result["attempts"][0]["attempt_id"] != original["attempt_id"]
    row["score"]["classification"] = "candidate"
    with pytest.raises(ValueError, match="INFRASTRUCTURE_EVIDENCE_REQUIRED"):
        recovery.revalidation(source, {"attempts": [row]}, [original["attempt_id"]])
