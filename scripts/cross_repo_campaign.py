"""冻结跨仓库执行协议，恢复资格源码并生成五组统一初始诊断。"""

import hashlib
import json
import os
import random
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from check_native_cpp_candidate import restore_repository
from cpp_native_adapter import text_readable_paths
from cpp_sources import load_records
from qualify_cpp_batch import save, sha
from verify_qualification_evidence import required_task_artifacts, verify_tree

from repropatch.context import ContextPolicy
from repropatch.task import IMAGE_ID, Task

ROOT = Path(__file__).resolve().parents[1]
ARMS = ["full", "no-checks", "shell-only", "mini", "codex"]
NATIVE_ARMS = ["full", "mini", "codex"]
NATIVE_VARIANT = "semantic-state-native-v1"
NATIVE_CAMPAIGN = "semantic-state-native-20261101"
NATIVE_TRANSPORT_MAX_BYTES = 64 * 1024 * 1024


def native_trend(protocol):
    """识别结构状态与原生执行器的三臂开发对照。"""
    return protocol.get("variant") == NATIVE_VARIANT


def arm_context_policy(protocol, arm):
    """Full 使用自身状态策略，原生对照只保留传输计量配置。"""
    value = dict(protocol["context_policy"])
    if native_trend(protocol) and arm in {"mini", "codex"}:
        value["compaction_enabled"] = False
    return ContextPolicy.from_dict(value)


def validate_execution_evidence(protocol, ci, calibration_bytes):
    """核对执行源码 CI 和历史校准原件，校准次数按该证据合同核验。"""
    if (
        ci.get("conclusion") != "success"
        or ci.get("head_sha") != protocol["execution_source_commit"]
        or ci.get("name") != "CI"
    ):
        raise ValueError("CROSS_CI_SOURCE_IDENTITY_MISMATCH")
    if hashlib.sha256(calibration_bytes).hexdigest() != protocol["network_calibration"]["sha256"]:
        raise ValueError("CROSS_NETWORK_CALIBRATION_IDENTITY_MISMATCH")
    data = json.loads(calibration_bytes)
    if (
        data.get("schema") != "repropatch.cross-network-calibration.v1"
        or data.get("status") != "PASSED"
        or data.get("model") != protocol["model"]
        or data.get("reasoning_effort") != protocol["reasoning_effort"]
        or data.get("model_timeout_seconds") != protocol["model_timeout_seconds"]
        or data.get("usage", {}).get("issued_requests") != 12
    ):
        raise ValueError("CROSS_NETWORK_CALIBRATION_REQUIRED")
    return data


