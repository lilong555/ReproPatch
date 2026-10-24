"""Qualify fixed Multi-SWE-bench fmt records without making model requests.

The prepared CTest adapter builds only test-patch targets inside their CTest
nodes. A separate cold, unmodified native build checks the reference patch.
Host results are explicitly distinct from isolated Docker qualification.
"""

import argparse
import concurrent.futures
import hashlib
import io
import json
import os
import re
import resource
import shutil
import signal
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import yaml
from prepare_multiswe_task import git as prepare_git
from screen_multiswe import patch_paths

from repropatch.task import IMAGE_ID, Task

ROOT = Path(__file__).resolve().parents[1]
REVISION = "56ff018c04a38e27ada1e9d0a6d5839a51f88f0d"
DATASET_URL = (
    f"https://huggingface.co/datasets/ByteDance-Seed/Multi-SWE-bench/resolve/{REVISION}/cpp"
)
FORMAT = {
    "schema_version": 1,
    "dataset": "ByteDance-Seed/Multi-SWE-bench",
    "dataset_revision": REVISION,
    "model_requests": 0,
}
CONFIGURE = [
    "cmake",
    "-S",
    "/src",
    "-B",
    "/build",
    "-G",
    "Ninja",
    "-DFMT_DOC=OFF",
    "-DFMT_TEST=ON",
    "-DCMAKE_BUILD_TYPE=Release",
    "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
]
CTEST = ["ctest", "--test-dir", "/build", "--output-on-failure", "--no-tests=error"]
CANCELLED = threading.Event()
ADAPTER = """  if (__CONDITION__)
    set_target_properties(${name} PROPERTIES EXCLUDE_FROM_ALL TRUE)
    add_test(NAME ${name} COMMAND ${CMAKE_COMMAND}
      "-DBUILD_DIR=${CMAKE_BINARY_DIR}" "-DTARGET=${name}"
      "-DTEST_BINARY=$<TARGET_FILE:${name}>"
      -P "${PROJECT_SOURCE_DIR}/test/repropatch-build-test.cmake")
  else ()
    add_test(NAME ${name} COMMAND ${name})
  endif ()
"""
BUILD_TEST = """execute_process(COMMAND "${CMAKE_COMMAND}" --build "${BUILD_DIR}"
  --target "${TARGET}" --parallel 2 RESULT_VARIABLE build_status)
if (NOT build_status STREQUAL "0")
  message(FATAL_ERROR "REPROPATCH_COMPILE_REGRESSION: ${build_status}")
endif ()
execute_process(COMMAND "${TEST_BINARY}" RESULT_VARIABLE test_status)
if (NOT test_status STREQUAL "0")
  message(FATAL_ERROR "REPROPATCH_RUNTIME_REGRESSION: ${test_status}")
endif ()
"""


def git(repository, *args, deadline=None):
    return prepare_git(
        repository,
        *args,
        deadline=deadline,
        cancelled=CANCELLED.is_set,
    )


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def records(dataset, download=False):
    """Check the complete file against the already frozen public coverage index."""
    if (dataset / "cpp").is_dir():
        dataset = dataset / "cpp"
    identity = json.loads((ROOT / "benchmarks/coverage.json").read_text())
    assert identity["revision"] == REVISION
    entry = next(f for f in identity["source_files"] if f["path"] == "fmtlib__fmt_dataset.jsonl")
    source = dataset / entry["path"]
    if not source.exists() and download:
        dataset.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(DATASET_URL + "/" + entry["path"], timeout=60) as response:
            source.write_bytes(response.read())
        (dataset / "revision.txt").write_text(REVISION + "\n")
    if sha(source) != entry["sha256"]:
        raise ValueError("DATASET_SHA256_MISMATCH")
    return [json.loads(line) for line in source.read_text().splitlines() if line.strip()]


