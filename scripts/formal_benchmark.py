"""执行冻结批次的首跑，静态分配请求额度，复用完整冷 Oracle。"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from collections import Counter
from datetime import datetime
from pathlib import Path

from actions_benchmark import save, sha
from benchmark_budget import LocalUsageLedger
from prepare_multiswe_task import git

from repropatch.context import ContextPolicy

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "benchmarks/formal-max-protocol.json"
ATTEMPT_ID = None


def protocol():
    value = json.loads(PROTOCOL.read_text())
    if value.get("campaign_schema") == "repropatch.cross-repository-campaign.v1":
        from cross_repo_campaign import validate_protocol

        validate_protocol(value)
    elif "context_policy" in value:
        from context_campaign import validate_protocol

        validate_protocol(value)
    if "attempts" not in value:
        value["attempts"] = [
            {
                "attempt_id": f"{value['batch_id']}/{task}/{arm}/first",
                "instance_id": task,
                "arm": arm,
                "request_cap": value["request_cap_per_attempt"],
            }
            for task in value["tasks"]
            for arm in value["arms"]
        ]
    assert sum(a["request_cap"] for a in value["attempts"]) == value["formal_request_cap"]
    assert os.environ.get("GITHUB_RUN_ATTEMPT", "1") == "1", "重跑使用新的预注册批次"
    return value


def execution_matrix(p):
    """全量对照按任务和实验臂拆分，单个 Job 只占用一次修复时限。"""
    arms = p["arms"] if p.get("matrix_per_arm") else ["all"]
    matrix = [
        {"instance": task, "arm": arm, "suffix": "" if arm == "all" else "-" + arm}
        for task in p["tasks"]
        for arm in arms
    ]
    if p.get("execution_order"):
        by_key = {(row["instance"], row["arm"]): row for row in matrix}
        return [by_key[(row["instance_id"], row["arm"])] for row in p["execution_order"]]
    return matrix


def run(command, log):
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as stream:
        result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    return result.returncode


def freeze_configuration(output, value):
    from repropatch.harness import implementation_sha256

    save(output / "protocol.json", value)
    save(
        output / "provenance.json",
        {
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "protocol_sha256": sha(PROTOCOL),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "implementation_sha256": implementation_sha256(),
            "context_policy_version": value.get("context_policy", {}).get("context_policy_version"),
            "frozen_execution_commit": value.get("execution_source_commit"),
            "execution_sha256": value.get("execution_sha256"),
        },
    )


def calibrate(output):
    import httpx2

    p = protocol()
    output.mkdir(parents=True, exist_ok=False)
    freeze_configuration(output, p)
    ledger = LocalUsageLedger.create_scoped(output / "usage.sqlite3", {"calibration": 1})
    request = {
        "model": p["model"],
        "reasoning": {"effort": "max"},
        "input": "Reply with exactly OK.",
        "max_output_tokens": 8192,
        "store": False,
    }
    payload = json.dumps(request).encode()
    identity = ledger.reserve("calibration", payload)
    (output / "request.json").write_bytes(payload)
    with httpx2.Client(timeout=90, trust_env=False) as client:
        response = client.post(
            p["endpoint"] + "/responses",
            content=payload,
            headers={
                "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                "Content-Type": "application/json",
            },
        )
    ledger.settle(identity, response.content, response.status_code)
    content = response.content.replace(os.environ["OPENAI_API_KEY"].encode(), b"[REDACTED]")
    (output / "response.json").write_bytes(content)
    observed = response.json()
    valid = response.status_code == 200 and observed.get("reasoning", {}).get("effort") == "max"
    valid = valid and observed.get("status") == "completed"
    valid = valid and ledger.summary()["unknown_usage_requests"] == 0
    save(
        output / "result.json",
        {
            "passed": valid,
            "request_id": identity,
            "reasoning": observed.get("reasoning"),
            **ledger.summary(),
        },
    )
    assert valid, "MAX_CALIBRATION_FAILED"


def verify_calibration(source, output):
    reference = json.loads((ROOT / "benchmarks/formal-max-calibration.json").read_text())
    for name, digest in reference["files"].items():
        assert sha(source / name) == digest, "CALIBRATION_EVIDENCE_CHANGED"
    request = json.loads((source / "request.json").read_text())
    response = json.loads((source / "response.json").read_text())
    p = protocol()
    assert request["model"] == p["model"] and request["reasoning"]["effort"] == "max"
    assert response["status"] == "completed" and response["reasoning"]["effort"] == "max"
    calibration_protocol = json.loads((source / "protocol.json").read_text())
    assert all(
        calibration_protocol[key] == p[key]
        for key in ("model", "endpoint", "reasoning_effort", "max_output_tokens")
    )
    usage = LocalUsageLedger(source / "usage.sqlite3").summary()
    assert usage["requests"] == 1 and usage["unknown_usage_requests"] == 0
    shutil.copytree(source, output)
    save(
        output / "verification.json",
        {
            "passed": True,
            "new_model_requests": 0,
            "execution_protocol_sha256": sha(PROTOCOL),
            **reference,
        },
    )


def pilot_gate(value, p):
    """八个首跑均有冷验收裁决、请求用量闭合，才开放后续任务。"""
    initial = ROOT / "benchmarks/formal-max-protocol.json"
    expected = {a["attempt_id"] for a in json.loads(initial.read_text())["attempts"]}
    rows = value["attempts"]
    assert value["protocol_sha256"] == p["pilot_protocol_sha256"] == sha(initial)
    assert len(rows) == len(expected) and {r["attempt_id"] for r in rows} == expected
    for row in rows:
        score = row["score"]
        assert score["classification"] in {"resolved", "candidate"}, "PILOT_INFRASTRUCTURE"
        assert type(score["accepted"]) is bool, "PILOT_SCORING_INCOMPLETE"
        usage = score["worker_usage"]
        assert 1 <= usage["requests"] <= 12 and usage["unknown_usage_requests"] == 0
    assert sum(row["score"]["worker_usage"]["requests"] for row in rows) <= 96


def verify_pilot(source, output):
    p = protocol()
    if "pilot_completion_run_id" in p:
        verify_completed_pilot(source, output, p)
        return
    value = json.loads((source / "results.json").read_text())
    pilot_gate(value, p)
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(source / "results.json", output / "pilot-results.json")
    save(output / "gate.json", {"passed": True, "pilot_run_id": p["pilot_run_id"]})


def completed_pilot_gate(prior, completion, p):
    """保留首批终止超时，仅以尚未请求过的四项完成对照链路。"""
    config = json.loads((ROOT / "benchmarks/formal-max-completion-protocol.json").read_text())
    completion_gate(prior, config)
    assert completion["protocol_sha256"] == p["completion_protocol_sha256"]
    expected = {a["attempt_id"]: a for a in config["attempts"]}
    rows = completion["attempts"]
    assert len(rows) == 4 and {r["attempt_id"] for r in rows} == expected.keys()
    for row in rows:
        assert row["original_attempt_id"] == expected[row["attempt_id"]]["original_attempt_id"]
        score = row["score"]
        assert score["classification"] in {"resolved", "candidate"}, "COMPLETION_INFRASTRUCTURE"
        assert type(score["accepted"]) is bool
        usage = score["worker_usage"]
        assert 1 <= usage["requests"] <= 12 and usage["unknown_usage_requests"] == 0
    retained = [r for r in prior["attempts"] if r["arm"] in {"full", "no-checks"}]
    assert len(retained) == 4
    for row in retained:
        score = row["score"]
        if row["arm"] == "no-checks":
            assert score["native_reason"] == "MODEL_REQUEST_TIMEOUT"
            assert score["classification"] == "infrastructure"
            assert score["worker_usage"]["unknown_usage_requests"] == 1
        else:
            assert score["classification"] in {"resolved", "candidate"}
            assert type(score["accepted"]) is bool
    total = config["prior_model_requests"] + sum(
        r["score"]["worker_usage"]["requests"] for r in rows
    )
    assert total <= config["parent_request_cap"]
    return retained + rows


def verify_completed_pilot(source, output, p):
    prior_file = source / "prior/results.json"
    assert sha(prior_file) == p["prior_results_sha256"]
    prior = json.loads(prior_file.read_text())
    completion = json.loads((source / "completion/results.json").read_text())
    rows = completed_pilot_gate(prior, completion, p)
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(source, output / "source-results")
    save(output / "combined-pilot-results.json", {"attempts": rows})
    save(
        output / "gate.json",
        {
            "passed": True,
            "pilot_run_id": p["pilot_run_id"],
            "completion_run_id": p["pilot_completion_run_id"],
            "retained_supplier_timeouts": 2,
            "retained_unknown_usage_requests": 2,
        },
    )


def completion_gate(value, p):
    """补齐阶段只接收尚未发出模型请求的实验臂，沿用首批总额度。"""
    assert value["protocol_sha256"] == p["prior_protocol_sha256"]
    rows = {r["attempt_id"]: r for r in value["attempts"]}
    usage = [r["score"]["worker_usage"] for r in rows.values()]
    spent = sum(u["requests"] for u in usage)
    assert spent == p["prior_model_requests"]
    assert sum(u["unknown_usage_requests"] for u in usage) == p["prior_unknown_usage_requests"]
    assert spent + p["formal_request_cap"] <= p["parent_request_cap"]
    for attempt in p["attempts"]:
        original = rows[attempt["original_attempt_id"]]
        assert original["score"]["worker_usage"]["requests"] == 0
        assert original["score"]["oracle_executed"] is False


def verify_completion(source, output):
    value = json.loads((source / "results.json").read_text())
    p = protocol()
    completion_gate(value, p)
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(source / "results.json", output / "prior-results.json")
    save(output / "gate.json", {"passed": True, "prior_run_id": p["prior_run_id"]})


def registry_gate(rows, p):
    """按实际发出的请求确定首跑，保留环境失败和已知终止超时。"""
    assert len({r["attempt_id"] for r in rows}) == len(rows)
    issued = [r for r in rows if r["score"]["worker_usage"]["requests"]]
    used = sum(r["score"]["worker_usage"]["requests"] for r in issued)
    known_timeouts = set(p["known_timeout_attempt_ids"])
    for row in issued:
        score = row["score"]
        usage = score["worker_usage"]
        assert 1 <= usage["requests"] <= 12
        if row["attempt_id"] in known_timeouts:
            expected = p.get("timeout_native_reasons", {}).get(
                row["attempt_id"], "MODEL_REQUEST_TIMEOUT"
            )
            assert score["native_reason"] == expected
            recorded = p.get("timeout_worker_result_sha256", {}).get(row["attempt_id"])
            if recorded:
                assert score["worker_result_sha256"] == recorded
            assert score["classification"] == "infrastructure"
            assert usage["unknown_usage_requests"] == 1
        else:
            assert score["classification"] in {"resolved", "candidate"}, "PILOT_INFRASTRUCTURE"
            assert type(score["accepted"]) is bool and usage["unknown_usage_requests"] == 0
    if p["campaign_stage"] == "mini-completion":
        assert used == p["prior_model_requests"]
        assert used + p["formal_request_cap"] <= p["pilot_request_cap"]
        for attempt in p["attempts"]:
            assert all(
                (r["instance_id"], r["arm"]) != (attempt["instance_id"], attempt["arm"])
                for r in issued
            ), "MODEL_ATTEMPT_ALREADY_ISSUED"
    else:
        expected = {(task, arm) for task in p["pilot_tasks"] for arm in p["arms"]}
        assert len(issued) == len(expected)
        assert {(r["instance_id"], r["arm"]) for r in issued} == expected
        assert used <= p["pilot_request_cap"]
        assert used + p["formal_request_cap"] <= p["campaign_request_cap"]
    return {"passed": True, "prior_model_requests": used, "prior_attempt_records": len(rows)}


def verify_registry(source, output):
    p = protocol()
    rows = []
    for entry in p["prior_results"]:
        file = source / str(entry["run_id"]) / "results.json"
        if entry.get("results_sha256"):
            assert sha(file) == entry["results_sha256"]
        value = json.loads(file.read_text())
        assert value["protocol_sha256"] == entry["protocol_sha256"]
        assert {r["attempt_id"] for r in value["attempts"]} == set(entry["attempt_ids"])
        rows.extend(value["attempts"])
    result = registry_gate(rows, p)
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(source, output / "source-results")
    save(output / "gate.json", result)
    save(output / "prior-attempts.json", {"attempts": rows})


def prepare_execution_contract(
    directory, target, model_timeout_seconds, budget_overrides=None, *, readable_paths=None
):
    """原生资格证据保持原件，执行 Task 单独记录预算与父证据身份。"""
    from repropatch.task import Task

    directory = directory.resolve(strict=True)
    target = target.resolve()
    original = Task.load(directory / "task.yaml")
    overrides = {**(budget_overrides or {}), "model_timeout_seconds": model_timeout_seconds}
    raw = original.to_dict()
    readable_changed = (
        readable_paths is not None and list(readable_paths) != raw["files"]["readable"]
    )
    if (
        all(raw["budget"].get(key) == value for key, value in overrides.items())
        and not readable_changed
    ):
        return directory
    if original.budget.model_timeout_seconds != model_timeout_seconds:
        assert original.budget.model_timeout_seconds == 90 and model_timeout_seconds == 180
    shutil.copytree(directory, target)
    for original_name, parent_name in (
        ("result.json", "native-qualification-parent.json"),
        ("task.yaml", "native-qualification-task.yaml"),
        ("manifest.json", "native-qualification-manifest.json"),
    ):
        shutil.copyfile(directory / original_name, target / parent_name)
    raw["budget"].update(overrides)
    if readable_changed:
        raw["files"]["readable"] = list(readable_paths)
    task = Task.from_dict(raw, target)
    (target / "task.yaml").write_bytes(task.source_bytes)
    parent = directory / "result.json"
    result = json.loads(parent.read_text())
    result.update(
        task_file_sha256=sha(target / "task.yaml"),
        native_qualification_parent_sha256=sha(parent),
        native_qualification_task_sha256=sha(directory / "task.yaml"),
        native_qualification_manifest_sha256=sha(directory / "manifest.json"),
        execution_budget_override=overrides,
    )
    if readable_changed:
        result["execution_readable_policy"] = "utf8-text-v1"
    save(target / "result.json", result)
    manifest = {
        str(file.relative_to(target)): {"size": file.stat().st_size, "sha256": sha(file)}
        for file in sorted(target.rglob("*"))
        if file.is_file() and file != target / "manifest.json" and ".git" not in file.parts
    }
    save(target / "manifest.json", manifest)
    return target


def prepare(instance, output, arm="all"):
    if protocol().get("campaign_schema") == "repropatch.cross-repository-campaign.v1":
        from cross_repo_campaign import prepare

        return prepare(instance, output, arm, protocol())
    from agents.testing import ScriptedModel, assistant_message
    from prepare_mini_environment import MINI_COMMIT
    from qualify_cpp_batch import ADAPTER, BUILD_TEST, archive, records, validate_record

    from repropatch.harness import Harness
    from repropatch.task import Task

    p = protocol()
    assert instance in p["tasks"]
    output.mkdir(parents=True, exist_ok=False)
    freeze_configuration(output, p)
    assert (
        subprocess.check_output(
            ["docker", "image", "inspect", "--format", "{{.Id}}", p["image"]], text=True
        ).strip()
        == p["image_id"]
    )
    # 原始归档经过逐文件清单核验；源码按相同确定性 Git 元数据重建。
    for file in (ROOT / ".repropatch/qualification-input").rglob("*.tar.gz"):
        digest = sha(file)
        assert digest in p["qualification_archive_sha256"]
        shard = file.name.removesuffix(".tar.gz").rsplit("-", 1)[1]
        destination = ROOT / ".repropatch/evidence" / shard
        destination.mkdir(parents=True, exist_ok=True)
        with tarfile.open(file) as data:
            manifest = json.load(data.extractfile("archive-manifest.json"))
            for row in manifest["files"]:
                content = data.extractfile(row["path"]).read()
                assert (
                    len(content) == row["size_bytes"]
                    and hashlib.sha256(content).hexdigest() == row["sha256"]
                )
            data.extractall(destination, filter="data")
    directory = next((ROOT / ".repropatch/evidence").glob("*/qualification/" + instance))
    qualification = json.loads((directory / "result.json").read_text())
    record = next(
        r for r in records(ROOT / ".repropatch/inputs/dataset") if r["instance_id"] == instance
    )
    source = directory / "repository"
    archive(ROOT / ".repropatch/inputs/fmt", record["base"]["sha"], source)
    git(source, "init", "--template=", "-q", ".")
    git(source, "apply", str(directory / "control/test.patch"))
    targets, _ = validate_record(record)
    cmake = source / "test/CMakeLists.txt"
    condition = " OR ".join(f'name STREQUAL "{name}"' for name in targets)
    cmake.write_text(
        cmake.read_text().replace(
            "  add_test(NAME ${name} COMMAND ${name})\n",
            ADAPTER.replace("__CONDITION__", condition),
        )
    )
    (source / "test/repropatch-build-test.cmake").write_text(BUILD_TEST)
    git(source, "add", "-f", ".")
    git(source, "commit", "-qm", "Freeze official regression tests and target-build CTest adapter")
    assert git(source, "rev-parse", "HEAD").decode().strip() == qualification["prepared_commit"]
    manifest = json.loads((directory / "manifest.json").read_text())
    from verify_qualification_evidence import verify_tree

    assert not verify_tree(directory, manifest)
    directory = prepare_execution_contract(
        directory,
        output / "qualified-contract",
        p["model_timeout_seconds"],
        p.get("execution_budget_override"),
    )
    task = Task.load(directory / "task.yaml")
    expected_contract = p.get("task_contracts", {}).get(instance)
    if expected_contract:
        assert sha(directory / "task.yaml") == expected_contract["execution_task_sha256"]
        assert task.revision == expected_contract["prepared_commit"]
    model = ScriptedModel([[assistant_message("基线输入准备完成。")]])
    baseline = Harness(task, model, output / "baseline-runs").run()
    assert baseline["reproduced"] and baseline["cleanup_confirmed"]
    initial = next(Path(baseline["artifact_directory"]).glob("agent/native/0001-input.json"))
    shutil.copyfile(initial, output / "common-input.json")
    mini = ROOT / ".repropatch/mini-source"
    if any(
        a["arm"] in {"mini", "codex"} and a["instance_id"] == instance and arm in {"all", a["arm"]}
        for a in p["attempts"]
    ):
        assert git(mini, "rev-parse", "HEAD").decode().strip() == MINI_COMMIT
    evidence = baseline["baseline"]
    seconds = (
        datetime.fromisoformat(evidence["finished_at"])
        - datetime.fromisoformat(evidence["started_at"])
    ).total_seconds()
    plan = {
        "instance_id": instance,
        "task": str(directory / "task.yaml"),
        "qualification": str(directory / "result.json"),
        "common_input": str(output / "common-input.json"),
        "mini_source": str(mini),
        "agent_seconds": max(
            1, int(task.budget.wall_seconds - task.budget.verification_reserve_seconds - seconds)
        ),
    }
    save(output / "prepared.json", plan)


def execute(instance, output, arm="all"):
    p = protocol()
    settings = json.loads((output / "prepared.json").read_text())
    attempts = [
        a
        for a in p["attempts"]
        if a["instance_id"] == instance
        and arm in {"all", a["arm"]}
        and (ATTEMPT_ID is None or a["attempt_id"] == ATTEMPT_ID)
    ]
    assert attempts, "任务与实验臂须在批次中注册"
    assert len({a["arm"] for a in attempts}) == len(attempts), "重复实验通过独立 Attempt ID 调度"
    agent_python = sys.executable
    mini_python = str(ROOT / ".repropatch/mini-env/bin/python")
    summaries = []
    for attempt in attempts:
        arm = attempt["arm"]
        ledger = output / "ledgers" / (arm + ".sqlite3")
        LocalUsageLedger.create_scoped(
            ledger,
            {attempt["attempt_id"]: attempt["request_cap"]},
            context_policy=ContextPolicy.from_dict(p["context_policy"])
            if "context_policy" in p
            else None,
        )
        target = output / arm
        common = [
            "--task",
            settings["task"],
            "--ledger",
            str(ledger),
            "--attempt",
            attempt["attempt_id"],
            "--output",
            str(target),
            "--reasoning-effort",
            "max",
        ]
        if p.get("cpa_route"):
            common += ["--cpa-route", p["cpa_route"]]
        if arm == "shell-only":
            command = [
                agent_python,
                "scripts/run_benchmark_agent.py",
                "--agent",
                "repropatch",
                "--provider",
                "local-luna",
                "--candidate-only",
                "--tool-mode",
                "shell-only",
                *common,
            ]
        elif arm in {"full", "no-checks"}:
            command = [
                agent_python,
                "scripts/run_benchmark_agent.py",
                "--agent",
                "repropatch",
                "--provider",
                "local-luna",
                "--candidate-only",
                "--compiler-cache",
                "--intermediate-checks",
                "disabled" if arm == "no-checks" else "enabled",
                *common,
            ]
        else:
            environment = output / (arm + "-environment")
            subprocess.run(
                [
                    mini_python,
                    "scripts/prepare_mini_environment.py",
                    "--task",
                    settings["task"],
                    "--mini-source",
                    settings["mini_source"],
                    "--output",
                    str(environment),
                ],
                check=True,
            )
            external = [
                "--mini-source",
                settings["mini_source"],
                "--mini-environment",
                str(environment / "environment.json"),
                "--common-input",
                settings["common_input"],
                "--agent-seconds",
                str(settings["agent_seconds"]),
            ]
            if arm == "mini":
                command = [
                    mini_python,
                    "scripts/run_benchmark_agent.py",
                    "--agent",
                    "mini",
                    "--provider",
                    "local-luna",
                    *common,
                    *external,
                ]
            else:
                command = [
                    agent_python,
                    "scripts/run_codex_benchmark.py",
                    "--binary",
                    str(ROOT / p["codex_binary"]),
                    *common,
                    *external,
                ]
        print(json.dumps({"attempt_started": attempt["attempt_id"]}), flush=True)
        code = run(command, output / (arm + "-worker.log"))
        score_code = run(
            [
                agent_python,
                "scripts/score_benchmark_attempt.py",
                "--worker-result",
                str(target / "result.json"),
                "--attempt-id",
                attempt["attempt_id"],
                "--qualification",
                settings["qualification"],
                "--dataset",
                settings.get("dataset", str(ROOT / ".repropatch/inputs/dataset")),
                "--repository",
                settings.get("repository", str(ROOT / ".repropatch/inputs/fmt")),
                "--timeout",
                str(p.get("oracle_timeout_seconds", 900)),
                "--output",
                str(output / (arm + "-score")),
            ],
            output / (arm + "-score.log"),
        )
        score_file = output / (arm + "-score") / "score.json"
        if not score_file.is_file():
            matches = list((output / (arm + "-score")).glob("*.json"))
            score_file = next(
                (
                    f
                    for f in matches
                    if json.loads(f.read_text()).get("schema") == "repropatch.benchmark-score.v1"
                ),
                score_file,
            )
        score = (
            json.loads(score_file.read_text())
            if score_file.is_file()
            else {"status": "SCORING_ERROR", "accepted": None}
        )
        worker_path = target / "result.json"
        worker = json.loads(worker_path.read_text()) if worker_path.is_file() else {}
        metrics = attempt_metrics(worker, LocalUsageLedger(ledger).summary(), score, target)
        summaries.append(
            {
                **attempt,
                "worker_exit": code,
                "score_exit": score_code,
                "score": score,
                "usage": LocalUsageLedger(ledger).summary(),
                **metrics,
            }
        )
        save(
            output / "summary.json",
            {
                "instance_id": instance,
                "attempts": summaries,
                "usage": {
                    key: sum(r["usage"][key] for r in summaries)
                    for key in ("requests", "unknown_usage_requests")
                },
            },
        )
        print(
            json.dumps(
                {
                    "attempt_finished": attempt["attempt_id"],
                    "status": score["status"],
                    "accepted": score.get("accepted"),
                }
            ),
            flush=True,
        )


def attempt_metrics(worker, usage, score, target):
    context = worker.get("context") or {}
    compactions = worker.get("compactions", context.get("compactions", []))
    stop = (
        worker.get("stop_reason") or worker.get("agent_stop_reason") or worker.get("native_reason")
    )
    evaluations = []
    native_id = worker.get("native_run_id")
    if native_id:
        report = target / "runs" / native_id / "report.json"
        if report.is_file():
            evaluations = json.loads(report.read_text()).get("evaluations", [])
    self_check_seconds = sum(
        (
            datetime.fromisoformat(item["finished_at"]) - datetime.fromisoformat(item["started_at"])
        ).total_seconds()
        for item in evaluations
        if item.get("evaluation_role") == "agent_check" and item.get("finished_at")
    )
    return {
        "stop_reason": stop or "NOT_EXECUTED",
        "oracle_result": "PASS"
        if score.get("accepted") is True
        else "FAIL"
        if score.get("accepted") is False
        else score.get("status"),
        "metrics": {
            **usage,
            "compaction_count": sum(
                item.get("status", "completed") == "completed" for item in compactions
            ),
            "compactions": compactions,
            "compaction_seconds": sum(item.get("duration_seconds", 0) for item in compactions),
            "worker_seconds": worker.get("duration_seconds"),
            "self_check_seconds": self_check_seconds,
            "cold_oracle_seconds": score.get("wall_seconds"),
            "tool_calls": worker.get("tool_calls", worker.get("tool_calls_admitted")),
        },
    }


def aggregate(source, output):
    p = protocol()
    known = {}
    for path in source.rglob("summary.json"):
        value = json.loads(path.read_text())
        for row in value.get("attempts", []):
            if row["attempt_id"] in known:
                raise ValueError("DUPLICATE_FORMAL_ATTEMPT")
            known[row["attempt_id"]] = row
    rows = [
        known.get(
            a["attempt_id"],
            a if "score" in a else {**a, "score": {"status": "NOT_EXECUTED", "accepted": None}},
        )
        for a in [*p["attempts"], *p.get("prior_attempts", [])]
    ]
    result = {
        "protocol_sha256": sha(PROTOCOL),
        "attempts": rows,
        "status_counts": dict(Counter(r["score"]["status"] for r in rows)),
        "context_policy": p.get("context_policy"),
        "stop_reason_counts": dict(Counter(r.get("stop_reason", "UNKNOWN") for r in rows)),
        "stop_oracle_matrix": [
            {"stop_reason": stop, "oracle_result": oracle, "attempts": count}
            for (stop, oracle), count in Counter(
                (r.get("stop_reason", "UNKNOWN"), r.get("oracle_result", "UNKNOWN")) for r in rows
            ).items()
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    save(output / "results.json", result)
    (output / "protocol.json").write_bytes(PROTOCOL.read_bytes())
    lines = [
        "# Pilot 机制验收" if p.get("phase") == "pilot" else "# 正式首跑结果",
        "",
        "| 任务 | 臂 | Oracle | Agent 停止 | 请求 | 压缩请求 | 自检秒 |",
        "| --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    lines += [
        f"| {r['instance_id']} | {r['arm']} | {r.get('oracle_result', r['score']['status'])} | "
        f"{r.get('stop_reason', 'UNKNOWN')} | {r.get('usage', {}).get('requests', 0)} | "
        f"{r.get('metrics', {}).get('compact_requests', 0)} | "
        f"{r.get('metrics', {}).get('self_check_seconds', 0):.1f} |"
        for r in rows
    ]
    (output / "results.md").write_text("\n".join(lines) + "\n")


def main():
    global PROTOCOL, ATTEMPT_ID
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage",
        choices=(
            "calibrate",
            "verify-calibration",
            "verify-pilot",
            "verify-completion",
            "verify-registry",
            "prepare",
            "run",
            "aggregate",
        ),
    )
    parser.add_argument("--protocol", type=Path, default=PROTOCOL)
    parser.add_argument("--instance")
    parser.add_argument("--attempt-id")
    parser.add_argument(
        "--arm", choices=("all", "shell-only", "full", "no-checks", "mini", "codex"), default="all"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    PROTOCOL = args.protocol.resolve(strict=True)
    ATTEMPT_ID = args.attempt_id
    if args.stage == "calibrate":
        calibrate(args.output)
    elif args.stage == "verify-calibration":
        verify_calibration(args.source, args.output)
    elif args.stage == "verify-pilot":
        verify_pilot(args.source, args.output)
    elif args.stage == "verify-completion":
        verify_completion(args.source, args.output)
    elif args.stage == "verify-registry":
        verify_registry(args.source, args.output)
    elif args.stage == "prepare":
        prepare(args.instance, args.output, args.arm)
    elif args.stage == "run":
        p = protocol()
        if p.get("campaign_schema") == "repropatch.cross-repository-campaign.v1":
            from cpa_session import CPASession

            if not args.attempt_id:
                raise ValueError("CROSS_EXPLICIT_ATTEMPT_ID_REQUIRED")
            with CPASession(args.output / "cpa-session") as session:
                from cross_repo_campaign import allocation_phase

                attempt = next(a for a in p["attempts"] if a["attempt_id"] == args.attempt_id)
                session.claim(args.attempt_id, allocation_phase(p, attempt))
                execute(args.instance, args.output, args.arm)
        else:
            execute(args.instance, args.output, args.arm)
    else:
        aggregate(args.source, args.output)


if __name__ == "__main__":
    main()
