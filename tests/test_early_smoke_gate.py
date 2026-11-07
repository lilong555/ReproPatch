"""Offline early-smoke evidence, accounting, fairness and artifact integrity checks."""

import hashlib
import io
import json
import stat
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_early_smoke as gate

RUN_ID = "123456"
REPOSITORY = "lilong555/ReproPatch"
COMMIT = "1" * 40


@pytest.fixture
def evidence():
    protocol_path = gate.shared.ROOT / "benchmarks/context-early-20261107/protocol.json"
    protocol = gate.shared.read_protocol(protocol_path)
    expected = gate.shared.trials(protocol, "smoke")
    sources = {"scripts/check_early_smoke.py": "2" * 64}
    protocol_sha256 = gate.shared.sha(protocol_path)
    manifest = {
        "schema": "repropatch.context-ablation.manifest.v1",
        "protocol": protocol,
        "protocol_sha256": protocol_sha256,
        "scope": "smoke",
        "source_sha256": sources,
        "source_commit": COMMIT,
        "github_run_id": RUN_ID,
        "github_run_attempt": 1,
        "attempts": expected,
        "matrix": {"include": expected},
        "trial_count": 3,
        "request_cap": 72,
    }
    manifest["manifest_sha256"] = gate.shared.digest(manifest)
    rows = []
    for index, frozen in enumerate(expected):
        early = frozen["arm"] != "baseline"
        contract = protocol["task_contracts"][frozen["instance_id"]]
        rows.append(
            {
                **frozen,
                "manifest_sha256": manifest["manifest_sha256"],
                "protocol_sha256": protocol_sha256,
                "source_sha256": sources,
                "classification": "candidate",
                "accepted": False,
                "failure": None,
                "usage": {
                    "request_cap": 24,
                    "requests": 3 + int(early),
                    "repair_requests": 3,
                    "compact_requests": int(early),
                    "retry_requests": 0,
                    "unknown_usage_requests": 0,
                    "input_tokens": 1000 * (index + 1),
                    "output_tokens": 100 * (index + 1),
                },
                "score": {
                    "schema": "repropatch.benchmark-score.v1",
                    "attempt_id": frozen["attempt_id"],
                    "oracle_executed": True,
                    "qualification_evidence_status": "VERIFIED",
                    "scoring_model_requests": 0,
                    "accepted": False,
                    "classification": "candidate",
                    "status": "ORACLE_TESTS_FAILED",
                    "oracle_status": "ORACLE_TESTS_FAILED",
                    "oracle_verdict_sha256": "3" * 64,
                    "oracle_manifest_sha256": "4" * 64,
                    "task_sha256": contract["execution_task_sha256"],
                    "prepared_commit": contract["prepared_commit"],
                    "image_id": protocol["image_id"],
                },
                "mechanisms": {
                    "early_observation_reduction": {
                        "enabled": early,
                        "trigger_count": 0,
                        "metrics": {
                            "auxiliary_requests": int(early),
                            "auxiliary_unknown_usage": 0,
                            "auxiliary_input_tokens": 200 * int(early),
                            "auxiliary_output_tokens": 20 * int(early),
                        },
                    }
                },
                "first_request": {
                    "input_sha256": str(5 + index) * 64,
                    "instructions_sha256": "8" * 64,
                    "tools_sha256": "9" * 64,
                    "model": protocol["model"],
                    "reasoning": {"effort": protocol["reasoning_effort"]},
                },
            }
        )
    return {
        "run": {
            "id": int(RUN_ID),
            "repository": {"full_name": REPOSITORY},
            "head_sha": COMMIT,
            "status": "completed",
            "conclusion": "failure",
            "run_attempt": 1,
        },
        "manifest": manifest,
        "result": {
            "schema": "repropatch.context-ablation.aggregate.v1",
            "scope": "smoke",
            "registered_trials": 3,
            "manifest_sha256": manifest["manifest_sha256"],
            "source_sha256": sources,
            "automatic_reruns": 0,
            "rejected_artifacts": [],
            "attempts": rows,
            "arms": {row["arm"]: {"N": 1} for row in rows},
        },
        "arguments": {
            "run_id": RUN_ID,
            "repository": REPOSITORY,
            "source_commit": COMMIT,
            "protocol": protocol,
            "protocol_sha256": protocol_sha256,
            "sources": sources,
        },
    }


def validate(evidence):
    return gate.validate_smoke(
        evidence["run"], evidence["manifest"], evidence["result"], **evidence["arguments"]
    )


def set_path(value, path, replacement):
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = replacement


def test_complete_cold_failures_keep_selections_and_higher_token_use_pass(evidence):
    result = validate(evidence)
    assert result["passed"] is True
    assert all(
        row["accepted"] is False and row["selection_triggers"] == 0 for row in result["attempts"]
    )
    assert result["attempts"][1]["input_tokens"] > result["attempts"][0]["input_tokens"]
    assert result["input_identity"]["byte_identical_input"] is False
    assert result["input_identity"]["input_difference_is_diagnostic"] is True
    assert result["success_or_token_improvement_required"] is False


