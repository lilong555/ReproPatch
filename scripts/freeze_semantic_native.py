"""复用固定任务资格，冻结结构状态 Full 与原生 mini/Codex 的三臂协议。"""

import argparse
import copy
import json
import random
import re
import subprocess
from pathlib import Path

from cross_repo_campaign import (
    NATIVE_ARMS,
    NATIVE_CAMPAIGN,
    NATIVE_TRANSPORT_MAX_BYTES,
    NATIVE_VARIANT,
    execution_fingerprint,
    task_environment,
    validate_protocol,
)
from qualify_cpp_batch import save, sha

ROOT = Path(__file__).resolve().parents[1]
TASKS = [
    "catchorg__Catch2-2128",
    "fmtlib__fmt-3569",
    "nlohmann__json-2319",
    "nlohmann__json-3564",
    "simdjson__simdjson-644",
    "actor-framework__actor-framework-2300",
    "KhronosGroup__glslang-4006",
    "open-source-parsers__jsoncpp-1693",
]
PINNED_FIELDS = (
    "model",
    "reasoning_effort",
    "model_timeout_seconds",
    "max_tools_per_response",
    "max_output_tokens",
    "mini_commit",
    "codex_binary",
    "codex_version",
    "codex_sha256",
    "codex_tarball",
    "codex_tarball_integrity",
    "code_host_sha256",
    "network_calibration",
)


