"""Offline contracts for frozen native trials, unique execution and missing-data summaries."""

import hashlib
import json
import shutil
import sys
import tarfile
from collections import Counter
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from repropatch.task import Task

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import context_ablation as campaign
from benchmark_budget import LocalUsageLedger


@pytest.fixture
def manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_RUN_ID", "9001")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("RUNNER_NAME", "offline-runner")
    monkeypatch.setenv("GITHUB_JOB", "attempt")
    path = tmp_path / "plan.json"
    github_output = tmp_path / "github-output"
    campaign.plan(
        SimpleNamespace(
            protocol=campaign.PROTOCOL,
            scope="smoke",
            output=path,
            github_output=github_output,
        )
    )
    value = campaign.load(path)
    matrix = json.loads(github_output.read_text().removeprefix("matrix="))
    assert matrix == value["matrix"]
    return path, value


def args_for(manifest, output, index=0):
    path, value = manifest
    return SimpleNamespace(
        manifest=path,
        protocol=campaign.PROTOCOL,
        scope=value["scope"],
        attempt_id=value["attempts"][index]["attempt_id"],
        trial_index=None,
        output=output,
    )


def test_population_order_budget_and_isolated_flags():
    p = campaign.read_protocol()
    original = campaign.load(campaign.ROOT / p["task_source"])
    assert p["tasks"] == original["paired_tasks"]
    rows = campaign.trials(p, "full")
    assert len(rows) == len({r["attempt_id"] for r in rows}) == 190
    assert Counter(r["arm"] for r in rows) == dict.fromkeys(campaign.ARMS, 38)
    assert all(n == 5 for n in Counter((r["instance_id"], r["repeat"]) for r in rows).values())
    assert sum(r["request_cap"] for r in rows) == 4560
    assert len(campaign.trials(p, "smoke")) == 5
    assert not (
        {r["attempt_id"] for r in rows} & {r["attempt_id"] for r in campaign.trials(p, "smoke")}
    )
    assert not ({r["attempt_id"] for r in rows} & {r["attempt_id"] for r in original["attempts"]})
    for arm in campaign.ARMS:
        context_policy = campaign.context_policy(p, arm)
        assert {k: getattr(context_policy, k) for k in campaign.FLAGS} == p["treatments"][arm]
        policy = {k: v for k, v in context_policy.to_dict().items() if k not in campaign.FLAGS}
        assert policy == p["context_policy"]
    assert (
        policy["context_window_tokens"],
        policy["compact_trigger_tokens"],
        policy["compact_target_tokens"],
    ) == (128000, 48000, 21600)


def test_manifest_is_bound_to_source_run_and_first_attempt(manifest, monkeypatch):
    path, value = manifest
    assert campaign.read_manifest(path, execution=True) == value
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    with pytest.raises(ValueError, match="RERUN"):
        campaign.read_manifest(path, execution=True)
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("GITHUB_RUN_ID", "9002")
    with pytest.raises(ValueError, match="RUN_ID_CHANGED"):
        campaign.read_manifest(path, execution=True)
    monkeypatch.setenv("GITHUB_RUN_ID", "9001")
    monkeypatch.setattr(campaign, "source_hashes", lambda: {"different.py": "new"})
    with pytest.raises(ValueError, match="SOURCE_CHANGED"):
        campaign.read_manifest(path, execution=True)


def test_manifest_tampering_and_output_reuse_fail(manifest):
    path, value = manifest
    with pytest.raises(FileExistsError):
        campaign.exclusive_save(path, value)
    value["attempts"][0]["request_cap"] = 48
    campaign.save(path, value)
    with pytest.raises(ValueError, match="MANIFEST_HASH"):
        campaign.read_manifest(path)


def test_native_command_preserves_tools_and_checks(manifest, tmp_path):
    _, value = manifest
    row = value["attempts"][0]
    command = campaign.worker_command(row, {"task": "task.yaml"}, tmp_path, value["protocol"])
    for flag, expected in (
        ("--agent", "repropatch"),
        ("--tool-mode", "legacy"),
        ("--intermediate-checks", "enabled"),
        ("--reasoning-effort", "max"),
        ("--cpa-route", "azure-ssh"),
    ):
        assert command[command.index(flag) + 1] == expected
    assert "--compiler-cache" in command and "--candidate-only" in command
    assert "--semantic-state" not in command