def exposure(instance):
    """Conservative source-level exposure audit; no claim about pretraining."""
    number = instance.rsplit("-", 1)[1]
    expressions = [f"fmtlib__fmt-{number}", f"fmtlib-fmt-{number}", f"fmt-{number}", f"fmt{number}"]
    sources = []
    for path in sorted((ROOT / "benchmarks").glob("*results.json")):
        content = path.read_text()
        if any(re.search(re.escape(token) + r"(?!\d)", content) for token in expressions):
            sources.append(str(path.relative_to(ROOT)))
    return {
        "prior_model_attempts": "RECORDED" if sources else "NO_REPOSITORY_RECORD_FOUND",
        "sources": sources,
        "split": "development" if sources else "holdout_candidate",
        "qualification_exposes_reference_to_preparation_code": True,
        "holdout_frozen": False,
    }


def archive(repository, commit, target, deadline=None):
    target.mkdir(parents=True)
    with tarfile.open(
        fileobj=io.BytesIO(git(repository, "archive", commit, deadline=deadline))
    ) as source:
        source.extractall(target, filter="data")


def validate_record(record):
    fix_paths, special = patch_paths(record["fix_patch"])
    tests, test_special = patch_paths(record["test_patch"])
    if record["org"] != "fmtlib" or record["repo"] != "fmt" or special or test_special:
        raise ValueError("REFERENCE_LAYOUT_REVIEW_REQUIRED")
    if not fix_paths or any(
        not p.startswith(("include/", "src/", "fmt/"))
        or Path(p).suffix not in {".h", ".hpp", ".cc", ".cpp"}
        for p in fix_paths
    ):
        raise ValueError("REFERENCE_SCOPE_REVIEW_REQUIRED")
    if not tests or any(not p.startswith("test/") for p in tests):
        raise ValueError("TEST_PATCH_SCOPE_REVIEW_REQUIRED")
    targets = sorted({Path(p).stem for p in tests if re.fullmatch(r"test/[\w-]+-test\.cc", p)})
    required = sorted(record["fix_patch_result"]["passed_tests"])
    if not targets or not set(targets) <= set(required) or len(required) != len(set(required)):
        raise ValueError("TEST_TARGET_IDENTITY_REVIEW_REQUIRED")
    return targets, required


