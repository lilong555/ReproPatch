"""Offline scheduling, stage gates and independent localization campaign contracts."""

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import localization_ablation as campaign
from actions_benchmark import pack
from benchmark_budget import LocalUsageLedger


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_RUN_ID", "9001")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("RUNNER_NAME", "local-test")
    monkeypatch.setenv("GITHUB_JOB", "attempt")
    monkeypatch.setattr(campaign, "source_hashes", lambda: {"src/frozen.py": "a" * 64})
    p = campaign.read_protocol()
    gate = {
        "schema": "repropatch.localization-ablation.gate.v1",
        **campaign.gate_identity(p, "smoke", campaign.PROTOCOL),
        "passed": True,
        "offline_passed": True,
        "ci": {"conclusion": "success"},
    }
    gate_path = tmp_path / "gate.json"
    campaign.save(gate_path, gate)
    path = tmp_path / "plan.json"
    campaign.plan(
        SimpleNamespace(
            protocol=campaign.PROTOCOL, scope="smoke", output=path, dry_run=False, gate=gate_path
        )
    )
    return path, campaign.load(path)


def args_for(frozen, output):
    path, m = frozen
    return SimpleNamespace(
        manifest=path,
        protocol=campaign.PROTOCOL,
        scope=m["scope"],
        attempt_id=m["attempts"][0]["attempt_id"],
        trial_index=None,
        output=output,
    )


def test_frozen_allocations_block_pairing_and_namespace():
    p = campaign.read_protocol()
    full, smoke = campaign.trials(p, "full"), campaign.trials(p, "smoke")
    assert len(full) == len({r["attempt_id"] for r in full}) == 114
    assert len(smoke) == 3
    assert sum(r["request_cap"] for r in full) == 2736
    assert sum(r["request_cap"] for r in smoke) == 72
    assert Counter(r["arm"] for r in full) == dict.fromkeys(campaign.ARMS, 38)
    assert not {r["attempt_id"] for r in full} & {r["attempt_id"] for r in smoke}
    for offset in range(0, len(full), 3):
        group = full[offset : offset + 3]
        assert len({(r["instance_id"], r["repeat"]) for r in group}) == 1
        assert {r["arm"] for r in group} == set(campaign.ARMS)
        assert [r["block_position"] for r in group] == [0, 1, 2]
    assert len({tuple(r["arm"] for r in full[i : i + 3]) for i in range(0, 114, 3)}) > 1
    assert campaign.trials(p, "full") == full
    assert p["model"] == "gpt-6-luna" and p["reasoning_effort"] == "max"
    assert p["retries"] == 0 and p["model_timeout_seconds"] == 600
    policy = campaign.context_policy(p)
    assert all(getattr(policy, flag) is False for flag in campaign.shared.FLAGS)
    assert p["phase_contract"] == campaign.PHASE_CONTRACT


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"localization_tool_budget": 9}, "ALLOCATION"),
        ({"localization_step_budget": True}, "ALLOCATION"),
        ({"semantic_state": True}, "COMMON_CONTEXT"),
        ({"context_arm": "combined"}, "COMMON_CONTEXT"),
        ({"max_parallel": 9}, "ALLOCATION"),
        ({"model": "other"}, "PARENT_OVERRIDE"),
        ({"retries": 1}, "PARENT_OVERRIDE"),
        ({"parent_protocol_sha256": "0" * 64}, "PARENT_HASH"),
        ({"phase_contract": {}}, "PHASE_CONTRACT"),
    ],
)
def test_protocol_rejects_intervention_drift(tmp_path, change, reason):
    p = campaign.load(campaign.PROTOCOL)
    path = tmp_path / "protocol.json"
    campaign.save(path, {**p, **change})
    with pytest.raises(ValueError, match=reason):
        campaign.read_protocol(path)


def test_worker_flags_and_no_semantic_side_intervention(frozen, tmp_path):
    _, m = frozen
    for row in m["attempts"]:
        command = campaign.worker_command(row, {"task": "task.yaml"}, tmp_path, m["protocol"])
        for option, expected in (
            ("--localization-mode", row["arm"]),
            ("--localization-tool-budget", "8"),
            ("--localization-step-budget", "4"),
            ("--tool-mode", "legacy"),
            ("--reasoning-effort", "max"),
            ("--localization-feedback-file", str(tmp_path / "visible-feedback.json")),
        ):
            assert command[command.index(option) + 1] == expected
        assert "--semantic-state" not in command
        assert "--candidate-only" in command and "--compiler-cache" in command


