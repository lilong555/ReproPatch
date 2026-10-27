"""复验准入、请求额度及中断候选的身份验证。"""

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import complete_context_campaign as completion


def write_json(path, value):
    path.write_text(json.dumps(value))
    return {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def fixture_protocol(tmp_path, monkeypatch):
    monkeypatch.setattr(completion, "ROOT", tmp_path)
    proof = {
        "attempt_id": "old",
        "arm": "mini",
        "interrupted": False,
        "oracle_result": "INFRASTRUCTURE_FAILED",
        "archive_sha256": "archive",
        "usage": {"issued_requests": 1},
        "request_ids": ["request"],
    }
    row = {
        "attempt_id": "old",
        "instance_id": "fmt-1",
        "arm": "mini",
        "oracle_result": "INFRASTRUCTURE_FAILED",
        "stop_reason": "MODEL_TIMEOUT",
        "archive_sha256": "archive",
        "usage": proof["usage"],
    }
    result = {"attempts": [row], "campaign_usage": {"issued_requests": 1}}
    verification = {"passed": True, "failures": [], "issued_requests": 1, "records": [proof]}
    return {
        "revalidation_snapshot": {
            "results": write_json(tmp_path / "results.json", result),
            "verification": write_json(tmp_path / "verification.json", verification),
        },
        "prior_committed_request_upper_bound": 1,
        "formal_request_cap": 24,
        "parent_request_cap": 2520,
        "oracle_request_cap": 0,
        "oracle_attempts": [],
        "attempts": [
            {
                "attempt_id": "new",
                "original_attempt_id": "old",
                "instance_id": "fmt-1",
                "arm": "mini",
                "attempt_classification": "upstream_infrastructure_revalidation",
                "request_cap": 24,
                "source_evidence": proof,
            }
        ],
    }


@pytest.mark.parametrize(
    "problem", [None, "paid_failure", "snapshot_changed", "missing_attempt", "budget_reset"]
)
def test_revalidation_preserves_frozen_results_and_request_budget(tmp_path, monkeypatch, problem):
    protocol = fixture_protocol(tmp_path, monkeypatch)
    if problem == "paid_failure":
        path = tmp_path / "results.json"
        result = json.loads(path.read_text())
        result["attempts"][0]["oracle_result"] = "FAIL"
        protocol["revalidation_snapshot"]["results"] = write_json(path, result)
    elif problem == "snapshot_changed":
        (tmp_path / "verification.json").write_text("{}")
    elif problem == "missing_attempt":
        protocol["attempts"] = []
    elif problem == "budget_reset":
        protocol["prior_committed_request_upper_bound"] = 0
    if problem:
        with pytest.raises(AssertionError):
            completion.snapshot(protocol)
    else:
        rows, proofs = completion.snapshot(protocol)
        assert (
            rows["old"]["oracle_result"]
            == proofs["old"]["oracle_result"]
            == "INFRASTRUCTURE_FAILED"
        )


@pytest.mark.parametrize("status", [524, 200])
def test_revalidation_requires_upstream_failure_in_original_ledger(monkeypatch, tmp_path, status):
    request, response = b'{"model":"gpt-6-luna"}', b"upstream timeout"
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE requests (id,attempt,request_sha256,response_sha256,status_code)")
    db.execute(
        "INSERT INTO requests VALUES (?,?,?,?,?)",
        (
            "request",
            "old",
            hashlib.sha256(request).hexdigest(),
            hashlib.sha256(response).hexdigest(),
            status,
        ),
    )
    files = {
        "ledgers/mini.sqlite3": db.serialize(),
        "mini/http-native/request-request.json": request,
        "mini/http-native/request-response.json": response,
    }
    db.close()
    proof = {
        "arm": "mini",
        "attempt_id": "old",
        "archive_sha256": "archive",
        "request_ids": ["request"],
        "usage": {"issued_requests": 1},
        "interrupted": False,
    }
    monkeypatch.setattr(completion, "load_archive", lambda path: (files, "archive"))
    if status == 200:
        with pytest.raises(AssertionError, match="UPSTREAM_FAILURE_NOT_PROVEN"):
            completion.verify_source(tmp_path / "evidence.tar.gz", proof)
    else:
        assert completion.verify_source(tmp_path / "evidence.tar.gz", proof) is files


@pytest.mark.parametrize("tampered", [False, True])
def test_checkpoint_candidate_uses_frozen_patch_and_original_task(tampered):
    patch = b"saved patch"
    digest = hashlib.sha256(patch).hexdigest()
    attempt = {
        "checkpoint_patch": "checkpoints/20/patch.diff",
        "candidate_sha256": digest,
        "instance_id": "fmt-1",
    }
    manifest = {
        "patch": {"sha256": digest, "size_bytes": len(patch)},
        "boundary": "model_input_ready",
        "input_fingerprints": {"task_sha256": "task", "base_commit": "commit", "image_id": "image"},
    }
    files = {
        "checkpoints/20/patch.diff": b"changed patch" if tampered else patch,
        "checkpoints/20/manifest.json": json.dumps(manifest).encode(),
    }
    protocol = {
        "task_contracts": {"fmt-1": {"execution_task_sha256": "task", "prepared_commit": "commit"}},
        "image_id": "image",
    }
    if tampered:
        with pytest.raises(AssertionError):
            completion.checkpoint_candidate(files, attempt, protocol)
    else:
        assert completion.checkpoint_candidate(files, attempt, protocol) == patch


@pytest.mark.parametrize("accepted", [True, False])
def test_interrupted_cold_score_preserves_stop_and_uses_saved_candidate(
    tmp_path, monkeypatch, accepted
):
    import check_qualified_cpp_candidate

    monkeypatch.setattr(completion, "ROOT", tmp_path)
    qualification = tmp_path / "qualification"
    qualification.mkdir()
    (qualification / "task.yaml").write_text("frozen task")
    (qualification / "result.json").write_text("{}")
    prepared = tmp_path / "prepared"
    prepared.mkdir()
    write_json(prepared / "prepared.json", {"qualification": str(qualification / "result.json")})
    attempt = {
        "instance_id": "fmt-1",
        "arm": "full",
        "original_attempt_id": "old",
        "scoring_id": "checkpoint-score",
        "source_evidence": {"archive_sha256": "archive"},
        "checkpoint_patch": "checkpoints/20/patch.diff",
    }
    protocol = {
        "oracle_attempts": [attempt],
        "task_contracts": {
            "fmt-1": {"execution_task_sha256": completion.sha(qualification / "task.yaml")}
        },
    }
    monkeypatch.setattr(completion, "snapshot", lambda p: None)
    monkeypatch.setattr(completion, "verify_source", lambda archive, proof: {})
    monkeypatch.setattr(completion, "checkpoint_candidate", lambda files, a, p: b"saved patch")

    def check(args):
        assert args.candidate.read_bytes() == b"saved patch"
        assert args.build_jobs == 2 and args.timeout == 900
        return {
            "candidate_sha256": completion.sha(args.candidate),
            "accepted": accepted,
            "cold_build": True,
            "compiler_cache": "disabled",
            "status": "ORACLE_PASSED" if accepted else "ORACLE_BUILD_FAILED",
        }

    monkeypatch.setattr(check_qualified_cpp_candidate, "check", check)
    output = tmp_path / "score"
    assert (
        completion.rescore(protocol, "fmt-1", "full", tmp_path / "archive", prepared, output) == 0
    )
    summary = json.loads((output / "summary.json").read_text())
    assert summary["scoring_model_requests"] == 0
    assert summary["attempts"][0]["stop_reason"] == "USER_CANCELLED"
    assert summary["attempts"][0]["oracle_result"] == ("PASS" if accepted else "FAIL")