def test_prepare_failure_has_zero_request_ledger_and_durable_status(
    manifest,
    tmp_path,
    monkeypatch,
):
    real_root = campaign.ROOT
    monkeypatch.setattr(campaign, "read_manifest", lambda *a, **k: manifest[1])
    monkeypatch.setattr(campaign, "ROOT", tmp_path)
    monkeypatch.setattr(
        campaign,
        "prepare_inputs",
        lambda *a: (_ for _ in ()).throw(ValueError("QUALIFICATION_ARCHIVES_REQUIRED")),
    )
    args = args_for(manifest, tmp_path / "trial")
    assert campaign.prepare(args) == 2
    summary = campaign.load(args.output / "summary.json")
    assert summary["classification"] == "preparation"
    assert summary["usage"]["requests"] == 0
    assert summary["usage"]["input_tokens"] == 0
    assert campaign.load(args.output / "runner-status.json")["state"] == "PREPARATION_FAILED"
    with pytest.raises(FileExistsError):
        campaign.prepare(args)
    assert real_root != campaign.ROOT


def fake_prepared(manifest, output):
    _, m = manifest
    row = m["attempts"][0]
    output.mkdir()
    campaign.save(
        output / "trial.json",
        {**row, "manifest_sha256": m["manifest_sha256"], "runner": campaign.runner_identity()},
    )
    campaign.status(output, "PREPARED", **row)
    LocalUsageLedger.create_scoped(
        output / "usage.sqlite3",
        {row["attempt_id"]: 24},
        context_policy=campaign.context_policy(m["protocol"], row["arm"]),
    )
    for name in ("task.yaml", "qualification.json", "input.json"):
        campaign.save(output / name, {})
    settings = {
        "task": str(output / "task.yaml"),
        "qualification": str(output / "qualification.json"),
        "common_input": str(output / "input.json"),
    }
    campaign.save(output / "prepared/prepared.json", settings)
    campaign.save(
        output / "prepared-identity.json",
        {
            "task_sha256": campaign.sha(output / "task.yaml"),
            "qualification_sha256": campaign.sha(output / "qualification.json"),
            "common_input_sha256": campaign.sha(output / "input.json"),
            "prepared_sha256": campaign.sha(output / "prepared/prepared.json"),
        },
    )


