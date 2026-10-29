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
    # 资源筛选后的配额来自冻结登记，默认配额与仓库覆盖门槛继续生效。
    existing = ["old/repo", "new0/repo"]
    with pytest.raises(ValueError, match="QUOTA_MISMATCH"):
        campaign.selection_review(review, ids, development, existing)
    with pytest.raises(ValueError, match="COVERAGE_REQUIRED"):
        campaign.selection_review(review, ids, development, existing, new_repository_tasks=20)
    selected = ids[:-1] + ["new5__repo-99"]
    adjusted = {task: row for task, row in review.items() if task != ids[-1]}
    adjusted[selected[-1]] = {
        **review[ids[-1]],
        "repository": "new5/repo",
        "issue_key": "99",
    }
    selection = campaign.selection_review(
        adjusted, selected, development, existing, new_repository_tasks=21
    )
    assert selection["new_repository_tasks"] == 21
    assert selection["existing_repository_new_tasks"] == 9
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


def test_claimed_zero_request_preparation_uses_separate_revalidation_allocation():
    original = "batch/repo__project-1/codex/first"
    attempt = {
        "attempt_id": original + "/preparation-revalidation",
        "original_attempt_id": original,
        "instance_id": "repo__project-1",
        "arm": "codex",
        "allocation_phase": "infrastructure-revalidation",
    }
    evidence = {
        "classification": "infrastructure",
        "issued_requests": 0,
        "claim_status": "CLAIMED",
        "run_id": 123,
        "artifact_sha256": "a" * 64,
        "instance_id": attempt["instance_id"],
        "arm": attempt["arm"],
    }
    protocol = {"phase": "development", "preparation_failures": {original: evidence}}
    assert campaign.allocation_phase(protocol, attempt) == "infrastructure-revalidation"
    assert campaign.allocation_phase(protocol, {"attempt_id": "untouched"}) == "development"
    evidence["issued_requests"] = 1
    with pytest.raises(ValueError, match="REVALIDATION_EVIDENCE_REQUIRED"):
        campaign.allocation_phase(protocol, attempt)
    evidence["classification"] = "cancelled"
    attempt["attempt_id"] = original + "/infrastructure-revalidation"
    assert campaign.allocation_phase(protocol, attempt) == "infrastructure-revalidation"


def test_cpa_parallel_limit_and_retained_development_attempts(monkeypatch):
    import json

    path = (
        Path(__file__).resolve().parents[1] / "benchmarks/cross-repo/development-protocol-v2.json"
    )
    protocol = json.loads(path.read_text())
    monkeypatch.setattr(campaign, "execution_fingerprint", lambda: protocol["execution_sha256"])
    protocol["max_parallel"] = 3
    previous = protocol["attempts"][:2]
    protocol["attempts"] = protocol["attempts"][2:]
    protocol["prior_attempts"] = [
        {**row, "source_run_id": 123, "source_artifact_sha256": "a" * 64} for row in previous
    ]
    protocol["formal_request_cap"] = sum(a["request_cap"] for a in protocol["attempts"])
    campaign.validate_protocol(protocol)
    protocol["max_parallel"] = 4
    with pytest.raises(ValueError, match="BUDGET_CONFIGURATION_MISMATCH"):
        campaign.validate_protocol(protocol)


def test_five_arms_share_task_environment_with_distinct_repository_images(monkeypatch):
    import json

    path = (
        Path(__file__).resolve().parents[1] / "benchmarks/cross-repo/development-protocol-v2.json"
    )
    protocol = json.loads(path.read_text())
    monkeypatch.setattr(campaign, "execution_fingerprint", lambda: protocol["execution_sha256"])
    protocol["task_environments"] = {
        task: {
            "image": f"ghcr.io/example/project@sha256:{index + 1:064x}",
            "image_id": f"sha256:{index + 10:064x}",
        }
        for index, task in enumerate(protocol["tasks"])
    }
    campaign.validate_protocol(protocol)
    for attempt in protocol["attempts"]:
        assert (
            campaign.task_environment(protocol, attempt["instance_id"])
            == (protocol["task_environments"][attempt["instance_id"]])
        )
    first = protocol["tasks"][0]
    protocol["task_environments"].pop(first)
    with pytest.raises(ValueError, match="TASK_ENVIRONMENT_REGISTRY_MISMATCH"):
        campaign.validate_protocol(protocol)


@pytest.mark.parametrize("defect", [None, "overlap", "missing_arm", "identity", "quota"])
def test_incremental_formal_retains_campaign_review_and_unique_allocations(monkeypatch, defect):
    import json

    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "benchmarks/cross-repo/development-protocol-v2.json").read_text())
    registry = json.loads((root / "benchmarks/cross-repo/formal-preparation.json").read_text())
    review = json.loads((root / "benchmarks/cross-repo/formal-selection-review.json").read_text())
    tasks = registry["instances"][:3]
    batch = "cross-repository-20261028-formal"
    protocol.update(
        phase="formal",
        tasks=tasks,
        attempts=campaign.execution_order(tasks, batch=batch),
        formal_request_cap=len(tasks) * 120,
        prior_attempts=[],
        qualification_contracts={task: {} for task in tasks},
        repeat_tasks=registry["instances"][-6:],
        existing_repositories=[
            "catchorg/Catch2",
            "fmtlib/fmt",
            "nlohmann/json",
            "simdjson/simdjson",
            "zeux/pugixml",
            "leethomason/tinyxml2",
        ],
        selection_gate={
            "review": review,
            "campaign_tasks": registry["instances"],
            "new_repository_tasks": registry["new_repository_tasks"],
            "development": {
                "tasks": [
                    "nlohmann__json-3514",
                    "nlohmann__json-3463",
                    "open-source-parsers__jsoncpp-1696",
                    "simdjson__simdjson-1896",
                ],
                "scored_attempts": 20,
                "results_sha256": "a" * 64,
                "difficulty_counts": registry["difficulty_counts"],
            },
        },
        incremental_submission={
            "campaign_batch_id": batch,
            "campaign_request_cap": 3600,
            "prior_batches": [
                {
                    "protocol": "batch-01.json",
                    "sha256": "b" * 64,
                    "tasks": registry["instances"][3:6],
                }
            ],
        },
    )
    monkeypatch.setattr(campaign, "execution_fingerprint", lambda: protocol["execution_sha256"])
    if defect == "overlap":
        protocol["incremental_submission"]["prior_batches"][0]["tasks"] = tasks
    elif defect == "missing_arm":
        protocol["attempts"].pop()
        protocol["formal_request_cap"] -= 24
    elif defect == "identity":
        protocol["attempts"][0]["attempt_id"] += "-retry"
    elif defect == "quota":
        protocol["selection_gate"]["new_repository_tasks"] = 25
    if defect:
        with pytest.raises(ValueError, match="CROSS_"):
            campaign.validate_protocol(protocol)
    else:
        campaign.validate_protocol(protocol)
