"""复验上游故障，并对中断时保存的 Checkpoint 候选执行零模型冷评分。"""

import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from audit_context_history import load_archive, sql_rows
from context_campaign import ROOT, save, sha


def snapshot(protocol):
    for name, digest in protocol.get("model_execution_files", {}).items():
        assert sha(ROOT / name) == digest, "MODEL_EXECUTION_CHANGED"
    documents = {}
    for name, reference in protocol["revalidation_snapshot"].items():
        path = (ROOT / reference["path"]).resolve(strict=True)
        assert path.is_relative_to(ROOT)
        assert sha(path) == reference["sha256"], "CAMPAIGN_SNAPSHOT_CHANGED"
        documents[name] = json.loads(path.read_text())
    results, verification = documents["results"], documents["verification"]
    assert verification["passed"] and not verification["failures"]
    proofs = {row["attempt_id"]: row for row in verification["records"]}
    assert len(proofs) == len(verification["records"])
    request_ids = [identity for proof in proofs.values() for identity in proof["request_ids"]]
    assert len(request_ids) == len(set(request_ids)) == verification["issued_requests"]
    used = sum(proof["usage"]["issued_requests"] for proof in proofs.values())
    assert used == len(request_ids) == results["campaign_usage"]["issued_requests"]
    assert used == protocol["prior_committed_request_upper_bound"]
    assert used + protocol["formal_request_cap"] <= protocol["parent_request_cap"] == 2520
    rows = {row["attempt_id"]: row for row in results["attempts"]}
    expected = {
        identity
        for identity, row in rows.items()
        if row["oracle_result"] == "INFRASTRUCTURE_FAILED"
    }
    assert {a["original_attempt_id"] for a in protocol["attempts"]} == expected
    expected_scores = {
        identity
        for identity, row in rows.items()
        if row["stop_reason"] == "USER_CANCELLED" and row["oracle_result"] == "NOT_EXECUTED"
    }
    assert {a["original_attempt_id"] for a in protocol["oracle_attempts"]} == expected_scores
    assert len(expected) == len(protocol["attempts"])
    assert len(expected_scores) == len(protocol["oracle_attempts"])
    assert protocol["formal_request_cap"] == len(expected) * 24
    assert protocol["oracle_request_cap"] == 0
    assert len({a["attempt_id"] for a in protocol["attempts"]}) == len(expected)
    for attempt in protocol["attempts"] + protocol["oracle_attempts"]:
        identity = attempt["original_attempt_id"]
        row, proof = rows[identity], proofs[identity]
        assert (row["instance_id"], row["arm"]) == (attempt["instance_id"], attempt["arm"])
        assert attempt["source_evidence"] == proof
        assert row["usage"] == proof["usage"]
        assert row["archive_sha256"] == proof["archive_sha256"]
        if identity in expected:
            assert not proof["interrupted"] and proof["oracle_result"] == "INFRASTRUCTURE_FAILED"
            assert attempt["attempt_classification"] == "upstream_infrastructure_revalidation"
            assert attempt["request_cap"] == 24
        else:
            assert proof["interrupted"]
    return rows, proofs


def verify_source(archive, proof):
    files, digest = load_archive(archive)
    assert digest == proof["archive_sha256"], "SOURCE_ARCHIVE_CHANGED"
    requests = sql_rows(
        files[f"ledgers/{proof['arm']}.sqlite3"], "SELECT * FROM requests ORDER BY rowid"
    )
    assert [row["id"] for row in requests] == proof["request_ids"]
    assert len(requests) == proof["usage"]["issued_requests"]
    for row in requests:
        assert row["attempt"] == proof["attempt_id"]
        prefix = f"{proof['arm']}/http-native/{row['id']}"
        assert hashlib.sha256(files[prefix + "-request.json"]).hexdigest() == row["request_sha256"]
        if row["response_sha256"]:
            assert (
                hashlib.sha256(files[prefix + "-response.json"]).hexdigest()
                == row["response_sha256"]
            )
    if not proof["interrupted"]:
        assert requests[-1]["status_code"] in {502, 524}, "UPSTREAM_FAILURE_NOT_PROVEN"
    return files


