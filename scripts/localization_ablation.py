"""Independent paired localization trials, isolated scoring and fail-closed stage gates."""

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import context_ablation as shared
import yaml
from actions_benchmark import save, sha
from benchmark_budget import LocalUsageLedger
from cpa_session import CPASession
from prepare_multiswe_task import git as preparation_git

from repropatch.context import ContextPolicy
from repropatch.task import Task, canonical_json
from repropatch.workspace import Worktree, source_manifest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "benchmarks/localization-ablation/protocol.json"
CAMPAIGN = "localization-ablation-20261106"
ARMS = ("native", "bounded", "feedback")
load, digest, require = shared.load, shared.digest, shared.require
exclusive_save = shared.exclusive_save
PHASE_CONTRACT = {
    "initial_phase": "readonly",
    "allowed_tools": ["list_directory", "read_file", "search_code", "search_files"],
    "transition": "first_tool_cap_or_model_cap_or_final",
    "transition_effect": "repair_on_next_model_request",
    "denied_write_execute": "count_against_tool_budget_and_return_error",
    "batch_overflow": "return_budget_error_for_remaining_calls",
    "shared_total_model_requests": 24,
    "shared_total_tool_calls": 48,
    "model_request_accounting": "all_provider_requests_including_compaction",
    "exposure_delivery": "carrier_response_confirmed",
    "last_readonly_delivery": "first_repair_request_charged_to_hit_cost",
    "additional_baseline_collection": False,
}


def read_protocol(path=PROTOCOL):
    spec = load(path)
    require(spec["schema"] == "repropatch.localization-ablation.protocol.v1", "PROTOCOL_SCHEMA")
    require(spec["campaign"] == CAMPAIGN, "CAMPAIGN")
    require(spec["parent_protocol"] == "benchmarks/context-ablation/protocol.json", "PARENT")
    require(sha(ROOT / spec["parent_protocol"]) == spec["parent_protocol_sha256"], "PARENT_HASH")
    parent = shared.read_protocol(ROOT / spec["parent_protocol"])
    require(tuple(spec["arms"]) == ARMS, "ARMS")
    require(spec["arm_labels"] == dict(zip(ARMS, "ABC", strict=True)), "ARM_LABELS")
    require(
        spec["search_tools"]
        == dict(zip(ARMS, ("search_code", "search_files", "search_files"), strict=True)),
        "SEARCH_TOOLS",
    )
    require(spec["semantic_state"] is False and spec["context_arm"] == "baseline", "COMMON_CONTEXT")
    require(spec["phase_contract"] == PHASE_CONTRACT, "PHASE_CONTRACT")
    for key, value in {
        "localization_tool_budget": 8,
        "localization_step_budget": 4,
        "repeats": 2,
        "trial_count": 114,
        "formal_request_cap": 2736,
        "max_parallel": 8,
        "execution_order_seed": 20261106,
    }.items():
        require(type(spec[key]) is int and spec[key] == value, "ALLOCATION:" + key)
    require(
        spec["smoke"]
        == {"task": "fmtlib__fmt-2310", "repeats": 1, "trial_count": 3, "request_cap": 72},
        "SMOKE",
    )
    require(spec["concurrency_group"] == "context-ablation-cpa-8", "CONCURRENCY")
    require(
        spec["execution_order_algorithm"] == "sha256_task_repeat_blocks_then_sha256_arms_v1",
        "ORDER",
    )
    require(
        spec["gates"]
        == {
            "ci_workflow": "ci.yml",
            "ci_jobs": ["python-and-cpp", "sdk-contract", "docker-integration"],
            "same_source_commit": True,
            "offline_tests": True,
            "smoke_required_for_full": True,
            "smoke_complete_trials": 3,
            "smoke_known_usage": True,
            "smoke_scoring_complete": True,
            "decision_rule": (
                "task_equal_cold_success_delta_gte_0_and_capped_calls_delta_lt_0"
                "_and_actual_input_tokens_delta_lte_0"
            ),
            "cold_success_tolerance_percentage_points": 0,
        },
        "GATE_POLICY",
    )
    # A localized protocol inherits all model, context, qualified-task and time contracts.
    inherited = set(parent) - {
        "schema",
        "campaign",
        "parent_protocol",
        "parent_protocol_sha256",
        "arms",
        "repeats",
        "trial_count",
        "formal_request_cap",
        "max_parallel",
        "smoke",
        "execution_order_seed",
        "execution_order_algorithm",
        "scoring",
    }
    require(not (inherited & set(spec)), "PARENT_OVERRIDE_FORBIDDEN")
    p = {**parent, **spec}
    p["treatments"] = {arm: dict.fromkeys(shared.FLAGS, False) for arm in ARMS}
    p["batch_id"] = CAMPAIGN
    p["execution_order"] = {
        scope: [row["attempt_id"] for row in trials(p, scope)] for scope in ("smoke", "full")
    }
    p["input_policy"] = "identical frozen task and public feedback; arm-specific search interface"
    p["paired_analysis"] = spec["scoring"]["pairing"]
    return p


def trials(p, scope):
    require(scope in {"smoke", "full"}, "SCOPE")
    tasks = p["tasks"] if scope == "full" else [p["smoke"]["task"]]
    repeats = range(1, 3) if scope == "full" else (1,)
    seed = f"{p['execution_order_seed']}/{scope}"
    blocks = sorted(
        ((task, repeat) for task in tasks for repeat in repeats),
        key=lambda pair: digest([seed, *pair]),
    )
    rows = []
    for block_index, (task, repeat) in enumerate(blocks):
        arms = sorted(ARMS, key=lambda arm: digest([seed, task, repeat, arm]))
        for position, arm in enumerate(arms):
            index = len(rows)
            rows.append(
                {
                    "trial_index": index,
                    "job_key": f"trial-{index + 1:03d}",
                    "block_index": block_index,
                    "block_position": position,
                    "instance_id": task,
                    "repeat": repeat,
                    "arm": arm,
                    "scope": scope,
                    "attempt_id": f"{p['campaign']}/{scope}/{task}/{arm}/repeat-{repeat}",
                    "request_cap": 24,
                }
            )
    return rows


def source_hashes():
    result = shared.source_hashes()
    for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        result[str(path.relative_to(ROOT))] = sha(path)
    return result


def source_commit():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def context_policy(p):
    return ContextPolicy.from_dict({**p["context_policy"], **dict.fromkeys(shared.FLAGS, False)})