@pytest.mark.parametrize(
    "path,replacement",
    [
        (("run", "head_sha"), "0" * 40),
        (("run", "repository", "full_name"), "other/repository"),
        (("run", "status"), "in_progress"),
        (("run", "run_attempt"), 2),
        (("manifest", "source_commit"), "0" * 40),
        (("manifest", "source_sha256"), {"different": "0" * 64}),
        (("manifest", "protocol_sha256"), "0" * 64),
        (("result", "attempts"), []),
        (("result", "registered_trials"), 2),
        (("result", "arms", "early", "N"), 2),
        (("result", "attempts", 0, "usage", "unknown_usage_requests"), 1),
        (("result", "attempts", 0, "usage", "input_tokens"), None),
        (("result", "attempts", 0, "usage", "requests"), 25),
        (("result", "attempts", 0, "usage", "requests"), True),
        (("result", "attempts", 0, "usage", "compact_requests"), 12),
        (("result", "attempts", 0, "score", "oracle_executed"), False),
        (("result", "attempts", 0, "score", "oracle_manifest_sha256"), None),
        (("result", "attempts", 0, "score", "accepted"), None),
        (("result", "attempts", 0, "accepted"), None),
        (("result", "attempts", 0, "first_request", "instructions_sha256"), "a" * 64),
        (("result", "attempts", 0, "first_request", "tools_sha256"), "b" * 64),
        (
            (
                "result",
                "attempts",
                1,
                "mechanisms",
                "early_observation_reduction",
                "metrics",
                "auxiliary_requests",
            ),
            0,
        ),
        (
            (
                "result",
                "attempts",
                1,
                "mechanisms",
                "early_observation_reduction",
                "metrics",
                "auxiliary_unknown_usage",
            ),
            1,
        ),
    ],
)
def test_source_population_unknown_usage_and_incomplete_execution_are_rejected(
    evidence, path, replacement
):
    set_path(evidence, path, replacement)
    with pytest.raises(ValueError, match="EARLY_SMOKE_"):
        validate(evidence)


def test_manifest_source_is_checked_after_self_hash_is_valid(evidence):
    manifest = evidence["manifest"]
    manifest["source_commit"] = "0" * 40
    manifest["manifest_sha256"] = gate.shared.digest(
        {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    )
    with pytest.raises(ValueError, match="MANIFEST_SOURCE"):
        validate(evidence)


@pytest.mark.parametrize("status", sorted(gate.COLD_FAILURES))
def test_completed_negative_cold_verdicts_are_fairly_admitted(evidence, status):
    for row in evidence["result"]["attempts"]:
        row["score"].update(status=status, oracle_status=status)
    assert validate(evidence)["passed"] is True


def empty_candidate(row, *, file_exists):
    score = row["score"]
    score.update(
        status="EMPTY_CANDIDATE",
        oracle_executed=False,
        model_failure=True,
        worker_result_sha256="a" * 64,
        qualification_manifest_sha256="b" * 64,
    )
    for key in ("oracle_status", "oracle_verdict_sha256", "oracle_manifest_sha256"):
        score.pop(key)
    row["candidate_sha256"] = hashlib.sha256(b"").hexdigest() if file_exists else None
    if file_exists:
        score.update(candidate_available=False, candidate_bytes=0, candidate_sha256=None)


@pytest.mark.parametrize("indices", [(1,), (0, 1, 2)])
@pytest.mark.parametrize("file_exists", [False, True])
def test_mixed_and_all_empty_candidates_remain_valid_model_failures(evidence, indices, file_exists):
    for index in indices:
        empty_candidate(evidence["result"]["attempts"][index], file_exists=file_exists)
    result = validate(evidence)
    assert result["passed"] is True and result["scorer_rejected_empty"] == len(indices)
    assert all(row["accepted"] is False for row in result["attempts"])
    assert all(
        row["oracle_executed"] is (index not in indices)
        and row["scorer_rejected_empty"] is (index in indices)
        for index, row in enumerate(result["attempts"])
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "MISSING_CANDIDATE"),
        ("model_failure", False),
        ("oracle_executed", True),
        ("worker_result_sha256", None),
        ("qualification_manifest_sha256", "invalid"),
        ("task_sha256", "0" * 64),
        ("prepared_commit", "0" * 40),
        ("candidate_available", True),
        ("candidate_bytes", 1),
        ("candidate_bytes", False),
        ("candidate_sha256", "c" * 64),
    ],
)
def test_empty_candidate_requires_complete_scorer_and_candidate_identity(evidence, field, value):
    row = evidence["result"]["attempts"][0]
    empty_candidate(row, file_exists=True)
    row["score"][field] = value
    with pytest.raises(ValueError, match="EARLY_SMOKE_"):
        validate(evidence)