def build_protocol(sources, *, batch="r1", tasks=TASKS, seed=20261101):
    """按原始文件身份复用资格合同，生成显式草稿。"""
    if not tasks or len(set(tasks)) != len(tasks):
        raise ValueError("NATIVE_TASK_REGISTRY_INVALID")
    if not isinstance(batch, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", batch):
        raise ValueError("NATIVE_BATCH_ID_INVALID")
    batch_id = f"{NATIVE_CAMPAIGN}/{batch}"
    source_values = [(path, json.loads(path.read_text())) for path in sources]
    if not source_values:
        raise ValueError("NATIVE_SOURCE_PROTOCOLS_REQUIRED")
    base = source_values[0][1]
    contracts, environments, archives, used_sources, references = {}, {}, {}, {}, {}
    for task in tasks:
        matches = [(path, value) for path, value in source_values if task in value["tasks"]]
        if len(matches) != 1:
            raise ValueError("NATIVE_SOURCE_TASK_IDENTITY_AMBIGUOUS: " + task)
        path, value = matches[0]
        if any(value[field] != base[field] for field in PINNED_FIELDS):
            raise ValueError("NATIVE_SOURCE_EXECUTOR_IDENTITY_MISMATCH")
        contracts[task] = copy.deepcopy(value["qualification_contracts"][task])
        environments[task] = copy.deepcopy(task_environment(value, task))
        selected = [row for row in value["qualification_archives"] if task in row["instances"]]
        if len(selected) != 1:
            raise ValueError("CROSS_QUALIFICATION_ARCHIVE_MISSING")
        entry = selected[0]
        key = (entry["run_id"], entry["artifact"], entry["sha256"])
        if key not in archives:
            archives[key] = {**entry, "instances": []}
        archives[key]["instances"].append(task)
        used_sources[path.name] = {
            "path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
            "sha256": sha(path),
            "batch_id": value["batch_id"],
            "execution_source_commit": value["execution_source_commit"],
            "execution_sha256": value["execution_sha256"],
        }
        references[task] = {
            "source_protocol_sha256": sha(path),
            "attempts": [
                copy.deepcopy(row)
                for row in value["attempts"]
                if row["instance_id"] == task and row["arm"] in NATIVE_ARMS
            ],
        }
    generator = random.Random(seed)
    attempts = []
    for task in tasks:
        arms = NATIVE_ARMS.copy()
        generator.shuffle(arms)
        attempts.extend(
            {
                "attempt_id": f"{batch_id}/{task}/{arm}/first",
                "instance_id": task,
                "arm": arm,
                "request_cap": None,
            }
            for arm in arms
        )
    policy = {
        **base["context_policy"],
        "request_cap": None,
        "transport_max_bytes": NATIVE_TRANSPORT_MAX_BYTES,
        "context_policy_version": "v2.0-semantic-state",
    }
    value = {
        **{key: copy.deepcopy(base[key]) for key in PINNED_FIELDS},
        "campaign_schema": "repropatch.cross-repository-campaign.v1",
        "variant": NATIVE_VARIANT,
        "campaign": NATIVE_CAMPAIGN,
        "status": "DRAFT",
        "phase": "development",
        "study_type": "cross-repository-development-trend",
        "batch_id": batch_id,
        "tasks": list(tasks),
        "arms": NATIVE_ARMS.copy(),
        "attempts": attempts,
        "execution_order": copy.deepcopy(attempts),
        "selection_seed": seed,
        "matrix_per_arm": True,
        "request_cap_per_attempt": None,
        "formal_request_cap": None,
        "max_tool_calls": None,
        "max_parallel": 3,
        "cpa_max_concurrent_requests": 3,
        "context_policy": policy,
        "executor_policies": {
            "full": {"context_management": "repropatch", "semantic_state": True},
            "mini": {"context_management": "native", "semantic_state": False},
            "codex": {"context_management": "native", "semantic_state": False},
        },
        "primary_pairs": [["full", "mini"], ["full", "codex"], ["mini", "codex"]],
        "qualification_contracts": contracts,
        "environment_policy": "per-task-native-v1",
        "task_environments": environments,
        "qualification_run_ids": sorted({row["run_id"] for row in archives.values()}),
        "qualification_archives": list(archives.values()),
        "source_protocols": list(used_sources.values()),
        "historical_reference": {
            "configuration": "v1.0-unified-compaction; 24 requests; 48 tool calls",
            "mini_context_management": "custom-adapter",
            "codex_compact_trigger_tokens": 48_000,
            "purpose": "带配置身份的历史参考",
            "tasks": references,
        },
        "execution_budget_override": {
            "max_steps": None,
            "max_tool_calls": None,
            "model_timeout_seconds": 180,
            "wall_seconds": 12_600,
            "verification_reserve_seconds": 1800,
        },
        "deadline_policy": {
            "request_total": "unlimited",
            "termination": "native completion or recorded execution deadline",
            "nominal_repair_seconds": 10_800,
            "baseline_counts_toward_worker_wall": True,
            "platform_job_minutes": 360,
            "cold_oracle_timeout_seconds": 3600,
        },
        "platform_job_timeout_minutes": 360,
        "oracle_timeout_seconds": 3600,
        "execution_source_commit": None,
        "execution_sha256": None,
        "ci_run_id": None,
        "paid_calls_authorized": True,
        "cpa_route": "azure-ssh",
        "retries": 0,
        "prior_attempts": [],
        "protocol_identity": "冻结文件的 SHA256 随运行 provenance 保存",
        "selection_basis": "复用八道已执行任务，覆盖七仓库及定位、压缩问题与通过控制",
        "result_policy": "全部首跑保留；已有任务用于开发趋势观察",
    }
    return value


def freeze(value, *, source_commit, ci_run):
    """执行源码须已提交，协议引用通过 CI 的同一源码身份。"""
    resolved = subprocess.check_output(
        ["git", "rev-parse", source_commit + "^{commit}"], cwd=ROOT, text=True
    ).strip()
    paths = ["src/repropatch", "scripts", "requirements", ".github/workflows", "pyproject.toml"]
    subprocess.run(["git", "diff", "--quiet", resolved, "--", *paths], cwd=ROOT, check=True)
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "--", *paths], cwd=ROOT, text=True
    )
    if untracked.strip():
        raise ValueError("NATIVE_EXECUTION_SOURCE_UNCOMMITTED")
    result = copy.deepcopy(value)
    result.update(
        status="FROZEN",
        execution_source_commit=resolved,
        execution_sha256=execution_fingerprint(),
        ci_run_id=ci_run,
    )
    validate_protocol(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-protocol", type=Path, action="append")
    parser.add_argument("--tasks", default=",".join(TASKS))
    parser.add_argument("--batch", default="r1", help="campaign 下的独立批次标识")
    parser.add_argument("--seed", type=int, default=20261101)
    parser.add_argument("--source-commit")
    parser.add_argument("--ci-run", type=int)
    parser.add_argument("--draft", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sources = args.source_protocol or sorted(
        (ROOT / "benchmarks/cross-repo").glob("formal-protocol-batch-*.json")
    )
    value = build_protocol(sources, batch=args.batch, tasks=args.tasks.split(","), seed=args.seed)
    if not args.draft:
        if not args.source_commit or not args.ci_run:
            parser.error("冻结需要已提交源码 --source-commit 与通过记录 --ci-run")
        value = freeze(value, source_commit=args.source_commit, ci_run=args.ci_run)
    elif args.source_commit or args.ci_run:
        parser.error("草稿保留空源码和 CI 身份")
    save(args.output, value)
    print(
        json.dumps(
            {
                "status": value["status"],
                "protocol": str(args.output),
                "sha256": sha(args.output),
                "tasks": len(value["tasks"]),
                "attempts": len(value["attempts"]),
                "request_cap": value["formal_request_cap"],
                "max_parallel": value["max_parallel"],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