class Executor:
    def __init__(self, backend, image, directory, deadline, build_jobs, optimization="O3"):
        self.backend, self.image, self.directory = backend, image, directory
        self.deadline, self.build_jobs = deadline, build_jobs
        self.configure = [*CONFIGURE, f"-DCMAKE_CXX_FLAGS_RELEASE=-{optimization} -DNDEBUG"]
        # Use executable local scratch; copy diagnostics to evidence.
        self.build_root = Path(tempfile.mkdtemp(prefix="repropatch-qualify-build-"))
        self.commands = []
        self.phase_build_bytes = {}

    def git(self, repository, *args):
        return git(repository, *args, deadline=self.deadline)

    def release_build(self, phase, keep=False):
        build = self.build_root / phase
        self.phase_build_bytes[phase] = sum(
            p.stat().st_size for p in build.rglob("*") if p.is_file()
        )
        # Inventories, XML and command logs are already in the evidence folder.
        # No phase reads another phase's compiled files.
        if not keep and build.exists():
            shutil.rmtree(build)

    def run(self, argv, source, build, phase, label):
        build.mkdir(parents=True, exist_ok=True)
        logfile = self.directory / "logs" / f"{phase}-{label}.log"
        logfile.parent.mkdir(parents=True, exist_ok=True)
        container = "repropatch-qualify-" + uuid.uuid4().hex[:12]
        if self.backend == "docker":
            build.chmod(0o777)
            # Match an unprivileged Actions host uid so temporary build files
            # remain removable; root hosts use nobody inside the container.
            container_user = f"{os.getuid() or 65534}:{os.getgid() or 65534}"
            command = [
                "docker",
                "run",
                "--rm",
                "--pull=never",
                "--name",
                container,
                "--label",
                "repropatch.batch=" + os.environ.get("REPROPATCH_BATCH_ID", "local"),
                "--network=none",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges:true",
                f"--user={container_user}",
                f"--cpus={self.build_jobs}",
                "--memory=4096m",
                "--memory-swap=4096m",
                "--pids-limit=256",
                "--ulimit=core=0:0",
                "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777",
                "--mount",
                f"type=bind,source={source},target=/src,readonly",
                "--mount",
                f"type=bind,source={build},target=/build",
                "--workdir=/build",
                self.image,
                *argv,
            ]
        else:
            command = [
                arg.replace("/src", str(source)).replace("/build", str(build)) for arg in argv
            ]
        start = time.monotonic()
        if CANCELLED.is_set():
            raise InterruptedError("TASK_CANCELLED")
        if start >= self.deadline:
            raise TimeoutError("TASK_DEADLINE")
        usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
        stopped = None
        process = None
        try:
            with logfile.open("wb") as stream:
                process = subprocess.Popen(
                    command, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True
                )
                while process.poll() is None:
                    if CANCELLED.is_set():
                        stopped = "TASK_CANCELLED"
                    elif time.monotonic() >= self.deadline:
                        stopped = "TASK_DEADLINE"
                    elif logfile.stat().st_size > 32 * 1024 * 1024:
                        stopped = "OUTPUT_LIMIT"
                    if stopped:
                        break
                    time.sleep(0.1)
                if stopped and process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                code = process.wait()
            if logfile.stat().st_size > 32 * 1024 * 1024:
                stopped = "OUTPUT_LIMIT"
        finally:
            if process is not None and process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
            if self.backend == "docker":
                subprocess.run(["docker", "rm", "-f", container], capture_output=True, timeout=30)
                remaining = subprocess.check_output(
                    [
                        "docker",
                        "ps",
                        "-a",
                        "--filter",
                        f"name=^/{container}$",
                        "--format",
                        "{{.ID}}",
                    ],
                    timeout=30,
                )
                if remaining.strip():
                    raise RuntimeError("CONTAINER_CLEANUP_UNCONFIRMED")
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        result = {
            "phase": phase,
            "stage": label,
            "argv": argv,
            "exit_code": code,
            "wall_seconds": time.monotonic() - start,
            "stopped": stopped,
            "log": str(logfile.relative_to(self.directory)),
            "log_sha256": sha(logfile),
            "log_bytes": logfile.stat().st_size,
            "host_children_cpu_seconds": usage.ru_utime
            + usage.ru_stime
            - usage_before.ru_utime
            - usage_before.ru_stime,
            "host_children_maxrss_kib": usage.ru_maxrss,
            "resource_scope": "process-wide child high-water mark; overlapping tasks not additive",
        }
        self.commands.append(result)
        save(self.directory / "commands.json", self.commands)
        if stopped:
            raise TimeoutError(stopped)
        return result

    def suite(self, source, phase, required, selected=None):
        build = self.build_root / phase
        configure_argv = list(self.configure)
        if phase == "native-oracle":
            configure_argv += ["-DCMAKE_CXX_COMPILER_LAUNCHER=", "-DCMAKE_C_COMPILER_LAUNCHER="]
        configure = self.run(configure_argv, source, build, phase, "configure")
        if configure["exit_code"]:
            return {"status": "CONFIGURE_FAILED", "tests": {}}
        discovery = self.run(
            ["ctest", "--test-dir", "/build", "--show-only=json-v1"],
            source,
            build,
            phase,
            "inventory",
        )
        if discovery["exit_code"]:
            return {"status": "INVENTORY_FAILED", "tests": {}}
        inventory = json.loads((self.directory / discovery["log"]).read_text())
        observed = [test["name"] for test in inventory["tests"]]
        save(self.directory / (phase + "-inventory.json"), inventory)
        if set(observed) != set(required) or len(observed) != len(required):
            return {
                "status": "TEST_INVENTORY_MISMATCH",
                "tests": {},
                "expected": required,
                "observed": observed,
            }
        build_command = ["cmake", "--build", "/build", "--parallel", str(self.build_jobs)]
        if selected:
            build_command += ["--target", *selected]
        built = self.run(
            build_command,
            source,
            build,
            phase,
            "build",
        )
        if built["exit_code"]:
            return {"status": "BUILD_FAILED", "tests": {}}
        test_command = [*CTEST, "--output-junit", "/build/results.xml"]
        if selected:
            test_command += ["-R", "^(" + "|".join(re.escape(name) for name in selected) + ")$"]
        tested = self.run(test_command, source, build, phase, "ctest")
        if tested["exit_code"] not in {0, 8} or not (build / "results.xml").exists():
            return {"status": "TEST_EXECUTION_FAILED", "tests": {}}
        xml = ET.parse(build / "results.xml")
        nodes = xml.findall(".//testcase")
        states = {}
        for node in nodes:
            failure = node.find("failure")
            if node.find("skipped") is not None:
                state = "skipped"
            elif node.find("error") is not None or (
                failure is not None
                and failure.get("message", "").upper()
                in {"BAD_COMMAND", "NOT_RUN", "NOT RUN", "TIMEOUT"}
            ):
                state = "infrastructure_error"
            else:
                state = "failed" if failure is not None else "passed"
            states[node.attrib["name"]] = state
        shutil.copy2(build / "results.xml", self.directory / (phase + "-results.xml"))
        expected = selected or required
        if set(states) != set(expected) or len(nodes) != len(expected):
            return {"status": "TEST_RESULT_IDENTITY_MISMATCH", "tests": states}
        if "infrastructure_error" in states.values():
            return {"status": "TEST_INFRASTRUCTURE_FAILED", "tests": states}
        return {
            "status": "PASSED"
            if tested["exit_code"] == 0 and set(states.values()) == {"passed"}
            else "TESTS_FAILED",
            "tests": states,
        }


