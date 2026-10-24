"""Score an in-scope candidate against a qualified fmt task's cold original suite.

The same entry point accepts candidates from ReproPatch, mini-SWE-agent and
Codex. It never loads the reference patch into the candidate source tree.
Arbitrary candidates require Docker; native controls accept only the exact reference.
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET
from functools import partial
from pathlib import Path

from qualify_cpp_batch import (
    CANCELLED,
    FORMAT,
    Executor,
    archive,
    git,
    records,
    save,
    sha,
    validate_record,
)

from repropatch.task import IMAGE_ID


class CandidateRejected(ValueError):
    pass


def candidate_paths(source, patch_file, deadline=None):
    """Use Git's complete patch parser, including plain unified diff sections."""
    try:
        records = git(source, "apply", "--numstat", "-z", str(patch_file), deadline=deadline).split(
            b"\0"
        )
        summary = git(source, "apply", "--summary", str(patch_file), deadline=deadline)
    except subprocess.CalledProcessError as error:
        raise CandidateRejected("INVALID_CANDIDATE_PATCH") from error
    if not records or records.pop() != b"" or not records:
        raise CandidateRejected("INVALID_CANDIDATE_PATCH")
    if summary:
        raise CandidateRejected("CANDIDATE_SCOPE_REJECTED")
    paths = []
    for record in records:
        parts = record.split(b"\t", 2)
        if len(parts) != 3 or not all(number.isdigit() for number in parts[:2]):
            raise CandidateRejected("CANDIDATE_SCOPE_REJECTED")
        try:
            name = parts[2].decode("utf-8")
        except UnicodeError as error:
            raise CandidateRejected("INVALID_CANDIDATE_PATCH") from error
        path = Path(name)
        if (
            not name.startswith(("include/", "src/", "fmt/"))
            or path.suffix not in {".h", ".hpp", ".cc", ".cpp"}
            or ".." in path.parts
            or not (source / path).is_file()
            or (source / path).is_symlink()
        ):
            raise CandidateRejected("CANDIDATE_SCOPE_REJECTED")
        paths.append(name)
    return sorted(set(paths))