def visible_feedback(p, instance, source_tree_sha256):
    prefix = f"qualification/{instance}/"
    names = ("baseline-configure.log", "baseline-build.log", "baseline-ctest.log")
    logs = []
    archive_hash = None
    for path in shared.qualification_archives(p):
        with tarfile.open(path) as archive:
            members = archive.getmembers()
            targets = {prefix + "logs/" + name for name in names}
            if not any(m.name in targets for m in members):
                continue
            require(archive_hash is None, "FEEDBACK_DUPLICATE_TASK")
            archive_hash = sha(path)
            manifest = json.load(archive.extractfile("archive-manifest.json"))
            records = {r["path"]: r for r in manifest["files"]}
            for name in names:
                key = prefix + "logs/" + name
                matches = [m for m in members if m.name == key]
                require(len(matches) == 1 and matches[0].isfile(), "FEEDBACK_LOG_MISSING")
                require(matches[0].size <= 2 * 1024 * 1024, "FEEDBACK_LOG_LIMIT")
                with archive.extractfile(matches[0]) as stream:
                    data = stream.read()
                content_hash = hashlib.sha256(data).hexdigest()
                require(
                    records[key]["sha256"] == content_hash
                    and records[key]["size_bytes"] == len(data),
                    "FEEDBACK_LOG_HASH",
                )
                logs.append({"name": name, "sha256": content_hash, "text": data.decode("utf-8")})
    require(len(logs) == 3, "FEEDBACK_LOG_SET")
    result = {
        "schema": "repropatch.localization-feedback.v1",
        "instance_id": instance.replace("__", "-").lower(),
        "prepared_commit": p["task_contracts"][instance]["prepared_commit"],
        "source_tree_sha256": source_tree_sha256,
        "logs": logs,
    }
    result["feedback_sha256"] = hashlib.sha256(canonical_json(result)).hexdigest()
    require(len(canonical_json(result)) <= 2 * 1024 * 1024, "FEEDBACK_TOTAL_LIMIT")
    return result


def gate_identity(p, scope, protocol):
    return {
        "campaign": p["campaign"],
        "scope": scope,
        "source_commit": source_commit(),
        "source_sha256": source_hashes(),
        "protocol_sha256": sha(protocol),
    }


def validate_gate(gate, identity):
    require(gate.get("schema") == "repropatch.localization-ablation.gate.v1", "GATE_SCHEMA")
    require(gate.get("passed") is True, "GATE_REQUIRED")
    require(all(gate.get(k) == v for k, v in identity.items()), "GATE_IDENTITY")
    require(gate.get("offline_passed") is True, "OFFLINE_GATE_REQUIRED")
    require(gate.get("ci", {}).get("conclusion") == "success", "CI_GATE_REQUIRED")
    if identity["scope"] == "full":
        require(gate.get("smoke", {}).get("passed") is True, "SMOKE_GATE_REQUIRED")


def plan(args):
    shared.first_run()
    p = read_protocol(args.protocol)
    dry = getattr(args, "dry_run", False)
    gate = {} if dry else load(args.gate) if getattr(args, "gate", None) else {}
    if not dry:
        validate_gate(gate, gate_identity(p, args.scope, args.protocol))
    rows = trials(p, args.scope)
    result = {
        "schema": "repropatch.localization-ablation.manifest.v1",
        "protocol": p,
        **gate_identity(p, args.scope, args.protocol),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": 1,
        "dry_run": dry,
        "gate": gate,
        "attempts": rows,
        "matrix": {"include": rows},
        "trial_count": len(rows),
        "request_cap": len(rows) * 24,
        "max_parallel": 8,
        "task_population": p["task_population"],
    }
    result["manifest_sha256"] = digest(result)
    exclusive_save(args.output, result)
    if getattr(args, "github_output", None):
        with args.github_output.open("a") as stream:
            stream.write("matrix=" + json.dumps(result["matrix"]) + "\n")
    print(
        json.dumps({"trial_count": len(rows), "request_cap": len(rows) * 24, "dry_run": dry}),
        flush=True,
    )


def read_manifest(path, protocol_path=PROTOCOL, *, execution=False):
    m = load(path)
    require(m["schema"] == "repropatch.localization-ablation.manifest.v1", "MANIFEST_SCHEMA")
    require(
        m["manifest_sha256"] == digest({k: v for k, v in m.items() if k != "manifest_sha256"}),
        "MANIFEST_HASH",
    )
    require(m["protocol"] == read_protocol(protocol_path), "MANIFEST_PROTOCOL")
    require(m["protocol_sha256"] == sha(protocol_path), "PROTOCOL_HASH")
    require(m["attempts"] == trials(m["protocol"], m["scope"]), "ATTEMPT_MANIFEST")
    require(m["matrix"] == {"include": m["attempts"]}, "MATRIX_MANIFEST")
    require(
        (m["trial_count"], m["request_cap"], m["max_parallel"])
        == (len(m["attempts"]), 24 * len(m["attempts"]), 8),
        "MANIFEST_ALLOCATION",
    )
    if execution:
        shared.first_run()
        require(m["dry_run"] is False, "DRY_PLAN_NOT_EXECUTABLE")
        require(
            m["github_run_id"] and m["github_run_id"] == os.environ.get("GITHUB_RUN_ID"),
            "GITHUB_RUN_ID_CHANGED",
        )
        require(
            m["source_commit"] == source_commit() and m["source_sha256"] == source_hashes(),
            "EXECUTION_SOURCE_CHANGED",
        )
        validate_gate(m["gate"], gate_identity(m["protocol"], m["scope"], protocol_path))
    return m


def gh_json(*args):
    return json.loads(subprocess.check_output(["gh", *args], cwd=ROOT, text=True))


def validate_ci(run, jobs, commit, p):
    require(
        run.get("head_sha") == commit and run.get("event") in {"push", "workflow_dispatch"},
        "CI_SOURCE_MISMATCH",
    )
    require(run.get("path", "").split("@")[0] == ".github/workflows/ci.yml", "CI_WORKFLOW")
    require(
        run.get("status") == "completed" and run.get("conclusion") == "success", "CI_GATE_FAILED"
    )
    for name in p["gates"]["ci_jobs"]:
        matching = [j for j in jobs if j.get("name") == name]
        require(len(matching) == 1 and matching[0].get("conclusion") == "success", "CI_JOB:" + name)


def validate_smoke(result, p, protocol_hash, sources):
    require(result.get("schema") == "repropatch.localization-ablation.aggregate.v1", "SMOKE_SCHEMA")
    require(
        result.get("scope") == "smoke" and result.get("protocol_sha256") == protocol_hash,
        "SMOKE_PROTOCOL",
    )
    require(result.get("source_sha256") == sources, "SMOKE_SOURCE")
    require(not result.get("rejected_artifacts"), "SMOKE_REJECTED_ARTIFACTS")
    expected = trials(p, "smoke")
    rows = result.get("attempts", [])
    require(
        len(rows) == 3
        and {r.get("attempt_id") for r in rows} == {r["attempt_id"] for r in expected},
        "SMOKE_COMPLETENESS",
    )
    for row, frozen in zip(
        sorted(rows, key=lambda r: r["attempt_id"]),
        sorted(expected, key=lambda r: r["attempt_id"]),
        strict=True,
    ):
        require(all(row.get(k) == v for k, v in frozen.items()), "SMOKE_TRIAL_IDENTITY")
        require(type(row.get("accepted")) is bool and not row.get("failure"), "SMOKE_COLD_SCORE")
        usage = row.get("usage") or {}
        require(
            type(usage.get("requests")) is int
            and 0 < usage["requests"] <= 24
            and usage.get("unknown_usage_requests") == 0,
            "SMOKE_USAGE",
        )
        score = row.get("localization_score") or {}
        require(
            score.get("schema") == "repropatch.localization-score.v1"
            and score.get("evidence_status") == "complete"
            and score.get("exposures")
            and score.get("phase_finished")
            and score.get("attempt_id") == row["attempt_id"],
            "SMOKE_LOCALIZATION_SCORE",
        )
    fingerprints = [r.get("prepared_identity", {}).get("visible_feedback_sha256") for r in rows]
    require(all(fingerprints) and len(set(fingerprints)) == 1, "SMOKE_FIXED_FEEDBACK")
    return {"passed": True, "attempts": 3, "results_sha256": digest(result)}


