"""冻结跨仓库执行协议，恢复资格源码并生成五组统一初始诊断。"""

import hashlib
import json
import os
import random
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from check_native_cpp_candidate import restore_repository
from cpp_sources import load_records
from qualify_cpp_batch import save, sha
from verify_qualification_evidence import required_task_artifacts, verify_tree

from repropatch.context import ContextPolicy
from repropatch.task import IMAGE_ID, Task

ROOT = Path(__file__).resolve().parents[1]
ARMS = ["full", "no-checks", "shell-only", "mini", "codex"]


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
    if p["arms"] != ARMS or p["reasoning_effort"] != "max" or p["model_timeout_seconds"] != 180:
        raise ValueError("CROSS_FRAMEWORK_CONFIGURATION_MISMATCH")
    if p["request_cap_per_attempt"] != 24 or p["max_tool_calls"] != 48 or p["max_parallel"] != 2:
        raise ValueError("CROSS_BUDGET_CONFIGURATION_MISMATCH")
    if p["phase"] not in {"development", "formal", "repeat", "infrastructure-revalidation"}:
        raise ValueError("CROSS_PHASE_INVALID")
    ids = p["tasks"]
    if len(set(ids)) != len(ids) or len(ids) > 30:
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
    if p["phase"] == "formal" and (len(ids) != 30 or len(attempts) != 150):
        raise ValueError("CROSS_FORMAL_REGISTRY_INCOMPLETE")
    if p["phase"] == "development" and (len(ids) != 4 or len(attempts) != 20):
        raise ValueError("CROSS_DEVELOPMENT_REGISTRY_INCOMPLETE")
    if p["phase"] == "repeat" and (len(ids) != 6 or len(attempts) != 30):
        raise ValueError("CROSS_REPEAT_REGISTRY_INCOMPLETE")
    if p["phase"] != "infrastructure-revalidation" and {
        (a["instance_id"], a["arm"]) for a in attempts
    } != {(task, arm) for task in ids for arm in ARMS}:
        raise ValueError("CROSS_TASK_ARM_REGISTRY_INCOMPLETE")
    if not IMAGE_ID.fullmatch(p["image_id"]) or "@sha256:" not in p["image"]:
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
    from formal_benchmark import freeze_configuration
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
    if q["status"] != "QUALIFIED" or q["image_id"] != p["image_id"]:
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
    image = subprocess.check_output(
        ["docker", "image", "inspect", "--format", "{{.Id}}", p["image"]], text=True
    ).strip()
    if image != p["image_id"]:
        raise ValueError("CROSS_IMAGE_IDENTITY_MISMATCH")
    dataset = ROOT / ".repropatch/cross-inputs"
    record = next(r for r in load_records(dataset) if r["instance_id"] == instance)
    if record["base"]["sha"] != q["upstream_commit"]:
        raise ValueError("CROSS_DATASET_IDENTITY_MISMATCH")
    baseline = Harness(
        task, ScriptedModel([[assistant_message("固定基线输入。")]]), output / "baseline-runs"
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
            "task": str(directory / "task.yaml"),
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
