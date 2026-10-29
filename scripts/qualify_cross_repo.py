"""固定跨仓库 C++ 实例，验证基线、源码范围与独立冷 Oracle。"""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml
from cpp_native_adapter import (
    PRODUCTION_AREAS,
    editable_files,
    group_states,
    initialize_snapshot_git,
    make_contract,
    materialize,
    prepare_source_dependencies,
    recipe,
    source_manifest,
    text_readable_paths,
    wrapper,
)
from cpp_sources import MULTISWE_REVISION, load_records, production_reference
from qualify_cpp_batch import CANCELLED, CTEST, Executor, archive, git, save, sha

from repropatch.errors import ReproPatchError
from repropatch.task import IMAGE_ID, Task

ROOT = Path(__file__).resolve().parents[1]


class NativeExecutor(Executor):
    def __init__(self, backend, image, directory, deadline, configuration):
        super().__init__(backend, image, directory, deadline, 2)
        self.configuration = configuration
        self.memory_mib = configuration["memory_mib"]
        self.pids_limit = configuration.get("pids_limit", 256)
        self.tmp_executable = configuration.get("tmp_executable", False)
        self.configure = [*configuration["configure"], "-DREPROPATCH_NATIVE_WRAPPER=ON"]
        self.phase_timeout = configuration.get("phase_timeout_seconds", 1800)

    def suite(self, source, phase, required, selected=None):
        previous = self.deadline
        self.deadline = min(previous, time.monotonic() + self.phase_timeout)
        try:
            result = super().suite(source, phase, required, selected)
            xml = self.directory / (phase + "-results.xml")
            log = self.directory / "logs" / (phase + "-ctest.log")
            diagnostic = "\n".join(
                path.read_text(errors="replace") for path in (xml, log) if path.is_file()
            )
            if any(
                marker in diagnostic
                for marker in (
                    "REPROPATCH_NATIVE_NOT_EXECUTED",
                    "NATIVE_PROCESS_INFRASTRUCTURE_ERROR",
                    "NATIVE_FILESYSTEM_INFRASTRUCTURE_ERROR",
                    "NATIVE_JUNIT_MISSING",
                    "NATIVE_CTEST_NOT_EXECUTED",
                    "NATIVE_CTEST_IDENTITY_MISSING",
                    "NATIVE_CMAKE_FILE_API_MISSING",
                    "NATIVE_CTEST_COMMAND_AMBIGUOUS",
                )
            ):
                result["status"] = "TEST_INFRASTRUCTURE_FAILED"
            return result
        finally:
            self.deadline = previous

    def native_oracle(self, source, phase, contract, *, configuration=None, selected=None):
        """原始 CMake 工程使用全新构建树，编译缓存始终关闭。"""
        previous = self.deadline
        self.deadline = min(previous, time.monotonic() + self.phase_timeout)
        build = self.build_root / phase
        configuration = configuration or self.configuration
        configure = [
            *configuration["configure"],
            "-DCMAKE_CXX_COMPILER_LAUNCHER=",
            "-DCMAKE_C_COMPILER_LAUNCHER=",
        ]
        try:
            configured = self.run(configure, source, build, phase, "configure")
            if configured["exit_code"]:
                return {"status": "CONFIGURE_FAILED", "tests": {}}
            command = ["cmake", "--build", "/build", "--parallel", "2"]
            if selected:
                command += ["--target", *selected]
            built = self.run(command, source, build, phase, "build")
            if built["exit_code"]:
                return {"status": "BUILD_FAILED", "tests": {}}
            if selected:
                tested = self.run(
                    [
                        *CTEST,
                        "-R",
                        "^(" + "|".join(re.escape(name) for name in selected) + ")$",
                        "--output-junit",
                        "/build/selected.xml",
                    ],
                    source,
                    build,
                    phase,
                    "ctest",
                )
                from native_cpp_runner import ctest_results

                if tested["exit_code"] not in {0, 8} or not (build / "selected.xml").exists():
                    return {"status": "TEST_EXECUTION_FAILED", "tests": {}}
                observed = ctest_results((build / "selected.xml").read_text(), "ctest")
                states = {
                    name: "passed" if value == "pass" else "failed"
                    for name, value in observed.items()
                }
                save(self.directory / (phase + "-native-results.json"), {"tests": states})
                return {
                    "status": "PASSED"
                    if tested["exit_code"] == 0
                    and set(states) == set(selected)
                    and set(states.values()) == {"passed"}
                    else "TESTS_FAILED",
                    "tests": states,
                }
            tested = self.run(
                [
                    "python3",
                    "-I",
                    "/src/repropatch-native/runner.py",
                    "--source",
                    "/src",
                    "--build",
                    "/build",
                    "--contract",
                    "/src/repropatch-native/contract.json",
                    "--oracle",
                ],
                source,
                build,
                phase,
                "ctest",
            )
            result_file = build / "native-results.json"
            if not result_file.exists():
                return {"status": "TEST_EXECUTION_FAILED", "tests": {}}
            native = json.loads(result_file.read_text())
            save(self.directory / (phase + "-native-results.json"), native)
            if native["missing"]:
                return {"status": "TEST_RESULT_IDENTITY_MISMATCH", **native}
            if native["additional_failures"]:
                return {"status": "TESTS_FAILED", **native}
            if tested["exit_code"] not in {0, 1}:
                return {"status": "TEST_EXECUTION_FAILED", **native}
            states = group_states(contract, native["tests"])
            return {
                "status": "PASSED"
                if tested["exit_code"] == 0 and set(states.values()) == {"passed"}
                else "TESTS_FAILED",
                "tests": states,
                "native_tests": native["tests"],
            }
        finally:
            self.deadline = previous