def preflight(args):
    shared.first_run()
    p = read_protocol(args.protocol)
    identity = gate_identity(p, args.scope, args.protocol)
    repo = os.environ.get("GITHUB_REPOSITORY", "lilong555/ReproPatch")
    deadline = time.monotonic() + args.wait_ci
    while True:
        response = gh_json(
            "api",
            f"repos/{repo}/actions/workflows/ci.yml/runs?head_sha={identity['source_commit']}&per_page=100",
        )
        candidates = [
            r
            for r in response["workflow_runs"]
            if r.get("head_sha") == identity["source_commit"]
            and r.get("event") in {"push", "workflow_dispatch"}
        ]
        ci = next(
            (r for r in candidates if r["status"] == "completed" and r["conclusion"] == "success"),
            None,
        )
        if ci is not None:
            break
        require(time.monotonic() < deadline, "SAME_SOURCE_FULL_CI_REQUIRED")
        print(
            json.dumps(
                {"waiting_for_ci": identity["source_commit"], "at": datetime.now(UTC).isoformat()}
            ),
            flush=True,
        )
        time.sleep(min(15, max(0, deadline - time.monotonic())))
    pages = gh_json(
        "api", "--paginate", "--slurp", f"repos/{repo}/actions/runs/{ci['id']}/jobs?per_page=100"
    )
    validate_ci(ci, [j for page in pages for j in page["jobs"]], identity["source_commit"], p)
    tests = sorted(
        str(path.relative_to(ROOT)) for path in (ROOT / "tests").glob("test_localization*.py")
    )
    require(
        tests and (ROOT / "scripts/score_localization.py").is_file(),
        "LOCALIZATION_IMPLEMENTATION_REQUIRED",
    )
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-m", "not docker", *tests], cwd=ROOT, check=True
    )
    smoke = None
    if args.scope == "full":
        require(args.smoke_run and args.smoke_run.isdigit(), "SMOKE_RUN_REQUIRED")
        run = gh_json("api", f"repos/{repo}/actions/runs/{args.smoke_run}")
        same_run = args.smoke_run == os.environ.get("GITHUB_RUN_ID")
        require(run.get("head_sha") == identity["source_commit"], "SMOKE_RUN_SOURCE")
        require(
            same_run or (run.get("status") == "completed" and run.get("conclusion") == "success"),
            "SMOKE_RUN_GATE",
        )
        destination = args.output.parent / "smoke-gate-input"
        require(not destination.exists(), "SMOKE_DOWNLOAD_ALREADY_EXISTS")
        subprocess.run(
            [
                "gh",
                "run",
                "download",
                args.smoke_run,
                "--repo",
                repo,
                "--name",
                f"localization-results-{args.smoke_run}-smoke",
                "--dir",
                str(destination),
            ],
            check=True,
        )
        smoke = validate_smoke(
            load(destination / "results.json"),
            p,
            identity["protocol_sha256"],
            identity["source_sha256"],
        )
        smoke["run_id"] = args.smoke_run
    exclusive_save(
        args.output,
        {
            "schema": "repropatch.localization-ablation.gate.v1",
            **identity,
            "passed": True,
            "offline_passed": True,
            "ci": ci,
            "smoke": smoke,
        },
    )


def status(output, state, **details):
    value = {
        **shared.optional_json(output / "runner-status.json"),
        "schema": "repropatch.localization-ablation.runner-status.v1",
        "state": state,
        "updated_at": datetime.now(UTC).isoformat(),
        "manifest_sha256": shared.optional_json(output / "trial.json").get("manifest_sha256"),
        **details,
    }
    save(output / "runner-status.json", value)
    with (output / "runner-events.jsonl").open("a") as stream:
        stream.write(json.dumps(value) + "\n")


PUBLIC_TASK_FILES = frozenset(
    {
        "task.yaml",
        "control/test.patch",
        "logs/baseline-configure.log",
        "logs/baseline-build.log",
        "logs/baseline-ctest.log",
    }
)


def archive_task_files(p, instance, *, public):
    """Read only current-task allowlisted members during generation."""
    require(instance in p["tasks"], "UNREGISTERED_TASK")
    prefix = f"qualification/{instance}/"
    result = None
    for path in shared.qualification_archives(p):
        with tarfile.open(path) as archive:
            members = archive.getmembers()
            if not any(m.name == prefix + "task.yaml" for m in members):
                continue
            require(result is None, "QUALIFICATION_TASK_DUPLICATE")
            names = [m.name for m in members]
            require(len(names) == len(set(names)), "QUALIFICATION_MEMBER_DUPLICATE")
            root_manifest = json.load(archive.extractfile("archive-manifest.json"))
            records = {r["path"]: r for r in root_manifest["files"]}

            def read(name, records=records):
                key = prefix + name
                member = archive.getmember(key)
                require(
                    member.isfile() and member.size <= 8 * 1024 * 1024, "QUALIFICATION_MEMBER_TYPE"
                )
                with archive.extractfile(member) as stream:
                    data = stream.read()
                require(
                    len(data) == records[key]["size_bytes"]
                    and hashlib.sha256(data).hexdigest() == records[key]["sha256"],
                    "QUALIFICATION_MEMBER_HASH",
                )
                return data

            task_manifest = json.loads(read("manifest.json"))
            selected = (
                PUBLIC_TASK_FILES
                if public
                else {
                    m.name.removeprefix(prefix)
                    for m in members
                    if m.name.startswith(prefix) and m.name != prefix + "manifest.json"
                }
            )
            files = {}
            for name in sorted(selected):
                require(
                    not Path(name).is_absolute()
                    and ".." not in Path(name).parts
                    and ".git" not in Path(name).parts,
                    "QUALIFICATION_MEMBER_PATH",
                )
                data = read(name)
                require(
                    task_manifest[name]["size"] == len(data)
                    and task_manifest[name]["sha256"] == hashlib.sha256(data).hexdigest(),
                    "QUALIFICATION_TASK_MEMBER_HASH",
                )
                files[name] = data
            result = {
                "files": files,
                "manifest": task_manifest,
                "manifest_bytes": read("manifest.json"),
                "archive_sha256": sha(path),
            }
    require(result is not None, "QUALIFICATION_TASK_MISSING")
    return result