def write_task(record, source, directory, image, f2p, p2p, configure=CONFIGURE, deadline=None):
    editable = sorted(
        p.relative_to(source).as_posix()
        for area in ("include", "src", "fmt")
        for p in (source / area).rglob("*")
        if p.is_file() and p.suffix in {".h", ".hpp", ".cc", ".cpp"}
    )
    issues = "\n\n".join(
        issue["title"] + "\n" + (issue.get("body") or "") for issue in record["resolved_issues"]
    )
    task = {
        "version": 2,
        "id": record["instance_id"].replace("__", "-"),
        "repository": {
            "path": str(source),
            "commit": git(source, "rev-parse", "HEAD", deadline=deadline).decode().strip(),
        },
        "environment": {
            "image": image,
            "cpu_limit": 2.0,
            "memory_mib": 4096,
            "build_tmpfs_mib": 2048,
            "pids_limit": 256,
        },
        "bug": {
            "description": issues
            + "\n\nThe protected CTest adapter builds and runs each regression target. "
            "Source /src; build /build. Run reproduce for F2P feedback."
        },
        "commands": {
            "configure": configure,
            "build": ["cmake", "--build", "/build", "--parallel", "2"],
            "reproduce": CTEST,
            "verify": CTEST,
        },
        "tests": {
            "fail_to_pass": [
                {
                    "name": n,
                    "expected_exit_code": 8,
                    "output_contains": "The following tests FAILED:",
                }
                for n in f2p
            ],
            "pass_to_pass": p2p,
            "protected_paths": ["test/", "CMakeLists.txt", "support/"],
        },
        "files": {
            "readable": ["include/", "src/", "fmt/", "test/", "CMakeLists.txt"],
            "editable": editable,
        },
        "budget": {
            "max_steps": 12,
            "max_tool_calls": 24,
            "wall_seconds": 2400,
            "verification_reserve_seconds": 1200,
            "model_timeout_seconds": 90,
            "command_timeout_seconds": 600,
            "max_output_tokens": 8192,
        },
        "workspace": {"root": str(directory / "workspaces")},
        "outputs": {"root": str(directory / "runs")},
    }
    # Readable prefixes must exist for the prepared historical layout.
    task["files"]["readable"] = [p for p in task["files"]["readable"] if (source / p).exists()]
    task["tests"]["protected_paths"] = [
        p for p in task["tests"]["protected_paths"] if (source / p).exists()
    ]
    path = directory / "task.yaml"
    path.write_text(yaml.safe_dump(task, sort_keys=False, allow_unicode=True))
    Task.load(path)
    return path