def validate_native_protocol(p):
    """核验请求总量开放的三臂冻结合同。"""
    if (
        p.get("status") != "FROZEN"
        or p.get("phase") != "development"
        or p.get("campaign") != NATIVE_CAMPAIGN
        or p.get("arms") != NATIVE_ARMS
        or p.get("model") != "gpt-6-luna"
        or p.get("reasoning_effort") != "max"
        or p.get("model_timeout_seconds") != 180
    ):
        raise ValueError("NATIVE_FRAMEWORK_CONFIGURATION_MISMATCH")
    if (
        any(
            p.get(key, "missing") is not None
            for key in ("request_cap_per_attempt", "formal_request_cap", "max_tool_calls")
        )
        or type(p.get("max_parallel")) is not int
        or not 1 <= p["max_parallel"] <= 3
        or p.get("cpa_max_concurrent_requests") != 3
    ):
        raise ValueError("NATIVE_BUDGET_CONFIGURATION_MISMATCH")
    tasks = p.get("tasks", [])
    attempts = p.get("attempts", [])
    if not tasks or len(set(tasks)) != len(tasks) or len(tasks) > 30:
        raise ValueError("NATIVE_TASK_REGISTRY_INVALID")
    expected = {(task, arm) for task in tasks for arm in NATIVE_ARMS}
    if (
        not re.fullmatch(
            re.escape(NATIVE_CAMPAIGN) + r"/[A-Za-z0-9_.-]{1,80}", p.get("batch_id") or ""
        )
        or len(attempts) != len(expected)
        or len({a["attempt_id"] for a in attempts}) != len(attempts)
        or {(a["instance_id"], a["arm"]) for a in attempts} != expected
        or any(a.get("request_cap", "missing") is not None for a in attempts)
        or any(
            a["attempt_id"] != f"{p['batch_id']}/{a['instance_id']}/{a['arm']}/first"
            for a in attempts
        )
        or p.get("execution_order") != attempts
        or p.get("prior_attempts")
    ):
        raise ValueError("NATIVE_ATTEMPT_REGISTRY_INVALID")
    policies = p.get("executor_policies", {})
    if (
        policies.get("full") != {"context_management": "repropatch", "semantic_state": True}
        or policies.get("mini") != {"context_management": "native", "semantic_state": False}
        or policies.get("codex") != {"context_management": "native", "semantic_state": False}
    ):
        raise ValueError("NATIVE_CONTEXT_POLICY_MISMATCH")
    budget = p.get("execution_budget_override", {})
    if (
        budget.get("max_steps", "missing") is not None
        or budget.get("max_tool_calls", "missing") is not None
        or budget.get("model_timeout_seconds") != 180
        or type(budget.get("wall_seconds")) is not int
        or type(budget.get("verification_reserve_seconds")) is not int
        or not 0 < budget["verification_reserve_seconds"] < budget["wall_seconds"] <= 18_000
        or p.get("platform_job_timeout_minutes") != 360
    ):
        raise ValueError("NATIVE_EXECUTION_DEADLINE_INVALID")
    if set(p.get("task_environments", {})) != set(tasks):
        raise ValueError("CROSS_TASK_ENVIRONMENT_REGISTRY_MISMATCH")
    if set(p.get("qualification_contracts", {})) != set(tasks):
        raise ValueError("CROSS_QUALIFICATION_REGISTRY_INCOMPLETE")
    for task in tasks:
        environment = task_environment(p, task)
        if not IMAGE_ID.fullmatch(environment["image_id"]) or not re.fullmatch(
            r"[A-Za-z0-9._:/-]+@sha256:[a-f0-9]{64}", environment["image"]
        ):
            raise ValueError("CROSS_IMMUTABLE_IMAGE_REQUIRED")
        identity = p["qualification_contracts"][task]
        if any(
            not re.fullmatch(r"[a-f0-9]{64}", identity.get(field, ""))
            for field in ("qualification_sha256", "task_sha256", "manifest_sha256", "bundle_sha256")
        ) or not re.fullmatch(r"[a-f0-9]{40}", identity.get("prepared_commit", "")):
            raise ValueError("NATIVE_QUALIFICATION_IDENTITY_INVALID")
        archives = [row for row in p.get("qualification_archives", []) if task in row["instances"]]
        if len(archives) != 1 or not re.fullmatch(r"[a-f0-9]{64}", archives[0].get("sha256", "")):
            raise ValueError("CROSS_QUALIFICATION_ARCHIVE_MISSING")
    if (
        p.get("cpa_route") != "azure-ssh"
        or p.get("retries") != 0
        or p.get("paid_calls_authorized") is not True
        or not p.get("network_calibration", {}).get("sha256")
    ):
        raise ValueError("CROSS_NETWORK_POLICY_MISMATCH")
    if (
        p.get("execution_sha256") != execution_fingerprint()
        or not re.fullmatch(r"[a-f0-9]{40}", p.get("execution_source_commit") or "")
        or type(p.get("ci_run_id")) is not int
        or p["ci_run_id"] <= 0
    ):
        raise ValueError("CROSS_EXECUTION_SOURCE_CHANGED")
    policy = arm_context_policy(p, "full")
    if (
        policy.request_cap is not None
        or not policy.compaction_enabled
        or policy.transport_max_bytes != NATIVE_TRANSPORT_MAX_BYTES
    ):
        raise ValueError("NATIVE_CONTEXT_POLICY_MISMATCH")


def task_environment(protocol, instance):
    """按题目选择冻结环境，五个实验臂共享同一映射。"""
    if "task_environments" in protocol:
        return protocol["task_environments"][instance]
    return {"image": protocol["image"], "image_id": protocol["image_id"]}