def coverage_task(p, instance):
    path = ROOT / "benchmarks/coverage.json"
    require(sha(path) == p["coverage_sha256"], "COVERAGE_HASH")
    coverage = load(path)
    require(coverage["revision"] == p["dataset_revision"], "DATASET_REVISION")
    rows = [r for r in coverage["records"] if r["instance_id"] == instance]
    require(len(rows) == 1 and re.fullmatch(r"[a-f0-9]{40}", rows[0]["base_commit"]), "BASE_COMMIT")
    return rows[0]


def fetch_public_base(p, instance):
    record = coverage_task(p, instance)
    repository = ROOT / ".repropatch/localization-public-base"
    repository.mkdir(parents=True, exist_ok=True)
    if not (repository / ".git").exists():
        preparation_git(repository, "init", "--template=", "-q")
    check = subprocess.run(
        ["git", "-C", str(repository), "cat-file", "-e", record["base_commit"] + "^{commit}"],
        capture_output=True,
        check=False,
    )
    if check.returncode:
        preparation_git(
            repository,
            "fetch",
            "--no-tags",
            "--depth=1",
            "https://github.com/fmtlib/fmt.git",
            record["base_commit"],
        )
    return repository, record["base_commit"]


def prepare_public_task(p, instance, output):
    from qualify_cpp_batch import ADAPTER, BUILD_TEST, archive
    from screen_multiswe import patch_paths

    package = archive_task_files(p, instance, public=True)
    original = Task.from_dict(yaml.safe_load(package["files"]["task.yaml"]), ROOT)
    raw = original.to_dict()
    raw["budget"].update(
        {**p["execution_budget_override"], "model_timeout_seconds": p["model_timeout_seconds"]}
    )
    task = Task.from_dict(raw, ROOT)
    contract = p["task_contracts"][instance]
    require(
        hashlib.sha256(task.source_bytes).hexdigest() == contract["execution_task_sha256"]
        and task.revision == contract["prepared_commit"],
        "PUBLIC_TASK_CONTRACT_CHANGED",
    )
    require(not task.repository.exists(), "PUBLIC_REPOSITORY_EXISTS")
    output.mkdir(parents=True, exist_ok=False)
    public = output / "public-input"
    for name, data in package["files"].items():
        path = public / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    upstream, base = fetch_public_base(p, instance)
    archive(upstream, base, task.repository)
    preparation_git(task.repository, "init", "--template=", "-q", ".")
    patch = public / "control/test.patch"
    tests, special = patch_paths(patch.read_text())
    require(
        tests and not special and all(path.startswith("test/") for path in tests),
        "PUBLIC_TEST_PATCH_SCOPE",
    )
    targets = sorted(
        {Path(path).stem for path in tests if re.fullmatch(r"test/[\w-]+-test\.cc", path)}
    )
    require(targets, "PUBLIC_TEST_TARGETS")
    preparation_git(task.repository, "apply", str(patch))
    cmake = task.repository / "test/CMakeLists.txt"
    original_cmake = cmake.read_text()
    marker = "  add_test(NAME ${name} COMMAND ${name})\n"
    require(marker in original_cmake, "PUBLIC_CTEST_ADAPTER_LAYOUT")
    condition = " OR ".join(f'name STREQUAL "{name}"' for name in targets)
    cmake.write_text(original_cmake.replace(marker, ADAPTER.replace("__CONDITION__", condition)))
    (task.repository / "test/repropatch-build-test.cmake").write_text(BUILD_TEST)
    preparation_git(task.repository, "add", "-f", ".")
    preparation_git(
        task.repository,
        "commit",
        "-qm",
        "Freeze official regression tests and target-build CTest adapter",
    )
    require(
        preparation_git(task.repository, "rev-parse", "HEAD").decode().strip() == task.revision,
        "PUBLIC_PREPARED_COMMIT_MISMATCH",
    )
    with Worktree(task.repository, output / "public-audit-worktree", task.revision) as workspace:
        observed = {
            "repository/" + f.path: {"size": f.size_bytes, "sha256": f.sha256}
            for f in workspace.initial_manifest.files
        }
        expected = {
            key: value
            for key, value in package["manifest"].items()
            if key.startswith("repository/")
        }
        require(observed == expected, "PUBLIC_SOURCE_MANIFEST_MISMATCH")
    task_path = output / "qualified-contract/task.yaml"
    task_path.parent.mkdir()
    task_path.write_bytes(task.source_bytes)
    projection = {
        "schema": "repropatch.localization-public-qualification.v1",
        "instance_id": instance,
        "archive_sha256": package["archive_sha256"],
        "base_commit": base,
        "prepared_commit": task.revision,
        "task_sha256": sha(task_path),
        "members": {name: package["manifest"][name] for name in sorted(PUBLIC_TASK_FILES)},
    }
    save(output / "qualification-public.json", projection)
    save(output / "common-input.json", {"task_id": task.id, "prepared_commit": task.revision})
    save(
        output / "prepared.json",
        {
            "instance_id": instance,
            "task": str(task_path),
            "qualification": str(output / "qualified-contract/result.json"),
            "qualification_projection": str(output / "qualification-public.json"),
            "common_input": str(output / "common-input.json"),
        },
    )
    return task


def ensure_image(p):
    observed = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", p["image"]],
        capture_output=True,
        text=True,
        check=False,
    )
    if observed.returncode:
        subprocess.run(["docker", "pull", p["image"]], check=True, timeout=600)
        observed = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{.Id}}", p["image"]],
            capture_output=True,
            text=True,
            check=True,
        )
    require(observed.stdout.strip() == p["image_id"], "IMMUTABLE_IMAGE_CHANGED")