def test_dry_plan_never_executes_and_live_plan_requires_gates(tmp_path):
    args = SimpleNamespace(
        protocol=campaign.PROTOCOL, scope="full", output=tmp_path / "dry.json", dry_run=True
    )
    campaign.plan(args)
    with pytest.raises(ValueError, match="DRY_PLAN"):
        campaign.read_manifest(args.output, execution=True)
    args.output = tmp_path / "live.json"
    args.dry_run = False
    with pytest.raises(ValueError, match="GATE"):
        campaign.plan(args)
    assert not args.output.exists()


def test_manifest_execution_identity_and_no_rerun(frozen, monkeypatch):
    path, m = frozen
    assert campaign.read_manifest(path, execution=True) == m
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    with pytest.raises(ValueError, match="RERUN"):
        campaign.read_manifest(path, execution=True)
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setattr(campaign, "source_hashes", lambda: {})
    with pytest.raises(ValueError, match="SOURCE_CHANGED"):
        campaign.read_manifest(path, execution=True)


def test_ci_requires_all_three_jobs_and_exact_source():
    p = campaign.read_protocol()
    run = {
        "head_sha": "abc",
        "event": "workflow_dispatch",
        "path": ".github/workflows/ci.yml",
        "status": "completed",
        "conclusion": "success",
    }
    jobs = [{"name": name, "conclusion": "success"} for name in p["gates"]["ci_jobs"]]
    campaign.validate_ci(run, jobs, "abc", p)
    with pytest.raises(ValueError, match="CI_JOB"):
        campaign.validate_ci(run, jobs[:-1], "abc", p)
    with pytest.raises(ValueError, match="CI_SOURCE"):
        campaign.validate_ci(run, jobs, "other", p)
    with pytest.raises(ValueError, match="CI_SOURCE"):
        campaign.validate_ci({**run, "event": "pull_request"}, jobs, "abc", p)


def smoke_result(m):
    rows = [
        {
            **row,
            "schema": "repropatch.localization-ablation.result.v1",
            "manifest_sha256": m["manifest_sha256"],
            "protocol_sha256": m["protocol_sha256"],
            "source_sha256": m["source_sha256"],
            "accepted": False,
            "classification": "candidate",
            "failure": None,
            "usage": {
                "requests": 2,
                "unknown_usage_requests": 0,
                "input_tokens": 100,
                "output_tokens": 20,
            },
            "localization_score": {
                "schema": "repropatch.localization-score.v1",
                "attempt_id": row["attempt_id"],
                "evidence_status": "complete",
                "exposures": [{}],
                "phase_finished": {"reason": "final"},
            },
            "prepared_identity": {"visible_feedback_sha256": "b" * 64},
        }
        for row in m["attempts"]
    ]
    return {
        "schema": "repropatch.localization-ablation.aggregate.v1",
        "scope": "smoke",
        "protocol_sha256": m["protocol_sha256"],
        "source_sha256": m["source_sha256"],
        "attempts": rows,
        "rejected_artifacts": [],
    }


def test_smoke_accepts_failed_repairs_with_complete_plumbing(frozen):
    _, m = frozen
    result = smoke_result(m)
    gate = campaign.validate_smoke(result, m["protocol"], m["protocol_sha256"], m["source_sha256"])
    assert gate["passed"] is True


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"accepted": None}, "COLD_SCORE"),
        ({"usage": {"requests": 0, "unknown_usage_requests": 0}}, "USAGE"),
        ({"usage": {"requests": 1, "unknown_usage_requests": 1}}, "USAGE"),
        ({"localization_score": {}}, "LOCALIZATION_SCORE"),
        ({"prepared_identity": {"visible_feedback_sha256": "different"}}, "FIXED_FEEDBACK"),
    ],
)
def test_smoke_gate_rejects_missing_measurements(frozen, change, reason):
    _, m = frozen
    result = smoke_result(m)
    result["attempts"][0].update(change)
    with pytest.raises(ValueError, match=reason):
        campaign.validate_smoke(result, m["protocol"], m["protocol_sha256"], m["source_sha256"])


