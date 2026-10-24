"""在原始 FMT 源码上构建并执行全部原生测试，作为两组共用的外部 Oracle。"""

import argparse
import hashlib
import io
import json
import shlex
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
from pathlib import Path

from check_multiswe_reference import EVALUATOR_COMMIT
from prepare_fmt_task import CASES, CONFIGURE, CTEST, IMAGE, native_tests, read_record
from prepare_mini_environment import set_container_read_permissions
from prepare_multiswe_task import git

from repropatch.artifacts import AuditBudget
from repropatch.process import run_logged_process
from repropatch.task import Task, resolve_task
from repropatch.workspace import Worktree

PREPARED_COMMITS = {
    4055: "148a69d245a44b1cc74baa6c9e05922fd8cb1b30",
    4310: "512849d9dfdef27c9bc46e410a8fdf9997c8dab6",
    4286: "af86d0892b0da6dcd80528ba391a20ad7cf7e3e0",
    4057: "71fba7a1916d064832dfdd6a8d705aa0a1a07102",
}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    path.chmod(0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--evaluator-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference-check", action="store_true")
    args = parser.parse_args()
    record = read_record(args.record)
    case = CASES[record["number"]]
    resolved = resolve_task(Task.load(args.task))
    if (
        resolved.base_commit != PREPARED_COMMITS[record["number"]]
        or resolved.task.id != f"fmtlib-fmt-{record['number']}"
        or resolved.image_id != IMAGE
        or list(resolved.task.commands.configure) != CONFIGURE
    ):
        parser.error("FMT_TASK_IDENTITY_MISMATCH")
    evaluator = args.evaluator_source.resolve(strict=True)
    if git(evaluator, "rev-parse", "HEAD").decode().strip() != EVALUATOR_COMMIT:
        parser.error("FMT_EVALUATOR_IDENTITY_MISMATCH")
    git(evaluator, "diff", "--quiet", "HEAD", "--", "multi_swe_bench")
    patch = args.candidate.read_bytes()
    if len(patch) > 8 * 1024 * 1024:
        parser.error("FMT_CANDIDATE_TOO_LARGE")
    if args.reference_check and patch not in (b"", record["fix_patch"].encode()):
        parser.error("FMT_REFERENCE_CHECK_REQUIRES_FIXED_PATCH")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    save(output / "record.json", record)
    candidate = output / "candidate.patch"
    candidate.write_bytes(patch)
    candidate.chmod(0o600)
    if not patch and not args.reference_check:
        verdict = {
            "accepted": False,
            "reason": "NO_PATCH",
            "native_tests_executed": False,
            "model_requests": 0,
        }
        save(output / "oracle-verdict.json", verdict)
        print(json.dumps(verdict))
        return 1
    if patch:
        with Worktree(
            resolved.repository_path, output / "scope-worktree", resolved.base_commit
        ) as work:
            work.apply_patch(patch, resolved.editable_files, resolved.protected_files)
            _, changed = work.validate_changes(resolved.editable_files, resolved.protected_files)
            if not changed:
                raise ValueError("FMT_NO_SOURCE_CHANGE")
        save(output / "scope.json", {"changed_files": list(changed), "worktree_removed": True})
    parser_file = evaluator / "multi_swe_bench/harness/repos/cpp/fmtlib/fmt.py"
    save(
        output / "evaluator-source.json",
        {
            "commit": EVALUATOR_COMMIT,
            "parser_sha256": hashlib.sha256(parser_file.read_bytes()).hexdigest(),
            "oracle": "原始源码、官方测试补丁、全量原生构建和 CTest；固定上游 Fmt parser",
            "prepared_ctest_adapter_used": False,
            "official_f2p_p2p_groups": "原始记录为空；本扩展按完整原生测试集合判定",
        },
    )
    name = "repropatch-fmt-oracle-" + uuid.uuid4().hex[:12]
    execution = {
        "upstream_commit": case["base_commit"],
        "image": IMAGE,
        "candidate_sha256": hashlib.sha256(patch).hexdigest(),
        "reference_check": args.reference_check,
        "container_deleted": False,
        "model_requests": 0,
    }
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="fmt-oracle-source-", dir=output.parent) as tmp:
        source = Path(tmp) / "source"
        source.mkdir()
        raw = git(args.repository, "archive", case["base_commit"])
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            archive.extractall(source, filter="data")
        git(source, "init", "--template=", "-q", ".")
        test_patch = Path(tmp) / "test.patch"
        test_patch.write_text(record["test_patch"])
        git(source, "apply", str(test_patch))
        if patch:
            git(source, "apply", str(candidate))
        set_container_read_permissions(source)
        # 此路径使用原生 CMake 文件，跳过适配器所在 prepared 仓库。
        command = " && ".join(
            shlex.join(argv)
            for argv in (
                CONFIGURE,
                ["cmake", "--build", "/build", "--parallel", "2"],
                CTEST,
            )
        )
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
            "--ulimit=core=0:0",
            "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777",
            "--tmpfs=/build:rw,exec,nosuid,nodev,size=1024m,uid=65534,gid=65534,mode=0700",
            "--mount",
            f"type=bind,source={source},target=/src,readonly",
            "--workdir=/build",
            IMAGE,
            "/bin/bash",
            "-ec",
            command,
        ]
        execution["argv"] = argv
        try:
            result = run_logged_process(
                argv,
                root=output,
                budget=AuditBudget(output),
                timeout=900,
                on_stop=lambda _: subprocess.run(
                    ["docker", "rm", "-f", name], capture_output=True, timeout=30
                ),
            )
            execution.update(exit_code=result.returncode, command=result.to_dict())
            for stream in ("stdout", "stderr"):
                reference = getattr(result, stream + "_log")
                (output / (stream + ".log")).write_bytes(
                    reference.read(output, limit=4 * 1024 * 1024) if reference else b""
                )
        finally:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=30)
            remaining = subprocess.check_output(
                ["docker", "ps", "-a", "--filter", f"name=^/{name}$", "--format", "{{.ID}}"],
                timeout=30,
            )
            execution["container_deleted"] = not remaining.strip()
            execution["duration_seconds"] = time.monotonic() - started
            save(output / "execution.json", execution)
    sys.path.insert(0, str(evaluator))
    from multi_swe_bench.harness.repos.cpp.fmtlib.fmt import Fmt

    observed = Fmt.parse_log(None, (output / "stdout.log").read_text())
    required = set(native_tests(record))
    missing = sorted(required - observed.passed_tests)
    accepted = (
        result.ok
        and execution["container_deleted"]
        and not missing
        and not observed.failed_tests
        and not observed.skipped_tests
        and observed.passed_tests == required
    )
    verdict = {
        "accepted": accepted,
        "reason": "NATIVE_SUITE_PASSED" if accepted else "NATIVE_BUILD_OR_TEST_FAILED",
        "required_tests": sorted(required),
        "passed_tests": sorted(observed.passed_tests),
        "failed_tests": sorted(observed.failed_tests),
        "missing_tests": missing,
        "native_tests_executed": bool(observed.passed_tests or observed.failed_tests),
        "reference_check": args.reference_check,
        "model_requests": 0,
    }
    save(output / "oracle-verdict.json", verdict)
    print(json.dumps(verdict))
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