def development_selection(results, expected_tasks):
    """四道开发题的五组冷评分完整后，确定预登记的难度配额。"""
    rows = results.get("attempts", [])
    expected = {(task, arm) for task in expected_tasks for arm in ARMS}
    pairs = [(row.get("instance_id"), row.get("arm")) for row in rows]
    if (
        len(expected_tasks) != 4
        or len(rows) != 20
        or set(pairs) != expected
        or len(set(pairs)) != 20
    ):
        raise ValueError("CROSS_DEVELOPMENT_RESULTS_INCOMPLETE")
    if any(
        type(row.get("score", {}).get("accepted")) is not bool
        or row.get("score", {}).get("classification") == "infrastructure"
        for row in rows
    ):
        raise ValueError("CROSS_DEVELOPMENT_ORACLE_PENDING")
    all_pass = all(row["score"]["accepted"] for row in rows)
    return {
        "tasks": list(expected_tasks),
        "scored_attempts": 20,
        "all_pass": all_pass,
        "difficulty_counts": {"complex": 24, "medium": 4, "compile_control": 2}
        if all_pass
        else {"complex": 18, "medium": 8, "compile_control": 4},
    }


def selection_review(
    review, selected, development, existing_repositories, *, new_repository_tasks=25
):
    """正式样本同时满足新仓库配额、缺陷语义、去重与难度分层。"""
    if (
        len(selected) != 30
        or set(review) != set(selected)
        or set(selected) & set(development["tasks"])
    ):
        raise ValueError("CROSS_FORMAL_SELECTION_REGISTRY_INVALID")
    difficulties = {"complex": 0, "medium": 0, "compile_control": 0}
    issue_keys, repositories = set(), {}
    new_tasks = 0
    for task in selected:
        row = review[task]
        repository = task.rsplit("-", 1)[0].replace("__", "/")
        if (
            row.get("repository") != repository
            or row.get("semantic_kind") != "defect"
            or row.get("historical_model_exposure") != "UNEXPOSED"
            or not row.get("rationale", "").strip()
            or not row.get("issue_key")
            or row.get("difficulty") not in difficulties
        ):
            raise ValueError("CROSS_FORMAL_SEMANTIC_REVIEW_REQUIRED")
        identity = (repository, row["issue_key"])
        if identity in issue_keys:
            raise ValueError("CROSS_FORMAL_SEMANTIC_DUPLICATE")
        issue_keys.add(identity)
        difficulties[row["difficulty"]] += 1
        repositories[repository] = repositories.get(repository, 0) + 1
        new_tasks += repository not in existing_repositories
    if (
        type(new_repository_tasks) is not int
        or not 5 <= new_repository_tasks <= 30
        or difficulties != development["difficulty_counts"]
        or new_tasks != new_repository_tasks
    ):
        raise ValueError("CROSS_FORMAL_SELECTION_QUOTA_MISMATCH")
    if len(set(repositories) - set(existing_repositories)) < 5:
        raise ValueError("CROSS_FORMAL_REPOSITORY_COVERAGE_REQUIRED")
    return {
        "difficulty_counts": difficulties,
        "repository_counts": repositories,
        "new_repository_tasks": new_tasks,
        "existing_repository_new_tasks": 30 - new_tasks,
    }


def execution_fingerprint():
    """执行代码、固定依赖与工作流共同构成冻结身份。"""
    paths = [
        *ROOT.glob("src/repropatch/*.py"),
        *ROOT.glob("scripts/*.py"),
        ROOT / "scripts/native_cpp_runtime.cmake",
    ]
    paths += [
        ROOT / name
        for name in (
            "pyproject.toml",
            "requirements/agent.txt",
            "requirements/formal-mini.txt",
            ".github/workflows/cross-repository.yml",
            ".github/workflows/formal-benchmark.yml",
            "docker/cross-repository.Dockerfile",
        )
    ]
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(
            path.relative_to(ROOT).as_posix().encode() + b"\0" + path.read_bytes() + b"\0"
        )
    return digest.hexdigest()