@pytest.mark.parametrize("failure_stage", [None, "heartbeat", "claim", "worker_start"])
def test_cpa_lifecycle_metering_and_cold_score_are_separate(
    manifest,
    tmp_path,
    monkeypatch,
    failure_stage,
):
    args = args_for(manifest, tmp_path / "trial")
    fake_prepared(manifest, args.output)
    monkeypatch.setenv("OPENAI_API_KEY", "offline-key-never-sent")
    calls = []

    class Session:
        def __init__(self, evidence, *, campaign):
            assert campaign == "context-ablation-20261106"
            self.evidence = evidence

        def __enter__(self):
            calls.append("enter")
            self.evidence.mkdir()
            # CPASession writes one complete JSON object per line.
            (self.evidence / "lease-events.jsonl").write_text(
                json.dumps({"action": "enter", "result": {"request_retry": 0}}) + "\n"
            )
            return self

        def healthy(self):
            calls.append("healthy")
            if failure_stage == "heartbeat" and "worker" in calls:
                raise RuntimeError("CPA_TUNNEL_OR_HEARTBEAT_LOST")

        def __exit__(self, *a):
            calls.append("close")

        def claim(self, attempt, phase, cap):
            assert "enter" in calls and "worker" not in calls
            assert (attempt, phase, cap) == (args.attempt_id, "smoke", 24)
            calls.append("claim")
            if failure_stage == "claim":
                raise RuntimeError("CPA_ATTEMPT_ALREADY_CLAIMED")
            return {
                "status": "CLAIMED",
                "attempt_id": attempt,
                "phase": phase,
                "request_cap": cap,
                "run_id": "9001",
            }

    def supervised(command, log, timeout, p, session=None):
        if session:
            assert calls.count("claim") == 1
            assert campaign.load(args.output / "cpa/claim.json")["status"] == "CLAIMED"
            calls.append("worker")
            if failure_stage == "worker_start":
                raise OSError("worker startup failed after persistent claim")
            campaign.save(args.output / "worker/result.json", {"context": {}})
        else:
            assert "close" in calls
            calls.append("score")
            campaign.save(
                args.output / "score/score.json",
                {
                    "accepted": False,
                    "classification": "candidate",
                    "status": "EMPTY_CANDIDATE",
                },
            )
        return 0

    monkeypatch.setattr(campaign, "CPASession", Session)
    monkeypatch.setattr(campaign, "supervised", supervised)
    assert campaign.run(args) == (2 if failure_stage else 0)
    assert calls.count("claim") == calls.count("close") == 1
    assert calls.count("worker") == (0 if failure_stage == "claim" else 1)
    assert calls.count("score") == (0 if failure_stage in {"claim", "worker_start"} else 1)
    row = campaign.load(args.output / "summary.json")
    assert row["accepted"] is (None if failure_stage else False)
    assert row["usage"]["requests"] == 0
    if failure_stage == "claim":
        assert row["cpa_claim"] == {}
        assert row["runner_status"]["error_message"] == "CPA_ATTEMPT_ALREADY_CLAIMED"
    else:
        assert row["cpa_claim"]["status"] == "CLAIMED"
    assert "offline-key-never-sent" not in json.dumps(row)
    with pytest.raises(ValueError, match="PREPARED_REQUIRED"):
        campaign.run(args)


def test_unknown_usage_propagates_and_failed_trials_stay_in_mean():
    rows = [
        {"accepted": True, "usage": {"unknown_usage_requests": 0, "input_tokens": 100}},
        {"accepted": False, "usage": {"unknown_usage_requests": 0, "input_tokens": 300}},
    ]
    assert campaign.token_statistics(rows, "input_tokens")["all_trial_mean"] == 200
    rows.append({"usage": {"unknown_usage_requests": 1, "input_tokens": 0}})
    result = campaign.token_statistics(rows, "input_tokens")
    assert result["all_trial_mean"] is None
    assert result["observed_trial_mean"] == 200 and result["missing_trials"] == 1


def test_mechanism_coverage_uses_receipts_and_explicit_missing():
    p = campaign.read_protocol()
    worker = {
        "context": {
            "optimization_state": {
                "metrics": {
                    "diagnostic_extraction": {"triggers": 3, "attempts": 8, "saved_bytes": 120},
                    "deduplicate_results": {"triggers": 0, "attempts": 8},
                }
            }
        }
    }
    metrics = campaign.mechanism_metrics(worker, p, "combined")
    assert metrics["diagnostic_extraction"]["trigger_count"] == 3
    assert metrics["deduplicate_results"]["trigger_count"] == 0
    assert metrics["state_aware_compaction"]["trigger_count"] is None
    assert (
        campaign.mechanism_metrics({"context": {}}, p, "baseline")["diagnostic_extraction"][
            "trigger_count"
        ]
        == 0
    )


def test_aggregate_retains_missing_interrupted_duplicates_and_rejects_history(
    manifest,
    tmp_path,
):
    path, m = manifest
    source = tmp_path / "downloaded"
    source.mkdir()
    rows = m["attempts"]
    row = {
        **rows[0],
        "schema": "repropatch.context-ablation.result.v1",
        "manifest_sha256": m["manifest_sha256"],
        "source_sha256": m["source_sha256"],
        "accepted": False,
        "classification": "candidate",
        "usage": {
            "unknown_usage_requests": 0,
            "input_tokens": 100,
            "output_tokens": 20,
        },
    }
    campaign.save(source / "one/summary.json", row)
    campaign.save(source / "duplicate/summary.json", row)
    campaign.save(
        source / "interrupt/runner-status.json",
        {
            **rows[1],
            "manifest_sha256": m["manifest_sha256"],
            "state": "RUNNING",
        },
    )
    campaign.save(source / "old/summary.json", {"schema": "old-campaign", "accepted": True})
    out = tmp_path / "aggregate"
    campaign.aggregate(
        SimpleNamespace(manifest=path, protocol=campaign.PROTOCOL, source=source, output=out)
    )
    result = campaign.load(out / "results.json")
    assert result["registered_trials"] == 5
    assert Counter(r["classification"] for r in result["attempts"]) == {
        "missing": 3,
        "infrastructure": 2,
    }
    assert len(result["rejected_artifacts"]) == 1
    assert len(result["paired_differences"]) == 10
    assert all(
        arm["N"] == 1 and arm["input_tokens"]["all_trial_mean"] is None
        for arm in result["arms"].values()
    )


