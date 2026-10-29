"""Frozen task/attempt/candidate identities and scoring without a model call."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def attempt(task, tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    import run_benchmark_agent as worker
    import score_benchmark_attempt as scorer
    from verify_qualification_evidence import required_task_artifacts

    qualified = tmp_path / "qualified"
    produced = tmp_path / "worker"
    qualified.mkdir()
    produced.mkdir()
    for directory in (qualified, produced):
        (directory / ("task.yaml" if directory == qualified else "task.original.yaml")).write_bytes(
            task.source_bytes
        )
    patch = b"diff --git a/src/stats.cpp b/src/stats.cpp\n"
    (produced / "candidate.patch").write_bytes(patch)
    metadata = {
        "schema": "repropatch.benchmark-attempt.v1",
        "attempt": "first-formal-attempt",
        "agent": "repropatch",
        **worker.attempt_identity(task, "first-formal-attempt"),
        **worker.candidate_metadata(patch),
        "native_status": "INCONCLUSIVE",
        "native_reason": "EXTERNAL_ORACLE_REQUIRED",
        "internal_verification_status": "skipped_candidate_only",
        "baseline_eligible": True,
        "container_deleted": True,
    }
    qualification = {
        "status": "QUALIFIED",
        "backend": "docker",
        "instance_id": task.id,
        "task_file_sha256": metadata["task_sha256"],
        "prepared_commit": task.revision,
        "image_id": task.environment.image,
    }
    worker.save(produced / "result.json", metadata)
    worker.save(qualified / "result.json", qualification)
    # Synthetic contract evidence only; this fixture does not claim a C++ qualification.
    for name in required_task_artifacts(qualification):
        path = qualified / name
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic qualification evidence\n")
    worker.save(
        qualified / "manifest.json",
        {
            path.relative_to(qualified).as_posix(): {
                "size": path.stat().st_size,
                "sha256": scorer.digest(path),
            }
            for path in qualified.rglob("*")
            if path.is_file()
        },
    )
    args = SimpleNamespace(
        worker_result=produced / "result.json",
        qualification=qualified / "result.json",
        candidate=None,
        attempt_id=metadata["attempt_id"],
        dataset=tmp_path / "unused-dataset",
        repository=task.repository,
        output=tmp_path / "score",
        timeout=60,
        build_jobs=1,
        check_only=True,
    )
    return scorer, args, metadata, qualification


def test_candidate_only_is_pending_and_score_evidence_is_frozen(attempt):
    scorer, args, _, _ = attempt
    result = scorer.score(args)
    assert result["status"] == "PENDING_ORACLE"
    assert result["accepted"] is None and result["model_failure"] is None
    assert not result["oracle_executed"] and result["scoring_model_requests"] == 0
    assert result["qualification_evidence_status"] == "VERIFIED"
    assert result["qualification_manifest_sha256"] == scorer.digest(
        args.output / "qualification-manifest.json"
    )
    assert (args.output / "candidate.patch").read_bytes() == (
        args.worker_result.parent / "candidate.patch"
    ).read_bytes()
    manifest = json.loads((args.output / "manifest.json").read_text())
    assert all(
        scorer.digest(args.output / name) == entry["sha256"] for name, entry in manifest.items()
    )
    with pytest.raises(FileExistsError):
        scorer.score(args)


def test_derived_text_task_keeps_worker_and_oracle_identity_aligned(attempt, tmp_path):
    from formal_benchmark import prepare_execution_contract
    from run_benchmark_agent import attempt_identity

    from repropatch.task import Task

    scorer, args, metadata, _ = attempt
    original = Task.load(args.qualification.parent / "task.yaml")
    directory = prepare_execution_contract(
        args.qualification.parent,
        tmp_path / "execution-contract",
        original.budget.model_timeout_seconds,
        readable_paths=["src/", "tests/stats_test.cpp", "CMakeLists.txt"],
    )
    task = Task.load(directory / "task.yaml")
    metadata.update(attempt_identity(task, args.attempt_id))
    scorer.save(args.worker_result, metadata)
    (args.worker_result.parent / "task.original.yaml").write_bytes(task.source_bytes)
    args.qualification = directory / "result.json"
    result = scorer.score(args)
    assert result["status"] == "PENDING_ORACLE"
    assert result["qualification_evidence_status"] == "VERIFIED"
    assert result["task_sha256"] == metadata["task_sha256"]
    assert result["qualification_sha256"] == scorer.digest(args.qualification)


@pytest.mark.parametrize("damage", ["missing_manifest", "changed_result"])
def test_missing_or_changed_qualification_evidence_cannot_reach_oracle(
    attempt, monkeypatch, damage
):
    import check_qualified_cpp_candidate as oracle

    scorer, args, _, qualification = attempt
    args.check_only = False
    monkeypatch.setattr(
        oracle, "check", lambda _: pytest.fail("unverified evidence reached Oracle")
    )
    if damage == "missing_manifest":
        (args.qualification.parent / "manifest.json").unlink()
    else:
        qualification["unverified_extra_field"] = True
        scorer.save(args.qualification, qualification)
    result = scorer.score(args)
    assert result["status"] == "QUALIFICATION_EVIDENCE_INCOMPLETE"
    assert result["classification"] == "infrastructure"
    assert result["accepted"] is None and result["model_failure"] is None
    assert not result["oracle_executed"]


@pytest.mark.parametrize(
    "changed",
    [
        "attempt_id",
        "task_sha256",
        "prepared_commit",
        "image_id",
        "candidate_sha256",
        "task_snapshot",
    ],
)
def test_identity_mismatch_cannot_reach_oracle(attempt, changed, monkeypatch):
    import check_qualified_cpp_candidate as oracle

    scorer, args, metadata, _ = attempt
    args.check_only = False
    monkeypatch.setattr(oracle, "check", lambda _: pytest.fail("identity mismatch reached Oracle"))
    if changed == "task_snapshot":
        (args.worker_result.parent / "task.original.yaml").write_bytes(b"tampered")
    else:
        metadata[changed] = "wrong"
        scorer.save(args.worker_result, metadata)
    result = scorer.score(args)
    assert result["classification"] == "infrastructure"
    assert result["accepted"] is None and result["model_failure"] is None
    assert not result["oracle_executed"]


@pytest.mark.parametrize(
    ("changes", "status"),
    [
        (
            {
                "native_status": "ERROR",
                "native_reason": "BASELINE_BUILD_FAILED",
                "baseline_eligible": False,
            },
            "PREPARATION_FAILED",
        ),
        (
            {
                "native_status": "CANCELLED",
                "native_reason": "USER_CANCELLED",
                "baseline_eligible": False,
            },
            "CANCELLED",
        ),
        ({"native_status": "ERROR", "native_reason": "HOST_ERROR"}, "INFRASTRUCTURE_FAILED"),
        ({"native_status": "INTERRUPTED"}, "PENDING_ATTEMPT"),
        ({"container_deleted": False}, "CLEANUP_UNCONFIRMED"),
    ],
)
def test_producer_failure_precedes_missing_candidate(attempt, changes, status):
    scorer, args, metadata, _ = attempt
    metadata.update(changes)
    scorer.save(args.worker_result, metadata)
    (args.worker_result.parent / "candidate.patch").unlink()
    result = scorer.score(args)
    assert result["status"] == status
    assert result["model_failure"] is None and not result["oracle_executed"]


def test_native_qualification_and_empty_candidate_are_separate(attempt):
    scorer, args, metadata, qualification = attempt
    qualification.update(status="HOST_QUALIFIED", backend="native")
    scorer.save(args.qualification, qualification)
    assert scorer.score(args)["status"] == "PREPARATION_FAILED"
    args.output = args.output.with_name("empty-score")
    qualification.update(status="QUALIFIED", backend="docker")
    scorer.save(args.qualification, qualification)
    metadata.update(candidate_available=False, candidate_bytes=0, candidate_sha256=None)
    scorer.save(args.worker_result, metadata)
    (args.worker_result.parent / "candidate.patch").unlink()
    result = scorer.score(args)
    assert result["status"] == "EMPTY_CANDIDATE" and result["model_failure"] is True


@pytest.mark.parametrize(
    "changes",
    [
        {"native_status": "CLI_ERROR"},
        {"native_status": "MODEL_REQUEST_ERROR"},
        {"native_status": "ERROR", "native_reason": "MODEL_REQUEST_TIMEOUT"},
        {"native_status": "ERROR", "native_reason": "AGENT_TIME_LIMIT"},
        {"native_status": "ERROR", "native_reason": "HOST_ERROR"},
        {"native_status": "INTERRUPTED"},
        {"native_status": "ERROR", "recovered_from_unverified_patch": True},
        {"native_status": "ERROR", "candidate_source": "native_frozen"},
    ],
)
def test_frozen_candidate_keeps_native_failure_and_reaches_scoring(attempt, changes):
    scorer, args, metadata, _ = attempt
    metadata.update(changes)
    scorer.save(args.worker_result, metadata)
    result = scorer.score(args)
    assert result["status"] == "PENDING_ORACLE"
    assert result["native_status"] == changes["native_status"]
    assert result["qualification_evidence_status"] == "VERIFIED"


@pytest.mark.parametrize(
    ("status", "accepted", "classification", "model_failure"),
    [
        ("ORACLE_PASSED", True, "resolved", False),
        ("ORACLE_BUILD_FAILED", False, "candidate", True),
        ("ORACLE_TEST_INFRASTRUCTURE_FAILED", False, "infrastructure", None),
    ],
)
def test_common_oracle_receives_frozen_candidate_and_controls_the_score(
    attempt, monkeypatch, status, accepted, classification, model_failure
):
    import check_qualified_cpp_candidate as oracle

    scorer, args, metadata, _ = attempt
    args.check_only = False

    def check(options):
        assert options.candidate.parent == args.output
        assert options.qualification == args.qualification
        assert scorer.digest(options.candidate) == metadata["candidate_sha256"]
        options.output.mkdir()
        verdict = {
            "accepted": accepted,
            "status": status,
            "cold_build": True,
            "compiler_cache": "disabled",
            "qualification_sha256": scorer.digest(args.qualification),
            "candidate_sha256": scorer.digest(options.candidate),
        }
        scorer.save(options.output / "oracle-verdict.json", verdict)
        scorer.save(options.output / "manifest.json", {})
        return verdict

    monkeypatch.setattr(oracle, "check", check)
    result = scorer.score(args)
    assert result["status"] == status
    assert result["classification"] == classification
    assert result["model_failure"] is model_failure
    assert result["oracle_executed"] and result["scoring_model_requests"] == 0


def test_worker_exports_task_identity_without_a_model_call(task, tmp_path, monkeypatch, capsys):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    import sys

    import run_benchmark_agent as worker
    from benchmark_budget import LocalUsageLedger

    from repropatch.task import Task

    raw = task.to_dict()
    raw["budget"].update(
        max_steps=12, max_tool_calls=24, max_output_tokens=8192, model_timeout_seconds=90
    )
    frozen = Task.from_dict(raw, tmp_path)
    task_file = tmp_path / "task.yaml"
    task_file.write_bytes(frozen.source_bytes)
    ledger = LocalUsageLedger.create(tmp_path / "usage.sqlite3")
    output = tmp_path / "worker"

    def no_model(args, hooks, parsed_task):
        assert parsed_task.source_bytes == frozen.source_bytes
        return {
            "native_status": "INCONCLUSIVE",
            "native_reason": "EXTERNAL_ORACLE_REQUIRED",
            "internal_verification_status": "skipped_candidate_only",
            "container_deleted": True,
        }

    monkeypatch.setattr(worker, "repropatch_agent", no_model)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "worker",
            "--agent",
            "repropatch",
            "--provider",
            "local-luna",
            "--task",
            str(task_file),
            "--ledger",
            str(ledger.path),
            "--attempt",
            "identity-fixture",
            "--output",
            str(output),
            "--candidate-only",
        ],
    )
    assert worker.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["task_sha256"] == hashlib.sha256(task_file.read_bytes()).hexdigest()
    assert result["attempt_id"] == "identity-fixture"
    assert result["prepared_commit"] == task.revision
    assert (output / "task.original.yaml").read_bytes() == task_file.read_bytes()
    assert result["money"]["requests"] == 0


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (-9, "RESOURCE_TERMINATED"),
        (137, "RESOURCE_TERMINATED"),
        (125, "ENVIRONMENT_FAILED"),
        (126, "ENVIRONMENT_FAILED"),
        (127, "ENVIRONMENT_FAILED"),
        (-11, "EXECUTION_TERMINATED"),
    ],
)
def test_build_process_termination_is_not_a_model_compile_failure(attempt, code, expected):
    scorer, args, _, _ = attempt
    command = {"stage": "build", "exit_code": code}
    assert scorer.oracle_execution_failure({"commands": [command]}, args.output)[0] == expected
    command["stage"] = "ctest"
    assert scorer.oracle_execution_failure({"commands": [command]}, args.output) is None


def test_compiler_kill_log_is_preserved_as_resource_failure(attempt):
    scorer, args, _, _ = attempt
    args.output.mkdir()
    log = args.output / "build.log"
    log.write_bytes(b"c++: fatal error: Killed signal terminated program cc1plus\n")
    command = {"stage": "build", "exit_code": 1, "log": log.name, "log_sha256": scorer.digest(log)}
    status, details = scorer.oracle_execution_failure({"commands": [command]}, args.output)
    assert status == "RESOURCE_TERMINATED" and details["log_sha256"] == scorer.digest(log)
    log.write_bytes(b"error: invalid conversion\n")
    command["log_sha256"] = scorer.digest(log)
    assert scorer.oracle_execution_failure({"commands": [command]}, args.output) is None