def prepare(args):
    m = read_manifest(args.manifest, args.protocol, execution=True)
    row = shared.selected(m, args)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    identity = {
        **row,
        "schema": "repropatch.localization-ablation.trial.v1",
        "manifest_sha256": m["manifest_sha256"],
        "runner": shared.runner_identity(),
    }
    exclusive_save(output / "trial.json", identity)
    exclusive_save(output / "manifest.json", m)
    try:
        exclusive_save(
            ROOT
            / ".repropatch/localization-attempts"
            / m["manifest_sha256"]
            / (row["job_key"] + ".json"),
            identity,
        )
        status(output, "PREPARING", **row)
        LocalUsageLedger.create_scoped(
            output / "usage.sqlite3",
            {row["attempt_id"]: 24},
            context_policy=context_policy(m["protocol"]),
        )
        prepare_public_task(m["protocol"], row["instance_id"], output / "prepared")
        ensure_image(m["protocol"])
        settings = load(output / "prepared/prepared.json")
        require(
            sha(Path(settings["task"]))
            == m["protocol"]["task_contracts"][row["instance_id"]]["execution_task_sha256"],
            "TASK_CONTRACT_HASH",
        )
        task = Task.load(Path(settings["task"]))
        require(
            subprocess.check_output(
                ["git", "-C", str(task.repository), "rev-parse", "HEAD"], text=True
            ).strip()
            == task.revision,
            "FEEDBACK_SOURCE_COMMIT",
        )
        source_hash = freeze_base_source(task, output / "prepared")
        exclusive_save(
            output / "visible-feedback.json",
            visible_feedback(m["protocol"], row["instance_id"], source_hash),
        )
        exclusive_save(
            output / "prepared-identity.json",
            {
                "task_sha256": sha(Path(settings["task"])),
                "qualification_projection_sha256": sha(Path(settings["qualification_projection"])),
                "common_input_sha256": sha(Path(settings["common_input"])),
                "prepared_sha256": sha(output / "prepared/prepared.json"),
                "source_tree_sha256": source_hash,
                "source_base_sha256": sha(output / "prepared/source-base.tar"),
                "source_bundle_sha256": sha(output / "prepared/source-base.bundle"),
                "visible_feedback_sha256": sha(output / "visible-feedback.json"),
            },
        )
        status(output, "PREPARED", **row)
        return 0
    except Exception as error:
        status(output, "PREPARATION_FAILED", **row, **shared.error_details(error))
        finish(m, row, output, failure="PREPARATION_FAILED")
        return 2


def freeze_base_source(task, output):
    require(
        preparation_git(task.repository, "rev-list", "--count", task.revision).decode().strip()
        == "1",
        "PUBLIC_SOURCE_HISTORY_REQUIRED",
    )
    preparation_git(task.repository, "bundle", "create", str(output / "source-base.bundle"), "HEAD")
    with Worktree(task.repository, output / "feedback-worktree", task.revision) as workspace:
        manifest = workspace.initial_manifest
        with tarfile.open(output / "source-base.tar", "x") as archive:
            for entry in manifest.files:
                path = workspace.path / entry.path
                info = archive.gettarinfo(str(path), arcname=entry.path)
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ""
                with path.open("rb") as stream:
                    archive.addfile(info, stream)
        return manifest.sha256


def worker_command(row, settings, output, p):
    return shared.worker_command(row, settings, output, p) + [
        "--localization-mode",
        row["arm"],
        "--localization-tool-budget",
        str(p["localization_tool_budget"]),
        "--localization-step-budget",
        str(p["localization_step_budget"]),
        "--localization-feedback-file",
        str(output / "visible-feedback.json"),
    ]


def run(args):
    m = read_manifest(args.manifest, args.protocol, execution=True)
    row = shared.selected(m, args)
    p, output = m["protocol"], args.output.resolve(strict=True)
    identity = load(output / "trial.json")
    require(
        identity["attempt_id"] == row["attempt_id"]
        and identity["manifest_sha256"] == m["manifest_sha256"],
        "OUTPUT_IDENTITY",
    )
    require(identity["runner"] == shared.runner_identity(), "RUNNER_ID_CHANGED")
    require(load(output / "runner-status.json")["state"] == "PREPARED", "PREPARED_REQUIRED")
    exclusive_save(output / "execution-started.json", {"attempt_id": row["attempt_id"]})
    failure, worker_exit = None, None
    try:
        settings = load(output / "prepared/prepared.json")
        frozen = load(output / "prepared-identity.json")
        for key, path in (
            ("task_sha256", settings["task"]),
            ("qualification_projection_sha256", settings["qualification_projection"]),
            ("common_input_sha256", settings["common_input"]),
            ("prepared_sha256", output / "prepared/prepared.json"),
            ("source_base_sha256", output / "prepared/source-base.tar"),
            ("source_bundle_sha256", output / "prepared/source-base.bundle"),
            ("visible_feedback_sha256", output / "visible-feedback.json"),
        ):
            require(sha(Path(path)) == frozen[key], "PREPARED_INPUT_CHANGED")
        ledger = LocalUsageLedger(output / "usage.sqlite3")
        require(
            ledger.policy == context_policy(p) and ledger.summary()["requests"] == 0,
            "UNUSED_BASELINE_LEDGER_REQUIRED",
        )
        require(bool(os.environ.get(p["api_key_env"])), "API_KEY_ENV_REQUIRED")
        os.environ["CPA_JOB_MEMBER"] = row["scope"] + "-" + row["job_key"]
        status(output, "RUNNING", **row)
        with CPASession(output / "cpa", campaign=p["campaign"]) as session:
            session.healthy()
            events = [
                json.loads(line)
                for line in (output / "cpa/lease-events.jsonl").read_text().splitlines()
                if line.strip()
            ]
            require(
                any(
                    e.get("action") == "enter" and e["result"].get("request_retry") == 0
                    for e in events
                ),
                "CPA_ZERO_RETRY_EVIDENCE_REQUIRED",
            )
            exclusive_save(
                output / "cpa/claim.json", session.claim(row["attempt_id"], row["scope"], 24)
            )
            worker_exit = shared.supervised(
                worker_command(row, settings, output, p),
                output / "worker.log",
                p["worker_timeout_seconds"],
                p,
                session,
            )
            session.healthy()
        if not (output / "worker/result.json").is_file():
            failure = "MISSING_WORKER_RESULT"
    except Exception as error:
        failure = "WORKER_INFRASTRUCTURE_FAILED"
        status(output, failure, **row, **shared.error_details(error))
    finish(m, row, output, failure=failure, worker_exit=worker_exit)
    status(output, failure or "AWAITING_ISOLATED_SCORING", **row, worker_exit=worker_exit)
    return 2 if failure else 0


def finish(m, row, output, *, failure=None, worker_exit=None):
    old = shared.optional_json(output / "summary.json")
    worker = shared.optional_json(output / "worker/result.json")
    cold = shared.optional_json(output / "score/score.json")
    localization = shared.optional_json(output / "localization-score.json")
    usage = None
    if (output / "usage.sqlite3").is_file():
        try:
            ledger = LocalUsageLedger(output / "usage.sqlite3")
            usage = ledger.summary(row["attempt_id"])
            with ledger.connect() as db:
                db.row_factory = sqlite3.Row
                raw = [
                    dict(r)
                    for r in db.execute(
                        "SELECT * FROM requests WHERE attempt=? ORDER BY sent_at",
                        (row["attempt_id"],),
                    )
                ]
            save(output / "raw-usage.json", raw)
        except (ValueError, sqlite3.Error):
            failure = failure or "USAGE_LEDGER_UNREADABLE"
    failure = failure or old.get("failure")
    result = {
        "schema": "repropatch.localization-ablation.result.v1",
        **row,
        "manifest_sha256": m["manifest_sha256"],
        "protocol_sha256": m["protocol_sha256"],
        "source_sha256": m["source_sha256"],
        "task_population": m["task_population"],
        "runner": load(output / "trial.json")["runner"],
        "failure": failure,
        "worker_exit": worker_exit if worker_exit is not None else old.get("worker_exit"),
        "classification": ("preparation" if failure == "PREPARATION_FAILED" else "infrastructure")
        if failure
        else cold.get("classification", "pending"),
        "accepted": None if failure else cold.get("accepted"),
        "score": cold,
        "localization_score": {**localization, "attempt_id": row["attempt_id"]}
        if localization
        else {},
        "usage": usage,
        "first_request": shared.first_request_identity(output),
        "prepared_identity": shared.optional_json(output / "prepared-identity.json"),
        "stop_reason": worker.get("stop_reason") or worker.get("native_reason"),
        "runner_status": shared.optional_json(output / "runner-status.json"),
    }
    save(output / "summary.json", result)
    return result