def write_task(record, source, directory, image, configuration, f2p, p2p):
    repo = record["org"] + "/" + record["repo"]
    editable = editable_files(record, source)
    protected = [
        "test/",
        "tests/",
        "testsuite/",
        "cmake/",
        "external/",
        "extern/",
        "dependencies/",
        "repropatch-native/",
        "CMakeLists.txt",
    ]
    protected = [name for name in protected if (source / name).exists()]
    description = "\n\n".join(
        (issue.get("title") or "") + "\n" + (issue.get("body") or "")
        for issue in record["resolved_issues"]
    ).strip()
    encoded_description = description.encode("utf-8")
    if len(encoded_description) > 30 * 1024:
        # 保留问题开头与日志结尾，完整原文随 control/record.json 归档。
        description = (
            encoded_description[: 26 * 1024].decode("utf-8", errors="ignore")
            + "\n\n[中间日志已折叠；完整问题原文见资格证据 control/record.json]\n\n"
            + encoded_description[-3 * 1024 :].decode("utf-8", errors="ignore")
        )
    raw = {
        "version": 2,
        "id": record["instance_id"].replace("__", "-").lower(),
        "repository": {
            "path": str(source),
            "commit": git(source, "rev-parse", "HEAD").decode().strip(),
        },
        "environment": {
            "image": image,
            "cpu_limit": 2.0,
            "memory_mib": configuration["memory_mib"],
            "build_tmpfs_mib": configuration["build_tmpfs_mib"],
            "pids_limit": configuration.get("pids_limit", 256),
            "tmp_executable": configuration.get("tmp_executable", False),
        },
        "bug": {
            "description": description
            + "\n\nSource /src; build /build. Protected CTest nodes execute "
            "the upstream native tests. Use reproduce for focused F2P feedback."
        },
        "commands": {
            "configure": [*configuration["configure"], "-DREPROPATCH_NATIVE_WRAPPER=ON"],
            "build": ["cmake", "--build", "/build", "--parallel", "2"],
            "reproduce": list(CTEST),
            "verify": list(CTEST),
        },
        "tests": {
            "fail_to_pass": [
                {
                    "name": name,
                    "expected_exit_code": 8,
                    "output_contains": "REPROPATCH_NATIVE_REGRESSION_FAILED",
                }
                for name in f2p
            ],
            "pass_to_pass": p2p,
            "protected_paths": protected,
        },
        "files": {
            "editable": editable,
            "readable": text_readable_paths(
                source,
                sorted(
                    {
                        name
                        for name in [*PRODUCTION_AREAS[repo], *protected]
                        if (source / name).exists()
                    }
                ),
            ),
        },
        "budget": {
            "max_steps": 24,
            "max_tool_calls": 48,
            "wall_seconds": 7200,
            "verification_reserve_seconds": 1200,
            "model_timeout_seconds": 180,
            "command_timeout_seconds": 1800,
            "max_output_tokens": 8192,
        },
        "workspace": {"root": str(directory / "workspaces")},
        "outputs": {"root": str(directory / "runs")},
    }
    path = directory / "task.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=True))
    Task.load(path)
    return path