def check(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    result = {
        **FORMAT,
        "accepted": False,
        "status": "PREPARING",
        "adapter_used": False,
        "cold_build": True,
        "compiler_cache": "disabled",
    }
    started = time.monotonic()
    deadline = started + args.timeout
    run_git = partial(git, deadline=deadline)
    runner, source = None, output / "native-source"
    try:
        if CANCELLED.is_set():
            raise InterruptedError("TASK_CANCELLED")
        result["qualification_sha256"] = sha(args.qualification)
        if not args.candidate.is_file():
            result["status"] = "MISSING_CANDIDATE"
            return result
        if args.candidate.stat().st_size > 8 * 1024 * 1024:
            raise CandidateRejected("CANDIDATE_TOO_LARGE")
        result["candidate_sha256"] = sha(args.candidate)
        qualification = json.loads(args.qualification.read_text())
        if qualification.get("backend") not in {"native", "docker"}:
            raise ValueError("UNSUPPORTED_QUALIFICATION_BACKEND")
        if qualification.get("dataset_revision") != FORMAT["dataset_revision"]:
            raise ValueError("QUALIFICATION_DATASET_MISMATCH")
        if qualification["status"] not in {"QUALIFIED", "HOST_QUALIFIED"}:
            raise ValueError("TASK_NOT_QUALIFIED")
        if (qualification["status"] == "QUALIFIED") != (qualification["backend"] == "docker"):
            raise ValueError("QUALIFICATION_BACKEND_MISMATCH")
        if qualification["backend"] == "docker" and not IMAGE_ID.fullmatch(
            str(qualification.get("image_id", ""))
        ):
            raise ValueError("IMMUTABLE_DOCKER_IMAGE_REQUIRED")
        record = next(
            r for r in records(args.dataset) if r["instance_id"] == qualification["instance_id"]
        )
        _, required = validate_record(record)
        control = args.qualification.parent / "control"
        if (
            record["base"]["sha"] != qualification["upstream_commit"]
            or required != qualification["required_tests"]
            or sha(control / "test.patch") != qualification["test_patch_sha256"]
            or (control / "test.patch").read_text() != record["test_patch"]
            or qualification.get("optimization") not in {"O0", "O1", "O2", "O3"}
            or not qualification["f2p"]
            or not qualification["p2p"]
            or set(qualification["f2p"]) & set(qualification["p2p"])
            or set(qualification["f2p"] + qualification["p2p"]) != set(required)
        ):
            raise ValueError("QUALIFICATION_IDENTITY_MISMATCH")
        result.update(
            instance_id=record["instance_id"],
            backend=qualification["backend"],
            optimization=qualification["optimization"],
            image_id=qualification["image_id"],
            upstream_commit=record["base"]["sha"],
            prepared_commit=qualification["prepared_commit"],
        )
        patch = args.candidate.read_bytes()
        if len(patch) > 8 * 1024 * 1024:
            raise CandidateRejected("CANDIDATE_TOO_LARGE")
        (output / "candidate.patch").write_bytes(patch)
        result["candidate_sha256"] = sha(output / "candidate.patch")
        if not patch.strip():
            result["status"] = "EMPTY_CANDIDATE"
            return result
        if qualification["backend"] == "native" and (
            result["candidate_sha256"] != qualification["reference_patch_sha256"]
            or patch != record["fix_patch"].encode()
        ):
            result["status"] = "NATIVE_CANDIDATE_REQUIRES_DOCKER"
            return result
        prepared = args.qualification.parent / "repository"
        if (
            run_git(prepared, "rev-parse", "HEAD").decode().strip()
            != qualification["prepared_commit"]
        ):
            raise ValueError("PREPARED_COMMIT_MISMATCH")
        run_git(prepared, "diff", "--quiet", "HEAD", "--")
        if qualification["backend"] == "docker":
            if sha(args.qualification.parent / "task.yaml") != qualification["task_file_sha256"]:
                raise ValueError("TASK_FILE_CHANGED")
        if qualification["backend"] == "native":
            environment = json.loads(
                (args.qualification.parent.parent / "environment.json").read_text()
            )
            for tool in ("c++", "cmake", "ninja"):
                executable = shutil.which(tool)
                if not executable or sha(Path(executable).resolve()) != environment[tool]["sha256"]:
                    raise ValueError("HOST_TOOLCHAIN_CHANGED")
        archive(args.repository, record["base"]["sha"], source, deadline=deadline)
        run_git(source, "init", "--template=", "-q", ".")
        run_git(source, "apply", str(control / "test.patch"))
        # The allowlist covers all production C++ files, not reference-diff paths.
        paths = candidate_paths(source, output / "candidate.patch", deadline=deadline)
        run_git(source, "add", "-f", ".")
        try:
            run_git(source, "apply", "--check", str(output / "candidate.patch"))
            run_git(source, "apply", str(output / "candidate.patch"))
        except subprocess.CalledProcessError:
            result["status"] = "INVALID_CANDIDATE_PATCH"
            return result
        actual = run_git(source, "diff", "--name-only", "-z", "--").split(b"\0")
        if actual[-1] != b"" or sorted(p.decode("utf-8") for p in actual[:-1]) != paths:
            raise CandidateRejected("CANDIDATE_SCOPE_REJECTED")
        if run_git(source, "diff", "--summary", "--"):
            raise CandidateRejected("CANDIDATE_SCOPE_REJECTED")
        result["input_preparation_wall_seconds"] = time.monotonic() - started
        runner = Executor(
            qualification["backend"],
            qualification["image_id"],
            output,
            deadline,
            args.build_jobs,
            qualification["optimization"],
        )
        if runner.configure != qualification["configure"]:
            raise ValueError("BUILD_CONFIGURATION_CHANGED")
        # Disable launchers even if the host has CMAKE_CXX_COMPILER_LAUNCHER set.
        runner.configure += ["-DCMAKE_CXX_COMPILER_LAUNCHER=", "-DCMAKE_C_COMPILER_LAUNCHER="]
        result["configure"] = runner.configure
        oracle = runner.suite(source, "native-oracle", required)
        result["oracle"] = oracle
        result["changed_files"] = paths
        result["accepted"] = oracle["status"] == "PASSED"
        result["status"] = "ORACLE_PASSED" if result["accepted"] else "ORACLE_" + oracle["status"]
        result["f2p"] = {
            name: oracle["tests"].get(name, "not_run") for name in qualification["f2p"]
        }
        result["p2p"] = {
            name: oracle["tests"].get(name, "not_run") for name in qualification["p2p"]
        }
        return result
    except CandidateRejected as error:
        result.update(status=str(error), accepted=False)
        return result
    except InterruptedError as error:
        result.update(status="CANCELLED", accepted=False, diagnostic=str(error))
        return result
    except TimeoutError as error:
        status = (
            "CANCELLED"
            if CANCELLED.is_set() or str(error) == "TASK_CANCELLED"
            else "OUTPUT_LIMIT_EXCEEDED"
            if str(error) == "OUTPUT_LIMIT"
            else "TIMED_OUT"
        )
        result.update(status=status, accepted=False, diagnostic=str(error))
        return result
    except (
        ValueError,
        KeyError,
        TypeError,
        OSError,
        RuntimeError,
        StopIteration,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        ET.ParseError,
    ) as error:
        result.update(status="INFRASTRUCTURE_FAILED", accepted=False, diagnostic=str(error)[-2000:])
        return result
    finally:
        if runner is not None:
            result["commands"] = runner.commands
        cleanup_errors = []
        for path in ([runner.build_root] if runner is not None else []) + [source]:
            if path.exists():
                try:
                    shutil.rmtree(path)
                except OSError as error:
                    cleanup_errors.append(f"{path}: {error}")
        result["cleanup"] = {
            "status": "FAILED" if cleanup_errors else "SUCCEEDED",
            "errors": cleanup_errors,
        }
        if cleanup_errors and result["accepted"]:
            result.update(
                status="CLEANUP_FAILED", accepted=False, oracle_passed_before_cleanup=True
            )
        result["wall_seconds"] = time.monotonic() - started
        save(output / "oracle-verdict.json", result)
        try:
            save(
                output / "manifest.json",
                {
                    str(p.relative_to(output)): {"sha256": sha(p), "size": p.stat().st_size}
                    for p in output.rglob("*")
                    if p.is_file() and source not in p.parents
                },
            )
        except OSError as error:
            result.update(status="ARCHIVE_FAILED", accepted=False, diagnostic=str(error)[-2000:])
            save(output / "oracle-verdict.json", result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qualification", type=Path, required=True, help="Per-task result.json")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--repository", type=Path, required=True, help="Shared upstream fmt object pool"
    )
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--build-jobs", type=int, choices=range(1, 5), default=2)
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("--timeout must be positive")
    os.environ.setdefault("REPROPATCH_BATCH_ID", "local-" + uuid.uuid4().hex)
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: CANCELLED.set())
    result = check(args)
    print(json.dumps(result))
    return 0 if result["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