def scorer_request(m, row, output):
    settings = load(output / "prepared/prepared.json")
    return {
        "schema": "repropatch.localization-score.request.v1",
        **row,
        "worker_result": str(output / "worker/result.json"),
        "usage_ledger": str(output / "usage.sqlite3"),
        "execution_task": settings["task"],
        "prepared_commit": m["protocol"]["task_contracts"][row["instance_id"]]["prepared_commit"],
        "dataset": str(ROOT / ".repropatch/inputs/dataset"),
        "repository": str(ROOT / ".repropatch/inputs/fmt"),
        "source_sha256": m["source_sha256"],
        "protocol_sha256": m["protocol_sha256"],
        "cold_score": str(output / "score/score.json"),
        "budgets": {
            "localization_tools": 8,
            "localization_steps": 4,
            "total_tools": 48,
            "total_requests": 24,
        },
    }


def restore_bundle_repository(bundle, destination, commit, tree_sha256):
    require(not destination.exists(), "SCORING_REPOSITORY_EXISTS")
    destination.mkdir(parents=True)
    preparation_git(destination, "init", "--template=", "-q")
    heads = preparation_git(destination, "bundle", "list-heads", str(bundle)).decode().splitlines()
    require(heads == [commit + " HEAD"], "SCORING_BUNDLE_HEADS")
    preparation_git(destination, "fetch", "--no-tags", str(bundle), "HEAD")
    preparation_git(destination, "checkout", "--detach", "-q", commit)
    require(
        preparation_git(destination, "rev-parse", "--show-toplevel").decode().strip()
        == str(destination.resolve()),
        "SCORING_REPOSITORY_ROOT",
    )
    require(
        preparation_git(destination, "rev-parse", "HEAD").decode().strip() == commit,
        "SCORING_PREPARED_COMMIT",
    )
    require(
        preparation_git(destination, "rev-list", "--count", "HEAD").decode().strip() == "1",
        "SCORING_SOURCE_HISTORY",
    )
    preparation_git(destination, "diff", "--quiet", "HEAD", "--")
    with Worktree(
        destination, destination.with_name(destination.name + "-audit"), commit
    ) as workspace:
        require(workspace.initial_manifest.sha256 == tree_sha256, "SCORING_BUNDLE_SOURCE_CHANGED")


def restore_private_qualification(output, settings, frozen):
    import formal_benchmark
    from verify_qualification_evidence import verify_tree

    m, row = load(output / "manifest.json"), load(output / "trial.json")
    p = m["protocol"]
    package = archive_task_files(p, row["instance_id"], public=False)
    original = output / "scoring-qualification-original"
    original.mkdir()
    for name, data in package["files"].items():
        target = original / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (original / "manifest.json").write_bytes(package["manifest_bytes"])
    bundle = output / "prepared/source-base.bundle"
    require(sha(bundle) == frozen["source_bundle_sha256"], "SCORING_BUNDLE_HASH")
    commit = p["task_contracts"][row["instance_id"]]["prepared_commit"]
    restore_bundle_repository(bundle, original / "repository", commit, frozen["source_tree_sha256"])
    require(not verify_tree(original, package["manifest"]), "SCORING_QUALIFICATION_MANIFEST")
    contract = formal_benchmark.prepare_execution_contract(
        original,
        output / "scoring-qualified-contract",
        p["model_timeout_seconds"],
        p["execution_budget_override"],
    )
    require(sha(contract / "task.yaml") == frozen["task_sha256"], "SCORING_EXECUTION_TASK_CHANGED")
    target = Path(settings["qualification"]).parent
    require(not Path(settings["qualification"]).exists(), "SCORING_QUALIFICATION_EXISTS")
    shutil.copytree(contract, target, dirs_exist_ok=True)
    require(
        preparation_git(target / "repository", "rev-parse", "HEAD").decode().strip() == commit,
        "SCORING_PREPARED_COMMIT",
    )
    require(not verify_tree(target, load(target / "manifest.json")), "SCORING_EXECUTION_MANIFEST")
    save(
        output / "scoring-qualification-identity.json",
        {
            "schema": "repropatch.localization-scoring-qualification.v1",
            "archive_sha256": package["archive_sha256"],
            "prepared_commit": commit,
            "source_tree_sha256": frozen["source_tree_sha256"],
            "source_bundle_sha256": frozen["source_bundle_sha256"],
            "qualification_sha256": sha(Path(settings["qualification"])),
            "task_sha256": sha(target / "task.yaml"),
        },
    )


def restore_scoring_base(output):
    settings = load(output / "prepared/prepared.json")
    frozen = load(output / "prepared-identity.json")
    archive_path = output / "prepared/source-base.tar"
    require(sha(archive_path) == frozen["source_base_sha256"], "SCORING_BASE_HASH")
    source = output / "scoring-source"
    require(not source.exists(), "SCORING_SOURCE_EXISTS")
    with tarfile.open(archive_path) as archive:
        require(
            all(
                (member.isfile() or member.isdir())
                and not Path(member.name).is_absolute()
                and ".." not in Path(member.name).parts
                for member in archive.getmembers()
            ),
            "SCORING_BASE_UNSAFE",
        )
        source.mkdir()
        archive.extractall(source, filter="data")
    require(
        source_manifest(source).sha256 == frozen["source_tree_sha256"],
        "SCORING_BASE_SOURCE_CHANGED",
    )
    restore_private_qualification(output, settings, frozen)
    return source