def manifest(directory):
    save(
        directory / "manifest.json",
        {
            path.relative_to(directory).as_posix(): {
                "size": path.stat().st_size,
                "sha256": sha(path),
            }
            for path in sorted(directory.rglob("*"))
            if path.is_file()
            and not path.is_symlink()
            and ".git" not in path.parts
            and path != directory / "manifest.json"
        },
    )


def qualify(record, args):
    directory = args.output.resolve() / record["instance_id"]
    directory.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = {
        "schema_version": 2,
        "adapter": "native-cpp-v1",
        "qualification_policy": "baseline-native-v1",
        "model_requests": 0,
        "attempt_id": uuid.uuid4().hex,
        "batch_id": os.environ.get("REPROPATCH_BATCH_ID", args.output.name),
        "started_at": datetime.now(UTC).isoformat(),
        "instance_id": record["instance_id"],
        "dataset": record.get("dataset", "ByteDance-Seed/Multi-SWE-bench"),
        "dataset_revision": record.get("dataset_revision", MULTISWE_REVISION),
        "backend": args.backend,
        "status": "PREPARING",
        "optimization": "O3",
        "image_id": args.image,
        "upstream_commit": record["base"]["sha"],
        "phases": {},
    }
    executor = None
    source = directory / "repository"
    save(directory / "result.json", result)
    try:
        reference, omitted = production_reference(record)
        configuration = recipe(record, cxx=args.cxx, cc=args.cc)
        task_timeout = (
            args.task_timeout
            if args.task_timeout is not None
            else configuration.get("qualification_timeout_seconds", 5400)
        )
        if task_timeout <= 0:
            raise ValueError("QUALIFICATION_TIMEOUT_MUST_BE_POSITIVE")
        result["qualification_timeout_seconds"] = task_timeout
        executor = NativeExecutor(
            args.backend, args.image, directory, started + task_timeout, configuration
        )
        control = directory / "control"
        control.mkdir()
        save(control / "record.json", record)
        (control / "reference.patch").write_text(reference)
        (control / "reference-full.patch").write_text(record["fix_patch"])
        (control / "test.patch").write_text(record["test_patch"])
        result["dependencies"] = materialize(
            configuration["repository"],
            record["base"]["sha"],
            source,
            args.repository,
            deadline=executor.deadline,
        )
        result["dependencies"].extend(
            prepare_source_dependencies(record, source, args.repository, deadline=executor.deadline)
        )
        git(source, "init", "--template=", "-q", ".", deadline=executor.deadline)
        git(source, "add", "-f", ".", deadline=executor.deadline)
        git(source, "commit", "-qm", "固定上游源码与离线依赖", deadline=executor.deadline)
        result["upstream_snapshot_commit"] = (
            git(source, "rev-parse", "HEAD", deadline=executor.deadline).decode().strip()
        )
        save(control / "upstream-source-manifest.json", source_manifest(source))
        git(source, "apply", str(control / "test.patch"), deadline=executor.deadline)
        contract = make_contract(record, configuration)
        wrapper(source, contract)
        save(control / "editable-files.json", editable_files(record, source))
        save(control / "prepared-source-manifest.json", source_manifest(source))
        required = sorted(contract["groups"])
        result.update(
            configuration=configuration,
            configure=executor.configure,
            required_tests=required,
            required_native_tests=contract["required_native_tests"],
            native_test_count=len(contract["required_native_tests"]),
            reference_patch_sha256=sha(control / "reference.patch"),
            reference_full_patch_sha256=sha(control / "reference-full.patch"),
            omitted_reference_paths=omitted,
            test_patch_sha256=sha(control / "test.patch"),
            native_contract_sha256=sha(source / "repropatch-native/contract.json"),
        )
        baseline = executor.suite(source, "baseline", required)
        result["phases"]["baseline"] = baseline
        executor.release_build("baseline")
        f2p = sorted(name for name, state in baseline["tests"].items() if state == "failed")
        p2p = sorted(name for name, state in baseline["tests"].items() if state == "passed")
        if (
            baseline["status"] != "TESTS_FAILED"
            or not f2p
            or not p2p
            or set(f2p + p2p) != set(required)
        ):
            result["status"] = "BASELINE_" + baseline["status"]
            return result
        declared = (
            sorted(name for name in contract["groups"] if name != "native-p2p")
            if contract["mode"] != "ctest"
            else contract["declared_native_f2p"]
        )
        if declared and f2p != declared:
            result.update(status="DECLARED_F2P_MISMATCH", observed_f2p=f2p, declared_f2p=declared)
            return result
        result.update(f2p=f2p, p2p=p2p)
        git(source, "add", "-f", ".", deadline=executor.deadline)
        git(source, "commit", "-qm", "固定官方回归与原生测试合同", deadline=executor.deadline)
        result["prepared_commit"] = (
            git(source, "rev-parse", "HEAD", deadline=executor.deadline).decode().strip()
        )
        native = control / "native-source"
        archive(source, result["upstream_snapshot_commit"], native, deadline=executor.deadline)
        initialize_snapshot_git(
            native, source, result["upstream_snapshot_commit"], deadline=executor.deadline
        )
        git(native, "apply", str(control / "test.patch"), deadline=executor.deadline)
        git(native, "apply", str(control / "reference.patch"), deadline=executor.deadline)
        shutil.copytree(
            source / "repropatch-native", native / "repropatch-native", dirs_exist_ok=True
        )
        result["phases"]["native_oracle"] = executor.native_oracle(
            native, "native-oracle", contract
        )
        executor.release_build("native-oracle")
        if result["phases"]["native_oracle"]["status"] != "PASSED":
            result["status"] = "NATIVE_ORACLE_" + result["phases"]["native_oracle"]["status"]
            return result
        result["native_oracle"] = {
            "adapter_used": False,
            "cold_build": True,
            "passed": True,
            "native_test_count": result["native_test_count"],
        }
        if configuration["repository"] == "nlohmann/json":
            single = {
                **configuration,
                "configure": [
                    arg.replace("-DJSON_MultipleHeaders=ON", "-DJSON_MultipleHeaders=OFF")
                    for arg in configuration["configure"]
                ],
            }
            single_result = executor.native_oracle(
                native, "single-header", contract, configuration=single, selected=f2p
            )
            result["phases"]["single_header"] = single_result
            executor.release_build("single-header")
            if single_result["status"] != "PASSED":
                result["status"] = "SINGLE_HEADER_" + single_result["status"]
                return result
        git(
            source,
            "bundle",
            "create",
            str(directory / "prepared.bundle"),
            "HEAD",
            deadline=executor.deadline,
        )
        result["prepared_bundle_sha256"] = sha(directory / "prepared.bundle")
        if args.backend == "docker":
            task = write_task(record, source, directory, args.image, configuration, f2p, p2p)
            result.update(task_path=str(task), task_file_sha256=sha(task))
        result["status"] = "QUALIFIED" if args.backend == "docker" else "HOST_QUALIFIED"
        return result
    except (KeyboardInterrupt, InterruptedError):
        result["status"] = "CANCELLED"
        return result
    except TimeoutError as error:
        result.update(
            status="CANCELLED" if CANCELLED.is_set() else "TIMED_OUT", diagnostic=str(error)
        )
        return result
    except (
        ValueError,
        OSError,
        subprocess.SubprocessError,
        RuntimeError,
        ReproPatchError,
    ) as error:
        result.update(
            status="CANCELLED" if CANCELLED.is_set() else "PREPARATION_FAILED",
            failure_type=type(error).__name__,
            diagnostic=str(error)[-2000:],
        )
        return result
    finally:
        result.update(
            wall_seconds=time.monotonic() - started,
            finished_at=datetime.now(UTC).isoformat(),
            commands=executor.commands if executor else [],
            phase_build_bytes=executor.phase_build_bytes if executor else {},
        )
        errors = []
        for path in [
            directory / "control/native-source",
            *([executor.build_root] if executor else []),
        ]:
            if path.exists():
                try:
                    shutil.rmtree(path)
                except OSError as error:
                    errors.append(type(error).__name__)
        result["cleanup"] = {"status": "FAILED" if errors else "SUCCEEDED", "errors": errors}
        if errors:
            result.update(status_before_cleanup=result["status"], status="CLEANUP_FAILED")
        save(directory / "commands.json", result["commands"])
        save(directory / "result.json", result)
        manifest(directory)