def validate_protocol(p):
    """正式请求只使用完整冻结的跨仓库合同。"""
    if native_trend(p):
        return validate_native_protocol(p)
    if p["arms"] != ARMS or p["reasoning_effort"] != "max" or p["model_timeout_seconds"] != 180:
        raise ValueError("CROSS_FRAMEWORK_CONFIGURATION_MISMATCH")
    if (
        p["request_cap_per_attempt"] != 24
        or p["max_tool_calls"] != 48
        or p["max_parallel"] not in {2, 3}
    ):
        raise ValueError("CROSS_BUDGET_CONFIGURATION_MISMATCH")
    if p["phase"] not in {"development", "formal", "repeat", "infrastructure-revalidation"}:
        raise ValueError("CROSS_PHASE_INVALID")
    ids = p["tasks"]
    if not ids or len(set(ids)) != len(ids) or len(ids) > 30:
        raise ValueError("CROSS_TASK_REGISTRY_INVALID")
    caps = {"development": 480, "formal": 3600, "repeat": 720, "infrastructure-revalidation": 480}
    attempts = p["attempts"]
    if (
        len({a["attempt_id"] for a in attempts}) != len(attempts)
        or sum(a["request_cap"] for a in attempts) != p["formal_request_cap"]
        or p["formal_request_cap"] > caps[p["phase"]]
    ):
        raise ValueError("CROSS_ATTEMPT_ALLOCATION_INVALID")
    if any(
        a["instance_id"] not in ids or a["arm"] not in ARMS or a["request_cap"] != 24
        for a in attempts
    ):
        raise ValueError("CROSS_ATTEMPT_IDENTITY_INVALID")
    if p["phase"] == "formal" and len(attempts) != len(ids) * len(ARMS):
        raise ValueError("CROSS_FORMAL_REGISTRY_INCOMPLETE")
    prior = p.get("prior_attempts", [])
    registered = [*attempts, *prior]
    if prior and (
        p["phase"] != "development"
        or len({a["attempt_id"] for a in registered}) != len(registered)
        or any(not a.get("source_run_id") or not a.get("source_artifact_sha256") for a in prior)
        or any(
            a.get("request_cap") != 24
            or a.get("instance_id") not in ids
            or a.get("arm") not in ARMS
            for a in prior
        )
        or sum(a["request_cap"] for a in registered) > caps["development"]
    ):
        raise ValueError("CROSS_PRIOR_ATTEMPT_EVIDENCE_REQUIRED")
    if p["phase"] == "development" and (len(ids) != 4 or len(registered) != 20):
        raise ValueError("CROSS_DEVELOPMENT_REGISTRY_INCOMPLETE")
    if p["phase"] == "repeat" and (len(ids) != 6 or len(attempts) != 30):
        raise ValueError("CROSS_REPEAT_REGISTRY_INCOMPLETE")
    if p["phase"] != "infrastructure-revalidation" and {
        (a["instance_id"], a["arm"]) for a in registered
    } != {(task, arm) for task in ids for arm in ARMS}:
        raise ValueError("CROSS_TASK_ARM_REGISTRY_INCOMPLETE")
    for attempt in attempts:
        allocation_phase(p, attempt)
    if "task_environments" in p and set(p["task_environments"]) != set(ids):
        raise ValueError("CROSS_TASK_ENVIRONMENT_REGISTRY_MISMATCH")
    for instance in ids:
        environment = task_environment(p, instance)
        if not IMAGE_ID.fullmatch(environment["image_id"]) or not re.fullmatch(
            r"[A-Za-z0-9._:/-]+@sha256:[a-f0-9]{64}", environment["image"]
        ):
            raise ValueError("CROSS_IMMUTABLE_IMAGE_REQUIRED")
    if p["cpa_route"] != "azure-ssh" or p["retries"] != 0 or not p["paid_calls_authorized"]:
        raise ValueError("CROSS_NETWORK_POLICY_MISMATCH")
    ContextPolicy.from_dict(p["context_policy"])
    if set(p["qualification_contracts"]) != set(ids):
        raise ValueError("CROSS_QUALIFICATION_REGISTRY_INCOMPLETE")
    if p.get("execution_sha256") != execution_fingerprint():
        raise ValueError("CROSS_EXECUTION_SOURCE_CHANGED")
    if not p.get("network_calibration", {}).get("sha256"):
        raise ValueError("CROSS_NETWORK_CALIBRATION_REQUIRED")
    if p["phase"] == "formal":
        gate = p.get("selection_gate", {})
        development = gate.get("development", {})
        if development.get("scored_attempts") != 20 or not development.get("results_sha256"):
            raise ValueError("CROSS_DEVELOPMENT_SELECTION_GATE_REQUIRED")
        campaign_tasks = gate.get("campaign_tasks", ids)
        if not set(ids) <= set(campaign_tasks):
            raise ValueError("CROSS_FORMAL_SELECTION_REGISTRY_INVALID")
        selection_review(
            gate.get("review", {}),
            campaign_tasks,
            development,
            p["existing_repositories"],
            new_repository_tasks=gate.get("new_repository_tasks", 25),
        )
        if len(set(p.get("repeat_tasks", []))) != 6 or not set(p["repeat_tasks"]) <= set(
            campaign_tasks
        ):
            raise ValueError("CROSS_REPEAT_PREREGISTRATION_REQUIRED")
        incremental = p.get("incremental_submission")
        if len(ids) < 30 and not incremental:
            raise ValueError("CROSS_INCREMENTAL_REGISTRY_REQUIRED")
        if incremental:
            if incremental.get("campaign_request_cap") != 3600:
                raise ValueError("CROSS_INCREMENTAL_BUDGET_INVALID")
            allocated = set(ids)
            for previous in incremental.get("prior_batches", []):
                tasks = previous["tasks"]
                if (
                    not tasks
                    or len(set(tasks)) != len(tasks)
                    or set(tasks) & allocated
                    or not set(tasks) <= set(campaign_tasks)
                    or not re.fullmatch(r"[0-9a-f]{64}", previous.get("sha256", ""))
                ):
                    raise ValueError("CROSS_INCREMENTAL_TASK_OVERLAP")
                allocated.update(tasks)
            if any(
                a["attempt_id"]
                != f"{incremental['campaign_batch_id']}/{a['instance_id']}/{a['arm']}/first"
                for a in attempts
            ):
                raise ValueError("CROSS_INCREMENTAL_ATTEMPT_ID_CHANGED")
    if p["phase"] == "repeat" and (
        not p.get("formal_protocol_sha256") or set(p.get("formal_repeat_tasks", [])) != set(ids)
    ):
        raise ValueError("CROSS_REPEAT_PREREGISTRATION_MISMATCH")