def test_absent_candidate_cannot_claim_a_nonempty_artifact_or_partial_metadata(evidence):
    row = evidence["result"]["attempts"][0]
    empty_candidate(row, file_exists=False)
    row["candidate_sha256"] = "c" * 64
    with pytest.raises(ValueError, match="EMPTY_CANDIDATE_IDENTITY"):
        validate(evidence)
    row["candidate_sha256"] = None
    row["score"]["candidate_bytes"] = 0
    with pytest.raises(ValueError, match="EMPTY_CANDIDATE_IDENTITY"):
        validate(evidence)


def zip_json(member, value):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(member, json.dumps(value))
    return stream.getvalue()


def artifact(name, data, number=1):
    return {
        "id": number,
        "name": name,
        "expired": False,
        "workflow_run": {"id": int(RUN_ID), "head_sha": COMMIT},
        "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
    }


def test_zip_download_digest_is_checked_before_reading_members():
    data = zip_json("results.json", {"value": "verified"})
    record = artifact("results", data)
    assert gate.read_verified_json(data, record, "results.json") == {"value": "verified"}
    with pytest.raises(ValueError, match="DIGEST_MISMATCH"):
        gate.read_verified_json(data + b"corruption", record, "results.json")
    with pytest.raises(ValueError, match="MEMBER_MISSING"):
        gate.read_verified_json(data, record, "missing.json")


def test_json_member_with_symlink_type_is_rejected():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        info = zipfile.ZipInfo("results.json")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "{}")
    data = stream.getvalue()
    with pytest.raises(ValueError, match="MEMBER_TYPE_OR_SIZE"):
        gate.read_verified_json(data, artifact("results", data), "results.json")


@pytest.mark.parametrize(
    "change", [{"expired": True}, {"digest": None}, {"workflow_run": {"id": 0, "head_sha": COMMIT}}]
)
def test_artifact_run_and_digest_metadata_are_required(change):
    record = {**artifact("expected", b"value"), **change}
    with pytest.raises(ValueError, match="EARLY_SMOKE_ARTIFACT_"):
        gate.select_artifact([record], "expected", run_id=RUN_ID, source_commit=COMMIT)


@pytest.mark.parametrize("invalid", [False, True])
def test_cli_is_readonly_and_keeps_success_or_failure_receipt(
    tmp_path, monkeypatch, evidence, invalid
):
    if invalid:
        evidence["result"]["attempts"][0]["usage"]["unknown_usage_requests"] = 1
    plan_zip = zip_json("context-plan.json", evidence["manifest"])
    results_zip = zip_json("results.json", evidence["result"])
    archives = {1: plan_zip, 2: results_zip}
    artifacts = [
        artifact(f"context-plan-{RUN_ID}", plan_zip, 1),
        artifact(f"context-results-{RUN_ID}", results_zip, 2),
    ]
    for index, row in enumerate(evidence["manifest"]["attempts"], start=3):
        artifacts.append(artifact(f"context-raw-{RUN_ID}-{row['job_key']}", b"raw", index))
    calls = []

    def fetch(endpoint, *, paginate=False):
        calls.append((endpoint, paginate))
        return [{"artifacts": artifacts}] if paginate else evidence["run"]

    def download(repository, number, path):
        assert repository == REPOSITORY and number in archives
        path.write_bytes(archives[number])
        return archives[number]

    output = tmp_path / "gate.json"
    monkeypatch.setenv("GITHUB_SHA", COMMIT)
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setattr(gate, "gh_json", fetch)
    monkeypatch.setattr(gate, "download_artifact", download)
    monkeypatch.setattr(gate.shared, "read_protocol", lambda _: evidence["arguments"]["protocol"])
    monkeypatch.setattr(gate.shared, "sha", lambda _: evidence["arguments"]["protocol_sha256"])
    monkeypatch.setattr(gate.shared, "source_hashes", lambda: evidence["arguments"]["sources"])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_early_smoke.py",
            "--run-id",
            RUN_ID,
            "--protocol",
            "frozen.json",
            "--output",
            str(output),
        ],
    )
    assert gate.main() == (2 if invalid else 0)
    receipt = json.loads(output.read_text())
    assert receipt["passed"] is (not invalid)
    assert receipt["new_model_requests"] == 0 and receipt["github_access"] == "read_only"
    assert all(a["digest_verified"] for a in receipt["verified_artifacts"])
    assert len(calls) == 2
    if invalid:
        assert receipt["error"] == "EARLY_SMOKE_USAGE_UNKNOWN_OR_BUDGET"
    else:
        assert len(receipt["raw_artifacts"]) == 3
        assert all("/artifacts/" in a["url"] for a in receipt["raw_artifacts"])
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        gate.main()
    assert output.read_bytes() == original


def test_github_read_uses_structured_get_arguments(monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(stdout=b'{"ok":true}')

    monkeypatch.setattr(gate.subprocess, "run", run)
    assert gate.gh_json("repos/owner/repo/actions/runs/1") == {"ok": True}
    command, options = calls[0]
    assert command == [
        "gh",
        "api",
        "--hostname",
        "github.com",
        "--method",
        "GET",
        "repos/owner/repo/actions/runs/1",
    ]
    assert options["check"] is True and "shell" not in options