def positive_seconds(value):
    seconds = int(value)
    if seconds <= 0:
        raise argparse.ArgumentTypeError("资格期限必须是正整数秒")
    return seconds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--instances", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend", choices=("docker", "native"), default="docker")
    parser.add_argument("--image")
    parser.add_argument("--cxx", default="clang++-19")
    parser.add_argument("--cc", default="clang-19")
    parser.add_argument("--task-timeout", type=positive_seconds, default=None)
    args = parser.parse_args()
    if args.backend == "docker" and not IMAGE_ID.fullmatch(args.image or ""):
        parser.error("Docker 资格使用固定 image ID")
    if args.output.exists():
        parser.error("每个资格批次使用独立目录")
    selected = args.instances.split(",")
    rows = {record["instance_id"]: record for record in load_records(args.dataset)}
    if len(set(selected)) != len(selected) or set(selected) - rows.keys():
        parser.error("候选实例缺失或重复")
    args.output.mkdir(parents=True)
    execution = {}
    for relative in (
        "scripts/qualify_cross_repo.py",
        "scripts/cpp_native_adapter.py",
        "scripts/native_cpp_runner.py",
        "scripts/native_cpp_runtime.cmake",
        "scripts/cpp_sources.py",
        "scripts/qualify_cpp_batch.py",
        "scripts/prepare_multiswe_task.py",
        "scripts/prepare_simdjson_task.py",
        "scripts/prepare_json_task.py",
        "scripts/check_json_candidate.py",
        "scripts/prepare_fmt_task.py",
        "scripts/screen_multiswe.py",
        "src/repropatch/task.py",
    ):
        path = ROOT / relative
        target = args.output / "execution-source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        execution[relative] = {"size": path.stat().st_size, "sha256": sha(path)}
    save(args.output / "source-manifest.json", execution)
    environment = {
        "backend": args.backend,
        "image_id": args.image,
        "python_unbuffered": True,
        "log_stream_policy": "ctest-stream-pairing-v1",
    }
    if args.backend == "docker":
        identity = subprocess.check_output(
            ["docker", "image", "inspect", "--format", "{{.Id}}", args.image], text=True
        ).strip()
        if identity != args.image:
            parser.error("DOCKER_IMAGE_ID_MISMATCH")
    else:
        for tool in (args.cxx, args.cc, "cmake", "ninja"):
            executable = Path(shutil.which(tool)).resolve()
            environment[tool] = {
                "sha256": sha(executable),
                "path": str(executable),
                "version": subprocess.check_output([tool, "--version"], text=True).splitlines()[0],
            }
    save(args.output / "environment.json", environment)
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: CANCELLED.set())
    results = []
    for instance in selected:
        result = qualify(rows[instance], args)
        results.append(result)
        save(
            args.output / "batch-summary.json",
            {"schema_version": 2, "model_requests": 0, "tasks": results},
        )
        print(
            json.dumps(
                {
                    "instance_id": instance,
                    "status": result["status"],
                    "wall_seconds": result["wall_seconds"],
                }
            ),
            flush=True,
        )
    return 0 if all(row["status"] in {"QUALIFIED", "HOST_QUALIFIED"} for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