def allocation_phase(protocol, attempt):
    """准备失败和中断任务使用独立基础设施复验额度。"""
    phase = attempt.get("allocation_phase", protocol["phase"])
    if phase == protocol["phase"]:
        return phase
    evidence = protocol.get("preparation_failures", {}).get(attempt.get("original_attempt_id"))
    if (
        protocol["phase"] != "development"
        or phase != "infrastructure-revalidation"
        or not evidence
        or evidence.get("classification") not in {"infrastructure", "cancelled"}
        or type(evidence.get("issued_requests")) is not int
        or not 0 <= evidence["issued_requests"] <= 24
        or evidence.get("claim_status") != "CLAIMED"
        or not evidence.get("run_id")
        or not evidence.get("artifact_sha256")
        or any(evidence.get(key) != attempt[key] for key in ("instance_id", "arm"))
        or attempt["attempt_id"]
        != attempt["original_attempt_id"]
        + (
            "/preparation-revalidation"
            if evidence["issued_requests"] == 0
            else "/infrastructure-revalidation"
        )
    ):
        raise ValueError("CROSS_PREPARATION_REVALIDATION_EVIDENCE_REQUIRED")
    return phase


def execution_order(tasks, *, seed=20261028, replicate="first", batch="cross-repository-20261028"):
    generator = random.Random(seed)
    rows = []
    for task in tasks:
        arms = ARMS.copy()
        generator.shuffle(arms)
        rows.extend(
            {
                "attempt_id": f"{batch}/{task}/{arm}/{replicate}",
                "instance_id": task,
                "arm": arm,
                "request_cap": 24,
            }
            for arm in arms
        )
    return rows