def test_all_19_feedback_packages_are_canonical_and_public_only():
    p = campaign.read_protocol()
    for instance in p["tasks"]:
        value = campaign.visible_feedback(p, instance, "0" * 64)
        again = campaign.visible_feedback(p, instance, "0" * 64)
        assert value == again
        assert value["instance_id"] == instance.replace("__", "-").lower()
        assert set(value) == {
            "schema",
            "instance_id",
            "prepared_commit",
            "source_tree_sha256",
            "logs",
            "feedback_sha256",
        }
        body = {k: v for k, v in value.items() if k != "feedback_sha256"}
        assert value["feedback_sha256"] == hashlib.sha256(campaign.canonical_json(body)).hexdigest()
        assert len(campaign.canonical_json(value)) <= 2 * 1024 * 1024
        assert {r["name"] for r in value["logs"]} == {
            "baseline-build.log",
            "baseline-configure.log",
            "baseline-ctest.log",
        }
        for log in value["logs"]:
            assert hashlib.sha256(log["text"].encode()).hexdigest() == log["sha256"]


def test_archive_roundtrip_and_tamper_rejection(tmp_path):
    source = tmp_path / "raw"
    source.mkdir()
    (source / "result.json").write_text('{"accepted": false}\n')
    path = tmp_path / "evidence.tar.gz"
    pack(SimpleNamespace(source=source, output=path))
    destination = tmp_path / "restored"
    campaign.unpack(SimpleNamespace(archive=path, output=destination))
    assert (destination / "result.json").read_bytes() == (source / "result.json").read_bytes()
    with path.open("ab") as stream:
        stream.write(b"tampered")
    with pytest.raises(ValueError, match="ARCHIVE_HASH"):
        campaign.unpack(SimpleNamespace(archive=path, output=tmp_path / "other"))


def test_aggregate_retains_every_missing_trial(frozen, tmp_path):
    path, m = frozen
    source = tmp_path / "results"
    source.mkdir()
    # Full aggregation retains missing runs without applying the smoke promotion gate.
    m["scope"] = "full"
    m["attempts"] = campaign.trials(m["protocol"], "full")
    m["matrix"] = {"include": m["attempts"]}
    m["trial_count"], m["request_cap"] = 114, 2736
    m["manifest_sha256"] = campaign.digest({k: v for k, v in m.items() if k != "manifest_sha256"})
    campaign.save(path, m)
    target = tmp_path / "aggregate"
    campaign.aggregate(
        SimpleNamespace(
            manifest=path, protocol=campaign.PROTOCOL, scope="full", source=source, output=target
        )
    )
    result = campaign.load(target / "results.json")
    assert result["registered_trials"] == 114
    assert all(
        row["accepted"] is None and row["classification"] == "missing" for row in result["attempts"]
    )
    assert all(arm["input_tokens"]["all_trial_mean"] is None for arm in result["arms"].values())


def test_workflow_chains_scopes_and_preserves_shared_queue():
    formal = yaml.safe_load((campaign.ROOT / ".github/workflows/formal-benchmark.yml").read_text())
    reuse = yaml.safe_load(
        (campaign.ROOT / ".github/workflows/localization-ablation.yml").read_text()
    )
    assert formal["concurrency"]["queue"] == "max"
    assert formal["concurrency"]["cancel-in-progress"] is False
    assert "localization-ablation" in formal["concurrency"]["group"]
    assert "context-ablation-cpa-8" in formal["concurrency"]["group"]
    assert formal["jobs"]["localization-full"]["needs"] == "localization-smoke"
    assert formal["jobs"]["localization-full"]["with"]["scope"] == "full"
    assert reuse["jobs"]["attempt"]["strategy"]["max-parallel"] == 8
    assert reuse["jobs"]["score"]["needs"] == ["plan", "attempt"]
    assert "secrets." not in json.dumps(reuse["jobs"]["score"])
    for job in reuse["jobs"].values():
        for step in job["steps"]:
            if "artifact@" in step.get("uses", ""):
                name = step.get("with", {}).get("name") or step["with"].get("pattern", "")
                assert "inputs.scope" in name


