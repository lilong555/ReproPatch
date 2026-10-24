"""One native 4-build fmt-4055 group; compare --workers 1, 2 and 4 sequentially.

Wrap each invocation with benchmark_resources.py. This measures cold target
builds on one host, not full qualification, model repair, or GitHub Job scaling.
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import qualify_cpp_batch as batch

SCRIPTS = Path(__file__).resolve().parent


def percentile(values, fraction):
    values = sorted(values)
    position = (len(values) - 1) * fraction
    low = int(position)
    return values[low] + (values[min(low + 1, len(values) - 1)] - values[low]) * (position - low)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True, help="New directory under /tmp")
    parser.add_argument("--workers", type=int, choices=(1, 2, 4), required=True)
    parser.add_argument("--timeout", type=int, default=900, help="Group deadline (seconds)")
    args = parser.parse_args()
    output, scratch = args.output.resolve(), args.scratch.resolve()
    if args.timeout < 1 or not scratch.is_relative_to(Path("/tmp").resolve()):
        parser.error("positive timeout and a new scratch directory under /tmp required")
    if output.is_relative_to(scratch) or scratch.is_relative_to(output):
        parser.error("output and scratch must be separate trees")
    output.mkdir(parents=True, exist_ok=False)
    scratch.mkdir(parents=True, exist_ok=False)
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: batch.CANCELLED.set())
    os.environ["CCACHE_DISABLE"] = "1"
    started, source = time.monotonic(), scratch / "source"
    deadline = started + args.timeout
    result = {
        **batch.FORMAT,
        "status": "PREPARING",
        "backend": "trusted-native-reference-only",
        "scope": "four cold format-test builds on one host; not GitHub Job or Agent scaling",
        "instance_id": "fmtlib__fmt-4055",
        "target": "format-test",
        "planned_builds": 4,
        "workers": args.workers,
        "build_jobs": 2,
        "generator": "Ninja",
        "optimization": "O3",
        "compiler_cache": "disabled",
        "affinity_cpus": sorted(os.sched_getaffinity(0)),
        "cold_scope": "fresh build trees; compiler cache disabled; host page cache retained",
        "task_latency_scope": "active configure/inventory/build/test/cleanup; excludes queue wait",
        "attempts": [],
    }
    try:
        record = next(
            r for r in batch.records(args.dataset) if r["instance_id"] == result["instance_id"]
        )
        _, required = batch.validate_record(record)
        if len(required) != 20 or "format-test" not in required:
            raise ValueError("EXPECTED_ORIGINAL_20_TEST_INVENTORY")
        control = output / "control"
        control.mkdir()
        names = (
            "profile_cpp_concurrency.py",
            "qualify_cpp_batch.py",
            "benchmark_resources.py",
            "prepare_multiswe_task.py",
            "screen_multiswe.py",
        )
        for name in names:
            shutil.copyfile(SCRIPTS / name, control / name)
        result["implementation_sha256"] = {name: batch.sha(control / name) for name in names}
        result["upstream_commit"], result["required_tests"] = record["base"]["sha"], required
        result["versions"] = {}
        for tool in ("c++", "cmake", "ninja"):
            version = subprocess.check_output([tool, "--version"], text=True, timeout=10)
            result["versions"][tool] = version.splitlines()[0]
        batch.archive(args.repository, result["upstream_commit"], source, deadline=deadline)
        batch.git(source, "init", "--template=", "-q", ".", deadline=deadline)
        for key in ("test_patch", "fix_patch"):
            path = control / (key + ".patch")
            path.write_text(record[key])
            result[key + "_sha256"] = batch.sha(path)
            batch.git(source, "apply", str(path), deadline=deadline)
        for path in [source, *source.rglob("*")]:
            if not path.is_symlink():
                path.chmod(path.stat().st_mode & ~0o222)
        result["setup_seconds"] = time.monotonic() - started

        def build(number):
            began, runner = time.monotonic(), None
            directory = output / f"cold-{number}"
            directory.mkdir()
            row = {"attempt_id": f"workers-{args.workers}-cold-{number}", "status": "RUNNING"}
            row["queue_wait_seconds"] = began - before
            try:
                runner = batch.Executor("native", None, directory, deadline, 2, "O3")
                runner.build_root.rmdir()  # Move this empty, owned tree under the watched root.
                runner.build_root = scratch / f"build-{number}"
                runner.build_root.mkdir()
                row["oracle"] = runner.suite(source, "native-oracle", required, ["format-test"])
                row["status"] = row["oracle"]["status"]
            except Exception as error:
                row.update(
                    status="CANCELLED" if batch.CANCELLED.is_set() else "INFRASTRUCTURE_FAILED",
                    diagnostic=f"{type(error).__name__}: {error}",
                )
            finally:
                if runner is not None:
                    row["commands"] = runner.commands
                    try:
                        shutil.rmtree(runner.build_root)
                    except OSError as error:
                        row.update(status="CLEANUP_FAILED", diagnostic=str(error))
                row["wall_seconds"] = time.monotonic() - began
                batch.save(directory / "result.json", row)
            return row

        before = time.monotonic()
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            result["attempts"] = list(pool.map(build, range(1, 5)))
        wall = time.monotonic() - before
        passed = sum(row["status"] == "PASSED" for row in result["attempts"])
        durations = [row["wall_seconds"] for row in result["attempts"]]
        result.update(
            status="PASSED" if passed == 4 else "FAILED",
            passed_builds=passed,
            build_group_wall_seconds=wall,
            completed_builds_per_minute=240 / wall,
            successful_builds_per_minute=60 * passed / wall,
            task_wall_seconds_sum=sum(durations),
            task_latency_p50_seconds=percentile(durations, 0.5),
            task_latency_p95_seconds=percentile(durations, 0.95),
        )
    except Exception as error:
        result.update(
            status="CANCELLED" if batch.CANCELLED.is_set() else "INFRASTRUCTURE_FAILED",
            diagnostic=f"{type(error).__name__}: {error}",
        )
    finally:
        try:
            for path in [source, *source.rglob("*")]:
                if path.is_dir() and not path.is_symlink():
                    path.chmod(0o700)
            shutil.rmtree(scratch)
        except OSError as error:
            result.update(status="CLEANUP_FAILED", cleanup_error=str(error))
        result["wall_seconds"] = time.monotonic() - started
        batch.save(output / "summary.json", result)
    print(json.dumps({key: result.get(key) for key in ("status", "workers", "passed_builds")}))
    return 0 if result["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