def checkpoint_candidate(files, attempt, protocol):
    path = attempt["checkpoint_patch"]
    patch = files[path]
    manifest = json.loads(files[path.rsplit("/", 1)[0] + "/manifest.json"])
    assert (
        hashlib.sha256(patch).hexdigest()
        == attempt["candidate_sha256"]
        == manifest["patch"]["sha256"]
    )
    assert len(patch) == manifest["patch"]["size_bytes"]
    contract = protocol["task_contracts"][attempt["instance_id"]]
    fingerprints = manifest["input_fingerprints"]
    assert manifest["boundary"] == "model_input_ready"
    assert fingerprints["task_sha256"] == contract["execution_task_sha256"]
    assert fingerprints["base_commit"] == contract["prepared_commit"]
    assert fingerprints["image_id"] == protocol["image_id"]
    return patch


def preflight(protocol, output):
    from context_campaign import download, gh_json

    snapshot(protocol)
    for run_id in {
        a["source_evidence"]["run_id"] for a in protocol["attempts"] + protocol["oracle_attempts"]
    }:
        run = gh_json("api", f"repos/lilong555/ReproPatch/actions/runs/{run_id}")
        assert run["status"] == "completed", "SOURCE_RUN_ACTIVE"
    for attempt in protocol["attempts"] + protocol["oracle_attempts"]:
        proof = attempt["source_evidence"]
        directory = output / "sources" / proof["artifact"]
        download("lilong555/ReproPatch", proof["run_id"], proof["artifact"], directory)
        files = verify_source(next(directory.glob("*.tar.gz")), proof)
        if proof["interrupted"]:
            checkpoint_candidate(files, attempt, protocol)
    save(
        output / "revalidation-gate.json",
        {
            "passed": True,
            "prior_issued_requests": protocol["prior_committed_request_upper_bound"],
            "revalidation_attempts": len(protocol["attempts"]),
            "cold_scoring_attempts": len(protocol["oracle_attempts"]),
            "request_upper_bound": protocol["prior_committed_request_upper_bound"]
            + protocol["formal_request_cap"],
            "new_model_requests": 0,
        },
    )


def rescore(protocol, instance, arm, archive, prepared, output):
    from check_qualified_cpp_candidate import check
    from score_benchmark_attempt import oracle_execution_failure

    snapshot(protocol)
    attempt = next(
        a for a in protocol["oracle_attempts"] if (a["instance_id"], a["arm"]) == (instance, arm)
    )
    files = verify_source(archive, attempt["source_evidence"])
    patch = checkpoint_candidate(files, attempt, protocol)
    settings = json.loads((prepared / "prepared.json").read_text())
    qualification = Path(settings["qualification"])
    assert (
        sha(qualification.parent / "task.yaml")
        == protocol["task_contracts"][instance]["execution_task_sha256"]
    )
    output.mkdir(parents=True, exist_ok=False)
    candidate = output / "candidate.patch"
    candidate.write_bytes(patch)
    result = {
        "attempt_id": attempt["original_attempt_id"],
        "scoring_id": attempt["scoring_id"],
        "instance_id": instance,
        "arm": arm,
        "stop_reason": "USER_CANCELLED",
        "source_evidence": attempt["source_evidence"],
        "checkpoint_patch": attempt["checkpoint_patch"],
        "candidate_sha256": sha(candidate),
        "scoring_model_requests": 0,
    }
    save(output / "source.json", result)
    verdict = check(
        SimpleNamespace(
            qualification=qualification,
            dataset=ROOT / ".repropatch/inputs/dataset",
            repository=ROOT / ".repropatch/inputs/fmt",
            candidate=candidate,
            output=output / "oracle",
            timeout=900,
            build_jobs=2,
        )
    )
    assert verdict["candidate_sha256"] == result["candidate_sha256"]
    assert verdict["cold_build"] and verdict["compiler_cache"] == "disabled"
    failure = oracle_execution_failure(verdict, output / "oracle")
    status = verdict["status"]
    oracle = (
        "PASS"
        if verdict["accepted"]
        else "FAIL"
        if status
        in {
            "ORACLE_CONFIGURE_FAILED",
            "ORACLE_BUILD_FAILED",
            "ORACLE_TESTS_FAILED",
            "INVALID_CANDIDATE_PATCH",
            "CANDIDATE_SCOPE_REJECTED",
            "EMPTY_CANDIDATE",
        }
        else "INFRASTRUCTURE_FAILED"
    )
    if failure:
        oracle = "INFRASTRUCTURE_FAILED"
    result.update(oracle_result=oracle, oracle_status=status, execution_failure=failure)
    save(output / "summary.json", {"attempts": [result], "scoring_model_requests": 0})
    print(json.dumps(result, ensure_ascii=False))
    return 1 if oracle == "INFRASTRUCTURE_FAILED" else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return rescore(
        json.loads(args.protocol.read_text()),
        args.instance,
        args.arm,
        args.archive,
        args.prepared,
        args.output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