def test_worker_generation_never_invokes_scorer(frozen, tmp_path, monkeypatch):
    _, m = frozen
    row = m["attempts"][0]
    output = tmp_path / "attempt"
    output.mkdir()
    campaign.save(
        output / "trial.json",
        {
            **row,
            "manifest_sha256": m["manifest_sha256"],
            "runner": campaign.shared.runner_identity(),
        },
    )
    campaign.save(output / "runner-status.json", {"state": "PREPARED"})
    settings = {}
    identity = {}
    for name, key in (
        ("task", "task_sha256"),
        ("qualification_projection", "qualification_projection_sha256"),
        ("common_input", "common_input_sha256"),
    ):
        file = output / (name + ".json")
        file.write_text("{}")
        settings[name] = str(file)
        identity[key] = campaign.sha(file)
    campaign.save(output / "prepared/prepared.json", settings)
    identity["prepared_sha256"] = campaign.sha(output / "prepared/prepared.json")
    for relative, key in (
        ("prepared/source-base.tar", "source_base_sha256"),
        ("prepared/source-base.bundle", "source_bundle_sha256"),
        ("visible-feedback.json", "visible_feedback_sha256"),
    ):
        file = output / relative
        file.write_text("{}")
        identity[key] = campaign.sha(file)
    campaign.save(output / "prepared-identity.json", identity)
    LocalUsageLedger.create_scoped(
        output / "usage.sqlite3",
        {row["attempt_id"]: 24},
        context_policy=campaign.context_policy(m["protocol"]),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "offline-placeholder")

    class Session:
        def __init__(self, directory, campaign):
            assert campaign == "localization-ablation-20261106"
            directory.mkdir()
            (directory / "lease-events.jsonl").write_text(
                json.dumps({"action": "enter", "result": {"request_retry": 0}}) + "\n"
            )

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def healthy(self):
            pass

        def claim(self, attempt, scope, cap):
            assert (attempt, scope, cap) == (row["attempt_id"], "smoke", 24)
            return {"attempt_id": attempt}

    calls = []

    def execute(command, *args):
        calls.append(command)
        campaign.save(output / "worker/result.json", {"native_status": "CANDIDATE"})
        return 0

    monkeypatch.setattr(campaign, "CPASession", Session)
    monkeypatch.setattr(campaign.shared, "supervised", execute)
    assert campaign.run(args_for(frozen, output)) == 0
    assert len(calls) == 1 and "run_benchmark_agent.py" in calls[0][1]
    assert campaign.load(output / "runner-status.json")["state"] == "AWAITING_ISOLATED_SCORING"
    with pytest.raises(ValueError, match="PREPARED_REQUIRED"):
        campaign.run(args_for(frozen, output))


def test_frozen_base_archive_matches_runtime_manifest_with_export_attributes(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "main.cpp").write_text("int main() { return 0; }\n")
    (repository / ".gitattributes").write_text("main.cpp export-ignore\n")
    for args in (
        ("init", "--template=", "-q"),
        ("config", "user.name", "test"),
        ("config", "user.email", "test@example.invalid"),
        ("add", "."),
        ("commit", "-qm", "source"),
    ):
        subprocess.run(["git", "-C", str(repository), *args], check=True)
    commit = subprocess.check_output(
        ["git", "-C", str(repository), "rev-parse", "HEAD"], text=True
    ).strip()
    output = tmp_path / "attempt"
    prepared = output / "prepared"
    prepared.mkdir(parents=True)
    tree_hash = campaign.freeze_base_source(
        SimpleNamespace(repository=repository, revision=commit), prepared
    )
    qualification = prepared / "contract/result.json"
    campaign.save(qualification, {})
    campaign.save(qualification.parent / "manifest.json", {"repository/main.cpp": {}})
    campaign.save(prepared / "prepared.json", {"qualification": str(qualification)})
    campaign.save(
        output / "prepared-identity.json",
        {
            "source_tree_sha256": tree_hash,
            "source_base_sha256": campaign.sha(prepared / "source-base.tar"),
            "source_bundle_sha256": campaign.sha(prepared / "source-base.bundle"),
        },
    )
    monkeypatch.setattr(
        campaign,
        "restore_private_qualification",
        lambda *args: campaign.restore_bundle_repository(
            prepared / "source-base.bundle", qualification.parent / "repository", commit, tree_hash
        ),
    )
    source = campaign.restore_scoring_base(output)
    assert (source / "main.cpp").read_text() == (repository / "main.cpp").read_text()
    assert campaign.source_manifest(source).sha256 == tree_hash
    assert (qualification.parent / "repository/main.cpp").is_file()
    assert not (prepared / "feedback-worktree").exists()


def test_default_promotion_requires_all_three_pre_registered_conditions():
    localized = {
        "missing_label_tasks": 0,
        "eligible_tasks": 1,
        "expected_runs": 6,
        "complete_score_runs": 6,
        "paired": [
            {
                "contrast": "bounded-native",
                "metric": "capped_first_hit_tools",
                "task_denominator": 1,
                "mean_difference": -1,
            }
        ],
    }
    pairs = [
        {
            "left": "native",
            "right": "bounded",
            "task_means": [{"input_tokens_difference": -10, "pass_difference": 0}],
        }
    ]
    assert campaign.default_decisions(localized, pairs)[0]["default_criteria_met"]
    pairs[0]["task_means"][0]["pass_difference"] = -0.5
    assert not campaign.default_decisions(localized, pairs)[0]["default_criteria_met"]
    pairs[0]["task_means"][0].update(pass_difference=0, input_tokens_difference=1)
    assert not campaign.default_decisions(localized, pairs)[0]["default_criteria_met"]
    pairs[0]["task_means"][0]["input_tokens_difference"] = None
    assert not campaign.default_decisions(localized, pairs)[0]["evidence_complete"]


