"""候选准入要求完整、成功且身份一致的资格证据。"""

import hashlib
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
summary = importlib.import_module("summarize_candidate_qualification")
pack = importlib.import_module("actions_benchmark").pack


def plan():
    return {
        "model_requests": 0,
        "stage": "qualify",
        "image": "ghcr.io/example/image@sha256:" + "a" * 64,
        "image_id": "sha256:" + "b" * 64,
        "instances": ["org__repo-1", "org__repo-2"],
    }


def test_missing_qualification_never_becomes_eligible(tmp_path):
    report = summary.summarize(plan(), tmp_path)
    assert report["status"] == "BLOCKED"
    assert report["qualified"] == 0
    assert report["eligible_instances"] == []
    assert all(row["qualification_status"] == "MISSING_RESULT" for row in report["tasks"])


def test_archive_checksum_is_required_before_reading_results(tmp_path):
    directory = tmp_path / "cross-evidence-run-task"
    directory.mkdir()
    archive = directory / "cross-evidence.tar.gz"
    archive.write_bytes(b"corrupted archive")
    archive.with_suffix(".gz.sha256").write_text(hashlib.sha256(b"original").hexdigest())
    report = summary.summarize(plan(), tmp_path)
    assert report["status"] == "BLOCKED"
    assert report["archive_errors"][0]["error"] == "ARCHIVE_CHECKSUM_MISMATCH"
    assert not report["eligible_instances"]


def test_duplicate_results_do_not_select_a_successful_retry(tmp_path, monkeypatch):
    for name in ("first", "second"):
        directory = tmp_path / name
        directory.mkdir()
        (directory / "cross-evidence.tar.gz").touch()

    def inspect(path, image_id):
        return [
            {
                "instance_id": "org__repo-1",
                "qualification_status": "QUALIFIED",
                "eligible": True,
                "evidence_errors": [],
            }
        ]

    monkeypatch.setattr(summary, "inspect_archive", inspect)
    report = summary.summarize(plan(), tmp_path)
    assert report["status"] == "BLOCKED"
    assert not report["eligible_instances"]
    assert report["tasks"][0]["evidence_errors"] == ["DUPLICATE_QUALIFICATION_RESULT"]


def test_paid_plan_cannot_run_as_zero_model_qualification(tmp_path):
    with pytest.raises(ValueError, match="ZERO_MODEL_QUALIFICATION_PLAN_REQUIRED"):
        summary.summarize({**plan(), "model_requests": 1}, tmp_path)


def image_pull(instance):
    return {
        "schema": "repropatch.image-pull.v1",
        "instance_id": instance,
        "image": plan()["image"],
        "stage": "image_pull",
        "status": "IMAGE_PULL_FAILED",
        "model_requests": 0,
        "qualification_executed": False,
        "attempts": [{"exit_code": 1, "diagnostic": "context deadline exceeded"}],
    }


def test_image_pull_archive_reports_original_infrastructure_failure(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "image-pull.json").write_text(json.dumps(image_pull("org__repo-1")))
    artifact = tmp_path / "artifacts/cross-evidence-run-org__repo-1"
    pack(SimpleNamespace(source=source, output=artifact / "cross-evidence.tar.gz"))
    report = summary.summarize(plan(), tmp_path / "artifacts")
    assert report["status"] == "BLOCKED"
    assert not report["archive_errors"]
    assert report["tasks"][0]["qualification_status"] == "IMAGE_PULL_FAILED"
    assert report["tasks"][0]["diagnostic"] == "context deadline exceeded"
    assert not report["eligible_instances"]


def test_toolchain_image_pull_failure_explains_all_missing_candidates(tmp_path):
    environment = tmp_path / "cross-inputs-123/cross-environment"
    environment.mkdir(parents=True)
    (environment / "image-pull.json").write_text(json.dumps(image_pull(None)))
    report = summary.summarize(plan(), tmp_path)
    assert report["status"] == "BLOCKED"
    assert {row["qualification_status"] for row in report["tasks"]} == {"IMAGE_PULL_FAILED"}
    assert all(row["diagnostic"] == "context deadline exceeded" for row in report["tasks"])
    assert not report["eligible_instances"]


def test_failed_download_emits_a_blocked_report_without_artifacts(tmp_path):
    report = summary.summarize(plan(), tmp_path, download_status="failure")
    assert report["status"] == "BLOCKED"
    assert report["archive_errors"] == [
        {"archive": "qualification", "error": "ARTIFACT_DOWNLOAD_FAILURE"}
    ]
    assert not report["eligible_instances"]