def prepare(instance, output, arm, p):
    from agents.testing import ScriptedModel, assistant_message
    from formal_benchmark import freeze_configuration, prepare_execution_contract
    from prepare_mini_environment import MINI_COMMIT

    from repropatch.harness import Harness

    assert instance in p["tasks"]
    validate_protocol(p)
    output.mkdir(parents=True, exist_ok=False)
    freeze_configuration(output, p)
    directory = (
        Path(os.environ.get("CROSS_QUALIFICATION_ROOT", ROOT / ".repropatch/cross-qualification"))
        / instance
    )
    q = json.loads((directory / "result.json").read_text())
    identity = p["qualification_contracts"][instance]
    for file, field in (
        ("result.json", "qualification_sha256"),
        ("task.yaml", "task_sha256"),
        ("manifest.json", "manifest_sha256"),
        ("prepared.bundle", "bundle_sha256"),
    ):
        if sha(directory / file) != identity[field]:
            raise ValueError("CROSS_QUALIFICATION_CONTRACT_MISMATCH")
    environment = task_environment(p, instance)
    if q["status"] != "QUALIFIED" or q["image_id"] != environment["image_id"]:
        raise ValueError("CROSS_TASK_IMAGE_MISMATCH")
    task = Task.load(directory / "task.yaml")
    if task.revision != identity["prepared_commit"]:
        raise ValueError("CROSS_PREPARED_COMMIT_MISMATCH")
    if not task.repository.exists():
        restore_repository(directory, q, task.repository)
    issues = verify_tree(
        directory, json.loads((directory / "manifest.json").read_text()), required_task_artifacts(q)
    )
    if issues:
        raise ValueError("CROSS_QUALIFICATION_EVIDENCE_INCOMPLETE")
    original_task_sha = sha(directory / "task.yaml")
    readable = text_readable_paths(task.repository, task.readable_paths, task.revision)
    directory = prepare_execution_contract(
        directory,
        output / "execution-contract",
        p["model_timeout_seconds"],
        p.get("execution_budget_override"),
        readable_paths=readable,
    )
    execution_task = directory / "task.yaml"
    task = Task.load(execution_task)
    save(
        output / "execution-task-provenance.json",
        {
            "qualification_task_sha256": original_task_sha,
            "execution_task_sha256": sha(execution_task),
            "readable_policy": "utf8-text-v1",
            "prepared_commit": task.revision,
        },
    )
    image = subprocess.check_output(
        ["docker", "image", "inspect", "--format", "{{.Id}}", environment["image"]], text=True
    ).strip()
    if image != environment["image_id"]:
        raise ValueError("CROSS_IMAGE_IDENTITY_MISMATCH")
    dataset = ROOT / ".repropatch/cross-inputs"
    record = next(r for r in load_records(dataset) if r["instance_id"] == instance)
    if record["base"]["sha"] != q["upstream_commit"]:
        raise ValueError("CROSS_DATASET_IDENTITY_MISMATCH")
    baseline = Harness(
        task,
        ScriptedModel([[assistant_message("固定基线输入。")]]),
        output / "baseline-runs",
        context_policy=ContextPolicy.from_dict(p["context_policy"]),
    ).run()
    if not baseline["reproduced"] or not baseline["cleanup_confirmed"]:
        raise ValueError("CROSS_EXECUTION_BASELINE_FAILED")
    initial = next(Path(baseline["artifact_directory"]).glob("agent/native/0001-input.json"))
    shutil.copyfile(initial, output / "common-input.json")
    mini = ROOT / ".repropatch/mini-source"
    if arm in {"all", "mini", "codex"}:
        commit = subprocess.check_output(
            ["git", "-C", str(mini), "rev-parse", "HEAD"], text=True
        ).strip()
        if commit != MINI_COMMIT:
            raise ValueError("CROSS_MINI_SOURCE_IDENTITY_MISMATCH")
    evidence = baseline["baseline"]
    seconds = (
        datetime.fromisoformat(evidence["finished_at"])
        - datetime.fromisoformat(evidence["started_at"])
    ).total_seconds()
    save(
        output / "prepared.json",
        {
            "instance_id": instance,
            "task": str(execution_task),
            "qualification": str(directory / "result.json"),
            "common_input": str(output / "common-input.json"),
            "mini_source": str(mini),
            "dataset": str(dataset),
            "repository": str(task.repository),
            "agent_seconds": max(
                1,
                int(task.budget.wall_seconds - task.budget.verification_reserve_seconds - seconds),
            ),
        },
    )