def test_full_preflight_consumes_same_run_smoke_before_parent_run_finishes(
    frozen, tmp_path, monkeypatch
):
    _, m = frozen
    p = m["protocol"]
    ci = {
        "id": 777,
        "head_sha": campaign.source_commit(),
        "event": "workflow_dispatch",
        "path": ".github/workflows/ci.yml",
        "status": "completed",
        "conclusion": "success",
    }
    calls = []

    def api(*args):
        endpoint = args[-1]
        if "workflows/ci.yml/runs" in endpoint:
            return {"workflow_runs": [ci]}
        if endpoint.endswith("jobs?per_page=100"):
            return [
                {
                    "jobs": [
                        {"name": name, "conclusion": "success"} for name in p["gates"]["ci_jobs"]
                    ]
                }
            ]
        if endpoint.endswith("runs/9001"):
            return {
                "head_sha": campaign.source_commit(),
                "status": "in_progress",
                "conclusion": None,
            }
        raise AssertionError(endpoint)

    def command(argv, **kwargs):
        calls.append(argv)
        if argv[:3] == ["gh", "run", "download"]:
            assert argv[argv.index("--name") + 1] == "localization-results-9001-smoke"
            destination = Path(argv[argv.index("--dir") + 1])
            campaign.save(destination / "results.json", smoke_result(m))
        else:
            assert argv[1:4] == ["-m", "pytest", "-q"]
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(campaign, "gh_json", api)
    # Keep source_commit's git read separate from the mocked subprocess runner.
    commit = campaign.source_commit()
    monkeypatch.setattr(campaign, "source_commit", lambda: commit)
    monkeypatch.setattr(campaign.subprocess, "run", command)
    target = tmp_path / "full-gate.json"
    campaign.preflight(
        SimpleNamespace(
            protocol=campaign.PROTOCOL, scope="full", output=target, smoke_run="9001", wait_ci=0
        )
    )
    gate = campaign.load(target)
    assert gate["passed"] is True and gate["smoke"]["passed"] is True
    assert len(calls) == 2


def test_prepare_freezes_feedback_from_real_git_checkout(frozen, task, tmp_path, monkeypatch):
    from repropatch.localization_runtime import validate_feedback

    path, original = frozen
    m = json.loads(json.dumps(original))
    row = m["attempts"][0]
    raw = task.to_dict()
    raw["id"] = row["instance_id"].replace("__", "-").lower()
    task = campaign.Task.from_dict(raw, tmp_path)
    m["protocol"]["task_contracts"][row["instance_id"]] = {
        "execution_task_sha256": hashlib.sha256(task.source_bytes).hexdigest(),
        "prepared_commit": task.revision,
    }
    monkeypatch.setattr(campaign, "read_manifest", lambda *args, **kwargs: m)
    monkeypatch.setattr(campaign, "ROOT", tmp_path)
    monkeypatch.setattr(campaign, "ensure_image", lambda *args: None)

    def prepare(protocol, instance, output):
        assert instance == row["instance_id"]
        output.mkdir()
        task_path = output / "task.yaml"
        task_path.write_bytes(task.source_bytes)
        campaign.save(output / "qualification.json", {})
        campaign.save(output / "common-input.json", {})
        campaign.save(
            output / "prepared.json",
            {
                "task": str(task_path),
                "qualification": str(output / "qualification.json"),
                "qualification_projection": str(output / "qualification.json"),
                "common_input": str(output / "common-input.json"),
            },
        )

    monkeypatch.setattr(campaign, "prepare_public_task", prepare)
    output = tmp_path / "prepared-attempt"
    assert campaign.prepare(args_for((path, m), output)) == 0
    identity = campaign.load(output / "prepared-identity.json")
    feedback = campaign.load(output / "visible-feedback.json")
    assert (
        validate_feedback(feedback, task, source_tree_sha256=identity["source_tree_sha256"])
        == feedback
    )
    assert identity["visible_feedback_sha256"] == campaign.sha(output / "visible-feedback.json")
    assert (output / "prepared/source-base.tar").is_file()
    assert not (output / "prepared/feedback-worktree").exists()