def test_blocked_plan_does_not_emit_a_partial_experiment_queue(tmp_path, monkeypatch):
    directory = tmp_path / "cross-evidence-run-org__repo-1"
    directory.mkdir()
    (directory / "cross-evidence.tar.gz").touch()
    monkeypatch.setattr(
        summary,
        "inspect_archive",
        lambda *args: [
            {
                "instance_id": "org__repo-1",
                "qualification_status": "QUALIFIED",
                "eligible": True,
                "evidence_errors": [],
            }
        ],
    )
    report = summary.summarize(plan(), tmp_path)
    assert report["status"] == "BLOCKED"
    assert report["qualified"] == 1
    assert report["qualified_instances"] == ["org__repo-1"]
    assert report["eligible_instances"] == []


def qualified_cases():
    """构造用例结果，验证成功标签与逐项状态的一致性。"""
    contract = {
        "mode": "ctest",
        "required_native_tests": ["regression", "control"],
        "groups": {"regression": ["regression"], "control": ["control"]},
        "declared_native_f2p": ["regression"],
    }
    passed = {"regression": "passed", "control": "passed"}
    result = {
        "adapter": "native-cpp-v1",
        "qualification_policy": "baseline-native-v1",
        "f2p": ["regression"],
        "p2p": ["control"],
        "required_tests": ["control", "regression"],
        "required_native_tests": ["regression", "control"],
        "native_test_count": 2,
        "native_oracle": {"passed": True, "cold_build": True, "native_test_count": 2},
        "cleanup": {"status": "SUCCEEDED"},
        "phases": {
            "baseline": {
                "status": "TESTS_FAILED",
                "tests": {"regression": "failed", "control": "passed"},
            },
            "native_oracle": {"status": "PASSED", "tests": passed, "native_tests": passed},
        },
    }
    native = {"tests": passed, "missing": [], "additional_failures": []}
    return result, contract, native


def test_complete_recorded_case_outcomes_pass_the_consistency_gate():
    assert summary.qualification_gate_errors(*qualified_cases()) == []


def test_success_label_cannot_hide_a_baseline_p2p_failure():
    result, contract, native = qualified_cases()
    result["phases"]["baseline"]["tests"]["control"] = "failed"
    assert "QUALIFICATION_GATE_INCOMPLETE" in summary.qualification_gate_errors(
        result, contract, native
    )


def test_success_label_cannot_hide_a_missing_native_case():
    result, contract, native = qualified_cases()
    native["tests"] = {"regression": "passed"}
    assert "NATIVE_ORACLE_CASES_INCOMPLETE" in summary.qualification_gate_errors(
        result, contract, native
    )


def test_json_single_header_must_have_passed_all_f2p_cases():
    result, contract, native = qualified_cases()
    result["configuration"] = {"repository": "nlohmann/json"}
    assert "SINGLE_HEADER_GATE_INCOMPLETE" in summary.qualification_gate_errors(
        result, contract, native
    )
    result["phases"]["single_header"] = {
        "status": "PASSED",
        "tests": {"regression": "passed"},
    }
    assert (
        summary.qualification_gate_errors(
            result, contract, native, {"tests": {"regression": "passed"}}
        )
        == []
    )


@pytest.mark.parametrize("changed", [None, "archive_sha256", "result_sha256", "artifact"])
def test_reused_evidence_must_match_the_registered_source(tmp_path, monkeypatch, changed):
    instance = "org__repo-1"
    identity = {
        "run_id": 123,
        "artifact": f"cross-evidence-123-{instance}",
        "archive_sha256": "a" * 64,
        "result_sha256": "b" * 64,
    }
    directory = tmp_path / identity["artifact"]
    directory.mkdir()
    (directory / "cross-evidence.tar.gz").touch()
    row = {
        "instance_id": instance,
        "qualification_status": "QUALIFIED",
        "eligible": True,
        "evidence_errors": [],
        "archive": identity["artifact"],
        "archive_sha256": identity["archive_sha256"],
        "result_sha256": identity["result_sha256"],
    }
    if changed:
        identity[changed] = "unexpected"
    monkeypatch.setattr(summary, "inspect_archive", lambda *args: [row])
    selected = {
        **plan(),
        "instances": [instance],
        "reusable_qualifications": {instance: identity},
    }
    report = summary.summarize(selected, tmp_path)
    assert report["status"] == ("BLOCKED" if changed else "QUALIFIED")
    assert report["eligible_instances"] == ([] if changed else [instance])
