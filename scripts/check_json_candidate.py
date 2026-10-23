"""固定 nlohmann/json 原始源码、官方测试及完整 98 项原生 Oracle。"""

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from check_multiswe_reference import EVALUATOR_COMMIT
from prepare_mini_environment import set_container_read_permissions
from prepare_multiswe_task import git
from prepare_simdjson_task import archive

from repropatch.task import Task, resolve_task
from repropatch.workspace import Worktree

BASE = "e6cafa573aac6ed9227f752a5371c0b3f436307d"
IMAGE = "sha256:85df2a93b8024356d4f10a729382a9a0663f73b3c0adc312a36dadb962e86477"
TEST_SHA = "45c07d5e45497738b0f5305e0416b0ccb06042982d862c6a74f3868168c409e4"
REFERENCE_SHA = "809d83d243aff95215f0f089dfb060c7e6f70bfe2158c5fb756556abcb67e9f1"
CONFIGURE = [
    "cmake",
    "-S",
    "/src",
    "-B",
    "/build",
    "-DJSON_BuildTests=ON",
    "-DJSON_TestDataDirectory=/opt/json-test-data",
    "-DCMAKE_CXX_FLAGS=-O1",
]
CTEST = ["ctest", "--test-dir", "/build", "--output-on-failure", "--no-tests=error"]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def record_file(path):
    record = json.loads(path.read_text())
    if (record["org"], record["repo"], record["number"], record["base"]["sha"]) != (
        "nlohmann",
        "json",
        4537,
        BASE,
    ) or any(
        hashlib.sha256(record[key].encode()).hexdigest() != digest
        for key, digest in (("test_patch", TEST_SHA), ("fix_patch", REFERENCE_SHA))
    ):
        raise ValueError("JSON_RECORD_IDENTITY")
    if len(set(record["run_result"]["passed_tests"])) != 98:
        raise ValueError("JSON_NATIVE_TEST_IDENTITY")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--evaluator-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task", type=Path)
    parser.add_argument("--reference-check", action="store_true")
    args = parser.parse_args()
    record = record_file(args.record)
    evaluator = args.evaluator_source.resolve(strict=True)
    if git(evaluator, "rev-parse", "HEAD").decode().strip() != EVALUATOR_COMMIT:
        parser.error("JSON_EVALUATOR_IDENTITY")
    git(evaluator, "diff", "--quiet", "HEAD", "--", "multi_swe_bench")
    patch = args.candidate.read_bytes()
    if len(patch) > 8 * 1024 * 1024:
        parser.error("JSON_CANDIDATE_TOO_LARGE")
    if args.reference_check and patch not in (b"", record["fix_patch"].encode()):
        parser.error("JSON_REFERENCE_IDENTITY")
    if args.task is None and not args.reference_check:
        parser.error("JSON_TASK_REQUIRED")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / "candidate.patch").write_bytes(patch)
    save(output / "record.json", record)
    if args.task is not None:
        resolved = resolve_task(Task.load(args.task))
        provenance = json.loads((resolved.repository_path.parent / "provenance.json").read_text())
        if (
            resolved.image_id != IMAGE
            or resolved.base_commit != provenance["prepared_commit"]
            or provenance["upstream_commit"] != BASE
            or resolved.task.id != "nlohmann-json-4537"
            or list(resolved.task.commands.configure) != CONFIGURE
        ):
            parser.error("JSON_TASK_IDENTITY")
        if patch:
            with Worktree(
                resolved.repository_path, output / "scope-worktree", resolved.base_commit
            ) as work:
                work.apply_patch(patch, resolved.editable_files, resolved.protected_files)
                _, changed = work.validate_changes(
                    resolved.editable_files, resolved.protected_files
                )
            save(output / "scope.json", {"changed_files": list(changed), "worktree_removed": True})
    if not patch and not args.reference_check:
        save(
            output / "oracle-verdict.json",
            {
                "accepted": False,
                "reason": "NO_PATCH",
                "native_tests_executed": False,
                "model_requests": 0,
            },
        )
        return 1
    name = "repropatch-json-oracle-" + uuid.uuid4().hex[:12]
    started = time.monotonic()
    execution = {
        "upstream_commit": BASE,
        "image": IMAGE,
        "model_requests": 0,
        "reference_check": args.reference_check,
        "exit_code": None,
    }
    with tempfile.TemporaryDirectory(dir=output.parent, prefix="json-native-") as temp:
        source = Path(temp) / "source"
        archive(args.repository, BASE, source)
        git(source, "init", "--template=", "-q", ".")
        test_patch = output / "official-test.patch"
        test_patch.write_text(record["test_patch"])
        git(source, "apply", str(test_patch))
        if patch:
            git(source, "apply", str(output / "candidate.patch"))
        if (
            "Regression test for issue #3915 - JSON_DIAGNOSTICS trigger assertion"
            not in (source / "tests/src/unit-diagnostics.cpp").read_text()
        ):
            raise ValueError("JSON_TEST_PATCH_NOT_APPLIED")
        # 原生 FetchContent 测试从只读快照进行本地 Git 克隆。
        git(source, "add", "-f", ".")
        git(
            source,
            "-c",
            "user.name=Benchmark",
            "-c",
            "user.email=benchmark@example.invalid",
            "commit",
            "-qm",
            "固定原生候选与测试",
        )
        set_container_read_permissions(source)
        save(
            output / "source-check.json",
            {
                "test_patch_applied": True,
                "diagnostics_sha256": hashlib.sha256(
                    (source / "tests/src/unit-diagnostics.cpp").read_bytes()
                ).hexdigest(),
                "headers_sha256": {
                    p: hashlib.sha256((source / p).read_bytes()).hexdigest()
                    for p in ("include/nlohmann/json.hpp", "single_include/nlohmann/json.hpp")
                },
                "native_cmake_used": True,
                "assertions_enabled": True,
            },
        )
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
            "--memory=4096m",
            "--memory-swap=4096m",
            "--pids-limit=256",
            "--ulimit=core=0:0",
            "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=128m,mode=1777",
            "--tmpfs=/build:rw,exec,nosuid,nodev,size=3072m,uid=65534,gid=65534,mode=0700",
            "--env=GIT_CONFIG_COUNT=2",
            "--env=GIT_CONFIG_KEY_0=safe.directory",
            "--env=GIT_CONFIG_VALUE_0=/src",
            "--env=GIT_CONFIG_KEY_1=safe.directory",
            "--env=GIT_CONFIG_VALUE_1=/src/.git",
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
                result = subprocess.run(argv, stdout=out, stderr=err, timeout=6000)
            execution["exit_code"] = result.returncode
        except subprocess.TimeoutExpired:
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
    from multi_swe_bench.harness.repos.cpp.nlohmann.json import Json

    observed = Json.parse_log(None, (output / "stdout.log").read_text())
    required = set(record["run_result"]["passed_tests"])
    accepted = (
        execution["exit_code"] == 0
        and execution["container_deleted"]
        and required <= observed.passed_tests
        and not observed.failed_tests
        and not observed.skipped_tests
    )
    save(
        output / "oracle-verdict.json",
        {
            "accepted": bool(accepted),
            "reason": "NATIVE_SUITE_PASSED" if accepted else "NATIVE_BUILD_OR_TEST_FAILED",
            "required_tests": sorted(required),
            "passed_tests": sorted(observed.passed_tests),
            "missing_tests": sorted(required - observed.passed_tests),
            "failed_tests": sorted(observed.failed_tests),
            "skipped_tests": sorted(observed.skipped_tests),
            "native_tests_executed": bool(observed.passed_tests),
            "evaluator_commit": EVALUATOR_COMMIT,
            "model_requests": 0,
        },
    )
    print(
        json.dumps(
            {"accepted": bool(accepted), "required": 98, "passed": len(observed.passed_tests)}
        )
    )
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
