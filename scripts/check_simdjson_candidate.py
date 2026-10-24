"""从固定 simdjson 上游与离线依赖重建，独立执行完整原生测试。"""

import argparse
import json
import shlex
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from check_multiswe_reference import EVALUATOR_COMMIT
from prepare_fmt_task import IMAGE
from prepare_mini_environment import set_container_read_permissions
from prepare_multiswe_task import git
from prepare_simdjson_task import (
    CASES,
    CONFIGURE,
    CTEST,
    DATA_COMMIT,
    adapt_environment,
    archive,
    record_file,
)

from repropatch.task import Task, resolve_task
from repropatch.workspace import Worktree


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--data-repository", type=Path, required=True)
    parser.add_argument("--cxxopts-repository", type=Path, required=True)
    parser.add_argument("--number", type=int, choices=sorted(CASES))
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--evaluator-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference-check", action="store_true")
    args = parser.parse_args()
    record = record_file(args.record, args.number)
    case = CASES[record["number"]]
    resolved = resolve_task(Task.load(args.task))
    provenance = json.loads((resolved.repository_path.parent / "provenance.json").read_text())
    if (
        resolved.image_id != IMAGE
        or resolved.base_commit != provenance["prepared_commit"]
        or resolved.task.id != f"simdjson-simdjson-{record['number']}"
        or list(resolved.task.commands.configure) != CONFIGURE
        or provenance["upstream_commit"] != case["base"]
    ):
        parser.error("SIMDJSON_TASK_IDENTITY")
    evaluator = args.evaluator_source.resolve(strict=True)
    if git(evaluator, "rev-parse", "HEAD").decode().strip() != EVALUATOR_COMMIT:
        parser.error("SIMDJSON_EVALUATOR_IDENTITY")
    git(evaluator, "diff", "--quiet", "HEAD", "--", "multi_swe_bench")
    patch = args.candidate.read_bytes()
    if len(patch) > 8 * 1024 * 1024:
        parser.error("SIMDJSON_CANDIDATE_TOO_LARGE")
    if args.reference_check and patch not in (b"", record["fix_patch"].encode()):
        parser.error("SIMDJSON_REFERENCE_IDENTITY")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / "candidate.patch").write_bytes(patch)
    if not patch and not args.reference_check:
        save(
            output / "oracle-verdict.json",
            {"accepted": False, "reason": "NO_PATCH", "native_tests_executed": False},
        )
        return 1
    if patch:
        with Worktree(
            resolved.repository_path, output / "scope-worktree", resolved.base_commit
        ) as work:
            work.apply_patch(patch, resolved.editable_files, resolved.protected_files)
            _, changed = work.validate_changes(resolved.editable_files, resolved.protected_files)
        save(output / "scope.json", {"changed_files": list(changed), "worktree_removed": True})
    name = "repropatch-simd-oracle-" + uuid.uuid4().hex[:12]
    started = time.monotonic()
    execution = {
        "upstream_commit": case["base"],
        "image": IMAGE,
        "model_requests": 0,
        "dependencies": provenance["dependencies"],
        "reference_check": args.reference_check,
    }
    with tempfile.TemporaryDirectory(dir=output.parent, prefix="simd-oracle-") as tmp:
        source = Path(tmp) / "source"
        archive(args.repository, case["base"], source)
        archive(args.data_repository, DATA_COMMIT, source / "dependencies/.cache/simdjson-data")
        archive(
            args.cxxopts_repository,
            provenance["dependencies"]["cxxopts"],
            source / "dependencies/.cache/cxxopts",
        )
        git(source, "init", "--template=", "-q", ".")
        test_patch = output / "official-test.patch"
        test_patch.write_text(record["test_patch"])
        git(source, "apply", str(test_patch))
        adapt_environment(source)
        if patch:
            git(source, "apply", str(output / "candidate.patch"))
        set_container_read_permissions(source)
        commands = [CONFIGURE, ["cmake", "--build", "/build", "--parallel", "2"], CTEST]
        argv = [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            "--name",
            name,
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
            "--user=65534:65534",
            "--cpus=2",
            "--memory=2048m",
            "--memory-swap=2048m",
            "--pids-limit=128",
            "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777",
            "--tmpfs=/build:rw,exec,nosuid,nodev,size=1024m,uid=65534,gid=65534,mode=0700",
            "--mount",
            f"type=bind,source={source},target=/src,readonly",
            "--workdir=/build",
            IMAGE,
            "bash",
            "-ec",
            " && ".join(shlex.join(c) for c in commands),
        ]
        execution["argv"] = argv
        try:
            with (
                (output / "stdout.log").open("wb") as out,
                (output / "stderr.log").open("wb") as err,
            ):
                result = subprocess.run(argv, stdout=out, stderr=err, timeout=1500)
            execution["exit_code"] = result.returncode
        except subprocess.TimeoutExpired:
            execution["exit_code"] = None
            execution["error"] = "ORACLE_TIME_LIMIT"
        finally:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=30)
            left = subprocess.check_output(
                ["docker", "ps", "-aq", "--filter", "name=^/" + name + "$"], timeout=30
            )
            execution.update(
                container_deleted=not left.strip(), duration_seconds=time.monotonic() - started
            )
            save(output / "execution.json", execution)
    sys.path.insert(0, str(evaluator))
    from multi_swe_bench.harness.repos.cpp.simdjson.simdjson import Simdjson

    observed = Simdjson.parse_log(None, (output / "stdout.log").read_text())
    required = set(record["run_result"]["passed_tests"])
    missing = required - observed.passed_tests
    accepted = (
        execution["exit_code"] == 0
        and execution["container_deleted"]
        and observed.passed_tests == required
    )
    accepted = accepted and not observed.failed_tests and not observed.skipped_tests
    verdict = {
        "accepted": bool(accepted),
        "reason": "NATIVE_SUITE_PASSED" if accepted else "NATIVE_BUILD_OR_TEST_FAILED",
        "required_tests": sorted(required),
        "passed_tests": sorted(observed.passed_tests),
        "failed_tests": sorted(observed.failed_tests),
        "missing_tests": sorted(missing),
        "extra_tests": sorted(observed.passed_tests - required),
        "model_requests": 0,
        "evaluator_commit": EVALUATOR_COMMIT,
        "native_tests_executed": bool(observed.passed_tests),
    }
    save(output / "oracle-verdict.json", verdict)
    print(
        json.dumps(
            {"accepted": accepted, "required": len(required), "passed": len(observed.passed_tests)}
        )
    )
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