def localization_score_commands(m, row, output):
    from qualify_cpp_batch import records

    settings = load(output / "prepared/prepared.json")
    task = Task.load(Path(settings["task"]))
    source = output / "scoring-source"
    record = next(
        r
        for r in records(ROOT / ".repropatch/inputs/dataset")
        if r["instance_id"] == row["instance_id"]
    )
    patch = output / "reference.patch"
    with patch.open("x") as stream:
        stream.write(record["fix_patch"])
    worker = load(output / "worker/result.json")
    run_dir = Path(worker["native_artifact_dir"]).resolve(strict=True)
    require(
        run_dir.is_relative_to((output / "worker/runs").resolve()), "SCORING_RUN_OUTSIDE_ATTEMPT"
    )
    prefix = [sys.executable, str(ROOT / "scripts/score_localization.py")]
    return [
        (
            prefix
            + [
                "labels",
                "--patch",
                str(patch),
                "--source-root",
                str(source),
                "--task-id",
                task.id,
                "--output",
                str(output / "localization-labels.json"),
            ],
            "localization-labels.log",
        ),
        (
            prefix
            + [
                "score",
                "--run-dir",
                str(run_dir),
                "--labels",
                str(output / "localization-labels.json"),
                "--tool-budget",
                "8",
                "--phase",
                "localization",
                "--task-id",
                task.id,
                "--arm",
                row["arm"],
                "--repeat-id",
                str(row["repeat"]),
                "--cold-score",
                str(output / "score/score.json"),
                "--output",
                str(output / "localization-score.json"),
            ],
            "localization-score.log",
        ),
    ]


def score(args):
    m = read_manifest(args.manifest, args.protocol, execution=True)
    row = shared.selected(m, args)
    output = args.output.resolve(strict=True)
    identity = load(output / "trial.json")
    require(
        identity["attempt_id"] == row["attempt_id"]
        and identity["manifest_sha256"] == m["manifest_sha256"],
        "SCORING_IDENTITY",
    )
    exclusive_save(
        output / "scoring-started.json",
        {"attempt_id": row["attempt_id"], "runner": shared.runner_identity()},
    )
    if not (output / "worker/result.json").is_file():
        finish(m, row, output, failure="MISSING_WORKER_RESULT")
        return 2
    p = m["protocol"]
    failure = None
    try:
        shared.prepare_inputs(m, row, output)
        settings = load(output / "prepared/prepared.json")
        restore_scoring_base(output)
        cold_command = [
            sys.executable,
            str(ROOT / "scripts/score_benchmark_attempt.py"),
            "--worker-result",
            str(output / "worker/result.json"),
            "--attempt-id",
            row["attempt_id"],
            "--qualification",
            settings["qualification"],
            "--dataset",
            str(ROOT / ".repropatch/inputs/dataset"),
            "--repository",
            str(ROOT / ".repropatch/inputs/fmt"),
            "--timeout",
            str(p["oracle_timeout_seconds"]),
            "--output",
            str(output / "score"),
        ]
        status(output, "SCORING", **row)
        shared.supervised(cold_command, output / "score.log", p["scorer_timeout_seconds"], p)
        exclusive_save(output / "localization-score-request.json", scorer_request(m, row, output))
        for command, logfile in localization_score_commands(m, row, output):
            require(
                shared.supervised(command, output / logfile, p["scorer_timeout_seconds"], p) == 0,
                "LOCALIZATION_SCORER_FAILED",
            )
        value = load(output / "localization-score.json")
        require(
            value.get("schema") == "repropatch.localization-score.v1"
            and value.get("arm") == row["arm"]
            and value.get("repeat_id") == row["repeat"],
            "LOCALIZATION_SCORE_IDENTITY",
        )
        require((output / "score/score.json").is_file(), "COLD_SCORE_MISSING")
    except Exception as error:
        failure = "SCORING_INFRASTRUCTURE_FAILED"
        status(output, failure, **row, **shared.error_details(error))
    result = finish(m, row, output, failure=failure)
    status(output, failure or "FINISHED", **row)
    return 2 if result["classification"] in {"infrastructure", "preparation", "pending"} else 0


def unpack(args):
    expected = args.archive.with_name(args.archive.name + ".sha256").read_text().split()[0]
    require(sha(args.archive) == expected, "ARCHIVE_HASH")
    require(not args.output.exists(), "ARCHIVE_DESTINATION_EXISTS")
    with tarfile.open(args.archive) as archive:
        members = archive.getmembers()
        names = [m.name for m in members]
        require(len(names) == len(set(names)), "ARCHIVE_DUPLICATE")
        require(
            all(
                m.isfile() and not Path(m.name).is_absolute() and ".." not in Path(m.name).parts
                for m in members
            ),
            "ARCHIVE_UNSAFE",
        )
        manifest = json.load(archive.extractfile("archive-manifest.json"))
        require(
            set(names) == {r["path"] for r in manifest["files"]} | {"archive-manifest.json"},
            "ARCHIVE_MEMBERS",
        )
        for row in manifest["files"]:
            require(archive.getmember(row["path"]).size == row["size_bytes"], "ARCHIVE_SIZE")
            with archive.extractfile(row["path"]) as stream:
                require(
                    hashlib.file_digest(stream, "sha256").hexdigest() == row["sha256"],
                    "ARCHIVE_CONTENT_HASH",
                )
        args.output.mkdir(parents=True)
        archive.extractall(args.output, filter="data")


def paired_statistics(rows, left, right):
    pairs = shared.paired_statistics(rows, left, right)
    task_means = []
    for task in sorted({r["instance_id"] for r in rows}):
        repeats = [r for r in pairs["pairs"] if r["instance_id"] == task]
        values = {"instance_id": task, "repeats": len(repeats)}
        for field in ("pass_difference", "input_tokens_difference", "output_tokens_difference"):
            observed = [r[field] for r in repeats]
            values[field] = (
                sum(observed) / len(observed) if all(v is not None for v in observed) else None
            )
        task_means.append(values)
    return {
        "left": left,
        "right": right,
        "direction": "right_minus_left",
        "task_means": task_means,
        "repeat_pairs": pairs["pairs"],
    }


def localization_statistics(rows, p, scope):
    from repropatch.localization_scoring import read_eligibility_registry, summarize_scores

    scoring = p["scoring"]
    registry_file = Path(scoring["eligibility_file"])
    require(
        not registry_file.is_absolute() and ".." not in registry_file.parts,
        "ELIGIBILITY_REGISTRY_PATH",
    )
    registrations = read_eligibility_registry(
        ROOT / registry_file,
        scoring["eligibility_sha256"],
        instance_ids=p["tasks"],
        task_contracts=p["task_contracts"],
        qualification_archive_sha256=p["qualification_archive_sha256"],
        source_protocol_sha256=p.get("parent_protocol_sha256"),
    )

    tasks = p["tasks"] if scope == "full" else [p["smoke"]["task"]]
    scores = [r["localization_score"] for r in rows if r.get("localization_score")]
    outcomes = {}
    for row in rows:
        key = (row["instance_id"].replace("__", "-").lower(), row["arm"], row["repeat"])
        require(key not in outcomes, "DUPLICATE_LOCALIZATION_ACCOUNTING")
        score = row.get("localization_score") or {}
        outcomes[key] = {
            "provider_usage": row.get("usage") or score.get("provider_usage"),
            "cold_verification": row.get("score") or score.get("cold_verification"),
        }
    result = summarize_scores(
        scores,
        task_ids=[task.replace("__", "-").lower() for task in tasks],
        arms=ARMS,
        repeat_ids=(1, 2) if scope == "full" else (1,),
        tool_budget=p["localization_tool_budget"],
        eligibility_by_task=registrations,
        outcomes_by_run=outcomes,
    )
    result["complete_score_runs"] = sum(
        s.get("evidence_status") == "complete" and s.get("status") == "scored" for s in scores
    )
    result["eligibility_sha256"] = scoring["eligibility_sha256"]
    result["all_actual_scores_complete"] = (
        result["complete_score_runs"] == result["expected_runs"]
        and len(scores) == result["expected_runs"]
    )
    return result