def qualify(record, args):
    directory = args.output.resolve() / record["instance_id"]
    directory.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = {
        **FORMAT,
        "attempt_id": uuid.uuid4().hex,
        "batch_id": os.environ.get("REPROPATCH_BATCH_ID", args.output.name),
        "started_at": datetime.now(UTC).isoformat(),
        "instance_id": record["instance_id"],
        "backend": args.backend,
        "status": "PREPARING",
        "upstream_commit": record["base"]["sha"],
        "image_id": args.image if args.backend == "docker" else None,
        "optimization": args.optimization,
        "exposure": exposure(record["instance_id"]),
        "reference_patch": str(directory / "control/reference.patch"),
        "repository_path": str(directory / "repository"),
        "phases": {},
    }
    executor = Executor(
        args.backend,
        args.image,
        directory,
        started + args.task_timeout,
        args.build_jobs,
        args.optimization,
    )
    result["configure"] = executor.configure
    save(directory / "result.json", result)
    try:
        if CANCELLED.is_set():
            raise InterruptedError("TASK_CANCELLED")
        targets, required = validate_record(record)
        result.update(targets=targets, required_tests=required)
        control = directory / "control"
        control.mkdir()
        (control / "reference.patch").write_text(record["fix_patch"])
        (control / "test.patch").write_text(record["test_patch"])
        save(control / "record.json", record)
        source = directory / "repository"
        archive(args.repository, record["base"]["sha"], source, deadline=executor.deadline)
        executor.git(source, "init", "--template=", "-q", ".")
        executor.git(source, "apply", str(control / "test.patch"))
        native = control / "native-source"
        shutil.copytree(source, native, ignore=shutil.ignore_patterns(".git"))
        cmake = source / "test/CMakeLists.txt"
        needle = "  add_test(NAME ${name} COMMAND ${name})\n"
        original = cmake.read_text()
        if original.count(needle) != 1:
            raise ValueError("FMT_CMAKE_LAYOUT_REVIEW_REQUIRED")
        condition = " OR ".join(f'name STREQUAL "{name}"' for name in targets)
        cmake.write_text(original.replace(needle, ADAPTER.replace("__CONDITION__", condition)))
        (source / "test/repropatch-build-test.cmake").write_text(BUILD_TEST)
        executor.git(source, "add", "-f", ".")
        executor.git(
            source,
            "commit",
            "-qm",
            "Freeze official regression tests and target-build CTest adapter",
        )
        result.update(
            prepared_commit=executor.git(source, "rev-parse", "HEAD").decode().strip(),
            reference_patch_sha256=sha(control / "reference.patch"),
            test_patch_sha256=sha(control / "test.patch"),
        )
        result["preparation_wall_seconds"] = time.monotonic() - started
        baseline = executor.suite(source, "baseline", required)
        result["phases"]["baseline"] = baseline
        executor.release_build("baseline", args.keep_builds)
        failed = sorted(n for n, state in baseline["tests"].items() if state == "failed")
        passed = sorted(n for n, state in baseline["tests"].items() if state == "passed")
        if (
            baseline["status"] != "TESTS_FAILED"
            or not failed
            or not passed
            or not set(failed) <= set(targets)
            or set(failed + passed) != set(required)
        ):
            result["status"] = (
                "BASELINE_" + baseline["status"]
                if baseline["status"] != "PASSED"
                else "BASELINE_NO_FAILURE"
            )
            return result
        result.update(f2p=failed, p2p=passed)
        preparing = time.monotonic()
        fixed = control / "reference-source"
        shutil.copytree(source, fixed, ignore=shutil.ignore_patterns(".git"))
        executor.git(fixed, "init", "--template=", "-q", ".")
        executor.git(fixed, "apply", str(control / "reference.patch"))
        result["reference_source_prepare_wall_seconds"] = time.monotonic() - preparing
        reference = executor.suite(fixed, "reference", required, selected=failed)
        result["phases"]["reference"] = reference
        executor.release_build("reference", args.keep_builds)
        if reference["status"] != "PASSED":
            result["status"] = "REFERENCE_" + reference["status"]
            return result
        preparing = time.monotonic()
        executor.git(native, "init", "--template=", "-q", ".")
        executor.git(native, "apply", str(control / "reference.patch"))
        result["native_source_prepare_wall_seconds"] = time.monotonic() - preparing
        oracle = executor.suite(native, "native-oracle", required)
        result["phases"]["native_oracle"] = oracle
        executor.release_build("native-oracle", args.keep_builds)
        if oracle["status"] != "PASSED":
            result["status"] = "NATIVE_ORACLE_" + oracle["status"]
            return result
        result["status"] = "QUALIFIED" if args.backend == "docker" else "HOST_QUALIFIED"
        result["native_oracle"] = {
            "adapter_used": False,
            "cold_build": True,
            "passed": True,
            "required_tests": required,
        }
        if args.backend == "docker":
            task = write_task(
                record,
                source,
                directory,
                args.image,
                failed,
                passed,
                executor.configure,
                deadline=executor.deadline,
            )
            result.update(task_path=str(task), task_file_sha256=sha(task))
        else:
            result["task_path"] = None
            result["task_export_pending"] = (
                "Repeat qualification with a fixed Docker image; "
                "host result is not isolated Task v2 qualification"
            )
        return result
    except InterruptedError as error:
        result.update(status="CANCELLED", failure_type=type(error).__name__, diagnostic=str(error))
        return result
    except TimeoutError as error:
        result.update(
            status=(
                "CANCELLED"
                if CANCELLED.is_set() or str(error) == "TASK_CANCELLED"
                else "OUTPUT_LIMIT_EXCEEDED"
                if str(error) == "OUTPUT_LIMIT"
                else "TIMED_OUT"
            ),
            failure_type=type(error).__name__,
            diagnostic=str(error),
        )
        return result
    except (
        ValueError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        OSError,
        RuntimeError,
        ET.ParseError,
    ) as error:
        result.update(
            status="CANCELLED" if CANCELLED.is_set() else "PREPARATION_FAILED",
            failure_type=type(error).__name__,
            diagnostic=str(error)[-2000:],
        )
        return result
    finally:
        result["wall_seconds"] = time.monotonic() - started
        result["finished_at"] = datetime.now(UTC).isoformat()
        result["commands"] = executor.commands
        result["phase_build_bytes"] = executor.phase_build_bytes
        result["build_retention"] = "all_phases" if args.keep_builds else "release_after_each_phase"
        result["temporary_build_root"] = str(executor.build_root)
        cleanup_errors = []
        try:
            result["build_bytes_before_cleanup"] = sum(
                p.stat().st_size for p in executor.build_root.rglob("*") if p.is_file()
            )
        except OSError as error:
            result["build_bytes_before_cleanup"] = None
            result["disk_measurement_error"] = str(error)
        temporary_paths = [
            directory / "control/native-source",
            directory / "control/reference-source",
        ]
        if not args.keep_builds:
            temporary_paths.append(executor.build_root)
        for temporary_path in temporary_paths:
            if temporary_path.exists():
                try:
                    shutil.rmtree(temporary_path)
                except OSError as error:
                    cleanup_errors.append(f"{temporary_path}: {error}")
        result["cleanup"] = {
            "status": "FAILED" if cleanup_errors else "SUCCEEDED",
            "errors": cleanup_errors,
            "builds_kept": args.keep_builds,
        }
        if cleanup_errors:
            result["status_before_cleanup"] = result["status"]
            result["status"] = "CLEANUP_FAILED"
        save(directory / "result.json", result)
        try:
            manifest = {
                str(p.relative_to(directory)): {"size": p.stat().st_size, "sha256": sha(p)}
                for p in sorted(directory.rglob("*"))
                if p.is_file()
                and ".git" not in p.parts
                and not any(part.endswith("-build") for part in p.parts)
            }
            save(directory / "manifest.json", manifest)
        except OSError as error:
            result["status_before_archive"] = result["status"]
            result.update(status="ARCHIVE_FAILED", diagnostic=str(error)[-2000:])
            save(directory / "result.json", result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument(
        "--instances",
        default="all",
        help="Comma-separated full instance IDs, or all (41 fmt records)",
    )
    parser.add_argument("--image", help="Local immutable Docker image ID; required for Docker")
    parser.add_argument("--backend", choices=["docker", "native"], default="docker")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jobs", type=int, choices=range(1, 5), default=1)
    parser.add_argument("--build-jobs", type=int, choices=range(1, 5), default=2)
    parser.add_argument("--task-timeout", type=int, default=1800)
    parser.add_argument("--keep-builds", action="store_true")
    parser.add_argument("--optimization", choices=["O0", "O1", "O2", "O3"], default="O3")
    args = parser.parse_args()
    os.environ.setdefault("REPROPATCH_BATCH_ID", "local-" + uuid.uuid4().hex)
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: CANCELLED.set())
    if args.backend == "docker" and (not args.image or not IMAGE_ID.fullmatch(args.image)):
        parser.error("Docker requires --image sha256:<64 hex>; use docker image inspect")
    if args.task_timeout < 1:
        parser.error("--task-timeout must be positive")
    selected = records(args.dataset, args.download)
    if args.instances != "all":
        wanted = args.instances.split(",")
        known = {r["instance_id"] for r in selected}
        if len(wanted) != len(set(wanted)) or set(wanted) - known:
            parser.error("Unknown or repeated instance IDs")
        selected = [r for r in selected if r["instance_id"] in wanted]
    if args.output.exists():
        parser.error("Output must be new; completed attempts are immutable")
    args.output.mkdir(parents=True)
    source_manifest = {}
    for relative in (
        "scripts/qualify_cpp_batch.py",
        "scripts/prepare_multiswe_task.py",
        "scripts/screen_multiswe.py",
        "src/repropatch/task.py",
    ):
        path = ROOT / relative
        target = args.output / "execution-source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        source_manifest[relative] = {"sha256": sha(path), "size": path.stat().st_size}
    save(args.output / "source-manifest.json", source_manifest)
    toolchain = {
        "backend": args.backend,
        "image_id": args.image if args.backend == "docker" else None,
        "host": {
            "system": os.uname().sysname,
            "release": os.uname().release,
            "machine": os.uname().machine,
            "logical_cpus": os.cpu_count(),
        },
    }
    if args.backend == "native":
        for tool in ("c++", "cmake", "ninja"):
            path = Path(shutil.which(tool)).resolve()
            toolchain[tool] = {
                "path": str(path),
                "sha256": sha(path),
                "version": subprocess.check_output(
                    [tool, "--version"], text=True, timeout=30
                ).splitlines()[0],
            }
    else:
        actual = subprocess.check_output(
            ["docker", "image", "inspect", "--format", "{{.Id}}", args.image], text=True, timeout=30
        ).strip()
        if actual != args.image:
            parser.error("DOCKER_IMAGE_ID_MISMATCH")
    save(args.output / "environment.json", toolchain)
    start = time.monotonic()
    summary = {
        **FORMAT,
        "batch_id": os.environ["REPROPATCH_BATCH_ID"],
        "started_at": datetime.now(UTC).isoformat(),
        "backend": args.backend,
        "requested_instances": [r["instance_id"] for r in selected],
        "jobs": args.jobs,
        "build_jobs": args.build_jobs,
        "optimization": args.optimization,
        "task_timeout": args.task_timeout,
        "results": [],
        "qualified_tasks": [],
        "toolchain": toolchain,
        "source_manifest": source_manifest,
    }
    save(args.output / "batch-summary.json", summary)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(qualify, row, args): row["instance_id"] for row in selected}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            summary["results"].append(result)
            summary["results"].sort(key=lambda item: item["instance_id"])
            summary["qualified_tasks"] = [
                r for r in summary["results"] if r["status"] == "QUALIFIED"
            ]
            summary["host_qualified_tasks"] = [
                r for r in summary["results"] if r["status"] == "HOST_QUALIFIED"
            ]
            summary["wall_seconds"] = time.monotonic() - start
            save(args.output / "batch-summary.json", summary)
            print(
                json.dumps(
                    {
                        "instance_id": result["instance_id"],
                        "status": result["status"],
                        "wall_seconds": result["wall_seconds"],
                    }
                ),
                flush=True,
            )
    summary["finished_at"] = datetime.now(UTC).isoformat()
    summary["wall_seconds"] = time.monotonic() - start
    save(args.output / "batch-summary.json", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