def test_pairing_uses_task_and_repeat_with_right_minus_left():
    rows = []
    for repeat, base, treated in ((1, False, True), (2, None, False)):
        for arm, accepted in (("baseline", base), ("diagnostics", treated)):
            rows.append(
                {
                    "instance_id": "fmt",
                    "repeat": repeat,
                    "arm": arm,
                    "accepted": accepted,
                    "classification": "candidate",
                }
            )
    result = campaign.paired_statistics(rows, "baseline", "diagnostics")
    assert result["N"] == 2
    assert result["pass_difference"]["all_pair_mean"] is None
    assert result["pass_difference"]["observed_pair_mean"] == 1
    assert result["pass_difference"]["missing_pairs"] == 1


@pytest.mark.parametrize(
    "reason",
    [
        "MODEL_CONTEXT_EXCEEDED",
        "LOCAL_TRANSPORT_LIMIT",
        "CONTEXT_BUDGET_EXHAUSTED",
        "COMPACTION_FAILED",
    ],
)
def test_overflow_categories_remain_separate(reason):
    assert campaign.overflow_kind(reason, {}) == reason


def test_error_details_redacts_env_secrets(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-example")
    assert campaign.error_details(ValueError("secret-example"))["error_message"] == "[REDACTED]"


def test_workflow_install_failure_is_infrastructure(manifest, tmp_path):
    path, m = manifest
    source = tmp_path / "summaries"
    campaign.save(
        source / "runner-status.json",
        {
            **m["attempts"][0],
            "run_id": m["github_run_id"],
            "source_commit": m["source_commit"],
            "prepare": "skipped",
            "execute": "skipped",
            "job_status": "failure",
        },
    )
    output = tmp_path / "results"
    campaign.aggregate(
        SimpleNamespace(manifest=path, protocol=campaign.PROTOCOL, source=source, output=output)
    )
    rows = campaign.load(output / "results.json")["attempts"]
    assert rows[0]["classification"] == "infrastructure"
    assert rows[0]["usage"] is None
    assert all(row["classification"] == "missing" for row in rows[1:])


def test_formal_prepare_accepts_explicit_configuration_without_global_protocol(
    monkeypatch, tmp_path
):
    import cross_repo_campaign
    import formal_benchmark

    p = {"campaign_schema": "repropatch.cross-repository-campaign.v1"}
    monkeypatch.setattr(formal_benchmark, "protocol", lambda: pytest.fail("global protocol read"))
    monkeypatch.setattr(cross_repo_campaign, "prepare", lambda task, output, arm, value: value)
    assert formal_benchmark.prepare("fmt", tmp_path, configuration=p) is p


@pytest.fixture(scope="module")
def real_qualification_tasks():
    p = campaign.load(campaign.PROTOCOL)
    parent = campaign.load(campaign.ROOT / p["parent_protocol"])
    archives = sorted((campaign.ROOT / "benchmarks/context-ablation/inputs").glob("*.tar.gz"))
    assert sorted(campaign.sha(path) for path in archives) == sorted(
        parent["qualification_archive_sha256"]
    )
    records = {}
    for path in archives:
        with tarfile.open(path) as archive:
            names = set(archive.getnames())
            for task in p["tasks"]:
                prefix = f"qualification/{task}/"
                if prefix + "task.yaml" not in names:
                    continue
                assert task not in records
                records[task] = {
                    name: archive.extractfile(prefix + name).read()
                    for name in ("task.yaml", "result.json", "manifest.json")
                }
    assert set(records) == set(p["tasks"])
    return p, parent, records


@pytest.mark.parametrize("instance", campaign.load(campaign.PROTOCOL)["tasks"])
def test_real_archive_contract_matches_native_preparation(
    instance,
    real_qualification_tasks,
    tmp_path,
):
    from formal_benchmark import prepare_execution_contract

    p, parent, records = real_qualification_tasks
    archived = records[instance]
    raw = yaml.safe_load(archived["task.yaml"])
    original = Task.from_dict(raw, tmp_path).to_dict()
    assert Task.from_dict(raw, tmp_path / "another-base").to_dict() == original
    assert "tmp_executable" not in raw["environment"]
    assert original["environment"]["tmp_executable"] is False
    updated = deepcopy(original)
    overrides = {**p["execution_budget_override"], "model_timeout_seconds": 180}
    updated["budget"].update(overrides)
    task = Task.from_dict(updated, tmp_path)
    contract = p["task_contracts"][instance]
    assert hashlib.sha256(task.source_bytes).hexdigest() == contract["execution_task_sha256"]
    assert (
        task.revision
        == contract["prepared_commit"]
        == parent["task_contracts"][instance]["prepared_commit"]
    )
    assert task.environment.image == p["image_id"]
    assert {k: v for k, v in task.to_dict().items() if k != "budget"} == {
        k: v for k, v in original.items() if k != "budget"
    }
    assert task.to_dict()["budget"] == {**original["budget"], **overrides}
    legacy = deepcopy(updated)
    legacy["environment"].pop("tmp_executable")
    assert (
        hashlib.sha256(Task.from_dict(legacy, tmp_path).source_bytes).hexdigest()
        == (contract["legacy_execution_task_sha256"])
        == parent["task_contracts"][instance]["execution_task_sha256"]
    )
    assert contract["legacy_execution_task_sha256"] != contract["execution_task_sha256"]

    source = tmp_path / "qualification"
    source.mkdir()
    for name, content in archived.items():
        (source / name).write_bytes(content)
    prepared = prepare_execution_contract(
        source,
        tmp_path / "execution",
        p["model_timeout_seconds"],
        p["execution_budget_override"],
    )
    assert (prepared / "task.yaml").read_bytes() == task.source_bytes
    assert campaign.sha(prepared / "task.yaml") == contract["execution_task_sha256"]
    assert (prepared / "native-qualification-task.yaml").read_bytes() == archived["task.yaml"]


@pytest.mark.parametrize(
    "field,reason",
    [
        ("execution_task_sha256", "EXECUTION_TASK_CONTRACT_CHANGED"),
        ("legacy_execution_task_sha256", "LEGACY_TASK_CONTRACT_CHANGED"),
        ("prepared_commit", "PREPARED_COMMIT_CHANGED"),
    ],
)
def test_real_archive_contract_gate_rejects_changed_hashes(field, reason, tmp_path):
    p = campaign.load(campaign.PROTOCOL)
    p["task_contracts"][p["tasks"][0]][field] = "0" * 64
    changed = tmp_path / "protocol.json"
    campaign.save(changed, p)
    with pytest.raises(ValueError, match=reason):
        campaign.read_protocol(changed)


def test_archive_digest_is_verified_before_task_parsing(monkeypatch, tmp_path):
    p = campaign.load(campaign.PROTOCOL)
    source = campaign.ROOT / "benchmarks/context-ablation/inputs"
    destination = tmp_path / "benchmarks/context-ablation/inputs"
    shutil.copytree(source, destination)
    path = next(destination.glob("*.tar.gz"))
    path.write_bytes(path.read_bytes() + b"corrupted")
    monkeypatch.setattr(campaign, "ROOT", tmp_path)
    monkeypatch.setattr(campaign.tarfile, "open", lambda *a, **k: pytest.fail("unverified archive"))
    with pytest.raises(ValueError, match="QUALIFICATION_ARCHIVES_REQUIRED"):
        campaign.archive_task_contracts(p)