def default_decisions(localization, paired):
    decisions = []
    for comparison in paired:
        contrast = comparison["right"] + "-" + comparison["left"]
        matches = [
            r
            for r in localization.get("paired", [])
            if r["contrast"] == contrast and r["metric"] == "capped_first_hit_tools"
        ]
        cap = matches[0] if len(matches) == 1 else {}
        costs = [r["input_tokens_difference"] for r in comparison["task_means"]]
        cold = [r["pass_difference"] for r in comparison["task_means"]]
        complete = (
            localization.get("missing_label_tasks") == 0
            and localization.get("complete_score_runs") == localization.get("expected_runs")
            and localization.get("eligible_tasks", 0) > 0
            and cap.get("task_denominator") == localization.get("eligible_tasks")
            and cap.get("mean_difference") is not None
            and all(value is not None for value in [*costs, *cold])
        )
        input_delta = sum(costs) / len(costs) if all(v is not None for v in costs) else None
        cold_delta = sum(cold) / len(cold) if all(v is not None for v in cold) else None
        accept = complete and cold_delta >= 0 and input_delta <= 0 and cap["mean_difference"] < 0
        decisions.append(
            {
                "contrast": contrast,
                "evidence_complete": complete,
                "default_criteria_met": bool(accept),
                "task_equal_cold_success_difference": cold_delta,
                "task_equal_actual_input_tokens_difference": input_delta,
                "task_equal_capped_calls_difference": cap.get("mean_difference"),
            }
        )
    return decisions


def aggregate(args):
    m = read_manifest(args.manifest, args.protocol)
    require(getattr(args, "scope", None) in {None, m["scope"]}, "SCOPE_MISMATCH")
    expected = {r["attempt_id"]: r for r in m["attempts"]}
    found, rejected = {}, []
    for path in sorted(args.source.rglob("summary.json")):
        try:
            row = load(path)
            require(
                row.get("schema") == "repropatch.localization-ablation.result.v1"
                and row.get("attempt_id") in expected
                and row.get("manifest_sha256") == m["manifest_sha256"],
                "FOREIGN_RESULT",
            )
            found.setdefault(row["attempt_id"], []).append(row)
        except (ValueError, OSError) as error:
            rejected.append({"path": str(path), "reason": str(error)})
    rows = []
    for key, frozen in expected.items():
        candidates = found.get(key, [])
        if (
            len(candidates) == 1
            and all(candidates[0].get(k) == v for k, v in frozen.items())
            and candidates[0].get("source_sha256") == m["source_sha256"]
            and candidates[0].get("protocol_sha256") == m["protocol_sha256"]
        ):
            row = candidates[0]
        else:
            row = {
                **frozen,
                "classification": "infrastructure" if candidates else "missing",
                "accepted": None,
                "usage": None,
                "failure": "DUPLICATE_OR_IDENTITY_MISMATCH" if candidates else "MISSING_SUMMARY",
            }
        rows.append(row)
    result = {
        "schema": "repropatch.localization-ablation.aggregate.v1",
        "scope": m["scope"],
        "manifest_sha256": m["manifest_sha256"],
        "protocol_sha256": m["protocol_sha256"],
        "source_sha256": m["source_sha256"],
        "source_commit": m["source_commit"],
        "task_population": m["task_population"],
        "registered_trials": len(rows),
        "attempts": rows,
        "rejected_artifacts": rejected,
        "automatic_reruns": 0,
        "arms": {},
        "paired_differences": [
            paired_statistics(rows, a, b) for a, b in zip(ARMS[:-1], ARMS[1:], strict=True)
        ],
    }
    try:
        result["localization"] = localization_statistics(rows, m["protocol"], m["scope"])
    except (ValueError, KeyError, TypeError) as error:
        result["localization"] = {"status": "invalid", "error": str(error)}
    result["default_decisions"] = default_decisions(
        result["localization"], result["paired_differences"]
    )
    lines = [
        "# Localization Ablation",
        "",
        "Population: 19 previously exposed development tasks.",
        "",
        "| Arm | N | Cold pass | Missing outcome | Input token mean |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for arm in ARMS:
        selected = [r for r in rows if r["arm"] == arm]
        stats = {
            "N": len(selected),
            "pass": sum(r.get("accepted") is True for r in selected),
            "unknown_outcome": sum(r.get("accepted") is None for r in selected),
            "classifications": dict(Counter(r["classification"] for r in selected)),
            "input_tokens": shared.token_statistics(selected, "input_tokens"),
            "output_tokens": shared.token_statistics(selected, "output_tokens"),
        }
        result["arms"][arm] = stats
        lines.append(
            f"| {arm} | {stats['N']} | {stats['pass']} | {stats['unknown_outcome']} | "
            f"{stats['input_tokens']['all_trial_mean']} |"
        )
    lines += [
        "",
        "All registered trials are retained. Missing usage remains null.",
        "Paired costs first average repeats within task. Localization scores retain "
        "the independent scorer's eligibility and censored outcomes.",
    ]
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / "results.json", result)
    (args.output / "summary.md").write_text("\n".join(lines) + "\n")
    if m["scope"] == "smoke":
        validate_smoke(result, m["protocol"], m["protocol_sha256"], m["source_sha256"])
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "preflight", "prepare", "run", "score", "aggregate", "unpack"):
        sub = commands.add_parser(name)
        sub.add_argument("--output", type=Path, required=True)
        if name == "unpack":
            sub.add_argument("--archive", type=Path, required=True)
            continue
        sub.add_argument("--protocol", type=Path, default=PROTOCOL)
        sub.add_argument(
            "--scope", choices=("smoke", "full"), required=name in {"plan", "preflight"}
        )
        if name == "plan":
            sub.add_argument("--dry-run", action="store_true")
            sub.add_argument("--gate", type=Path)
            sub.add_argument("--github-output", type=Path)
        elif name == "preflight":
            sub.add_argument("--smoke-run")
            sub.add_argument("--wait-ci", type=int, default=1200)
        else:
            sub.add_argument("--manifest", type=Path, required=True)
        if name in {"prepare", "run", "score"}:
            selection = sub.add_mutually_exclusive_group(required=True)
            selection.add_argument("--attempt-id")
            selection.add_argument("--trial-index", type=int)
        if name == "aggregate":
            sub.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    return globals()[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
