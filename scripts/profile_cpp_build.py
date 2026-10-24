"""Zero-model A/B experiment on a frozen fmt regression, with a cold target control."""

import argparse
import json
import os
import re
import shutil
import signal
import statistics
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from actions_benchmark import save, sha
from benchmark_resources import disk_tree
from benchmark_resources import run as measured_run
from prepare_multiswe_task import git
from qualify_cpp_batch import CONFIGURE, archive, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--instance", default="fmtlib__fmt-4055")
    parser.add_argument("--target", default="format-test")
    parser.add_argument("--backend", choices=("native", "docker"), default="docker")
    parser.add_argument("--image")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--build-jobs", type=int, default=2)
    parser.add_argument("--optimization", choices=("O0", "O1", "O2", "O3"), default="O3")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.backend == "docker" and not re.fullmatch(r"sha256:[0-9a-f]{64}", args.image or ""):
        parser.error("Docker requires an immutable local image ID")
    if not 1 <= args.repeats <= 5 or not 1 <= args.build_jobs <= 4:
        parser.error("repeats must be 1..5; build jobs 1..4")

    def cancel(_signum, _frame):
        raise InterruptedError("PROFILE_CANCELLED")

    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, cancel)
    dataset = args.dataset / "cpp" if (args.dataset / "cpp").is_dir() else args.dataset
    record = next(r for r in records(dataset) if r["instance_id"] == args.instance)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(Path(__file__), output / "profile-script.py")
    source, build, cache = (output / name for name in ("source", "build", "ccache"))
    cache.mkdir(mode=0o777)
    cache.chmod(0o777)
    archive(args.repository, record["base"]["sha"], source)
    git(source, "init", "--template=", "-q", ".")
    for name in ("test", "reference"):
        path = output / (name + ".patch")
        path.write_text(record["test_patch" if name == "test" else "fix_patch"])
        git(source, "apply", str(path))
    for path in source.rglob("*"):
        path.chmod(path.stat().st_mode | 0o555 if path.is_dir() else path.stat().st_mode | 0o444)
    source.chmod(0o755)
    versions = {}
    for executable in ("cmake", "ninja", "g++", "ccache"):
        cmd = [executable, "--version"]
        if args.backend == "docker":
            cmd = ["docker", "run", "--rm", "--network=none", args.image, *cmd]
        versions[executable] = subprocess.check_output(cmd, text=True, timeout=30).splitlines()[0]
    summary = {
        "schema_version": 1,
        "instance_id": args.instance,
        "backend": args.backend,
        "image": args.image,
        "upstream_commit": record["base"]["sha"],
        "test_patch_sha256": sha(output / "test.patch"),
        "reference_patch_sha256": sha(output / "reference.patch"),
        "target": args.target,
        "build_jobs": args.build_jobs,
        "optimization": args.optimization,
        "versions": versions,
        "model_requests": 0,
        "samples": [],
        "status": "RUNNING",
        "scope": "target-level reference-patch build experiment; not agent repair success",
        "source_sha256": {"profile_script": sha(output / "profile-script.py")},
    }
    save(output / "profile.json", summary)
    started = time.monotonic()

    def command(argv, label, use_cache=False):
        name = "repropatch-profile-" + uuid.uuid4().hex[:12]
        environment = {
            **os.environ,
            "CCACHE_DIR": str(cache),
            "CCACHE_MAXSIZE": "1G",
            "CCACHE_COMPILERCHECK": "content",
        }
        for key in ("CCACHE_SLOPPINESS", "CCACHE_BASEDIR", "CCACHE_NOHASHDIR"):
            environment.pop(key, None)
        if not use_cache:
            environment["CCACHE_DISABLE"] = "1"
        else:
            environment.pop("CCACHE_DISABLE", None)
        if args.backend == "docker":
            cmd = [
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
                f"--user={os.getuid() or 65534}:{os.getgid() or 65534}",
                "--label",
                "repropatch.batch=" + os.environ.get("REPROPATCH_BATCH_ID", name),
                f"--cpus={args.build_jobs}",
                "--memory=4096m",
                "--memory-swap=4096m",
                "--pids-limit=256",
                "--ulimit=core=0:0",
                "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777",
                "--mount",
                f"type=bind,source={source},target=/src,readonly",
                "--mount",
                f"type=bind,source={build},target=/build",
                "--mount",
                f"type=bind,source={cache},target=/cache",
                "-e",
                "CCACHE_DIR=/cache",
                "-e",
                "CCACHE_MAXSIZE=1G",
                "-e",
                "CCACHE_COMPILERCHECK=content",
            ]
            if not use_cache:
                cmd += ["-e", "CCACHE_DISABLE=1"]
            cmd += ["--workdir=/build", args.image, *argv]
        else:
            cmd = [arg.replace("/src", str(source)).replace("/build", str(build)) for arg in argv]
        log = output / (label + ".log")
        measurement = output / (label + "-command")
        before = time.monotonic()
        try:
            measured_run(
                argparse.Namespace(
                    output=measurement,
                    timeout=600,
                    interval=1,
                    watch_interval=5,
                    log_limit_bytes=2 * 1024 * 1024,
                    kill_grace_seconds=2,
                    watch=[],
                    command=cmd,
                    environment=environment,
                )
            )
            measured = json.loads((measurement / "telemetry.json").read_text())
            with log.open("xb") as stream:
                for filename in ("stdout.log", "stderr.log"):
                    with (measurement / filename).open("rb") as original:
                        shutil.copyfileobj(original, stream)
            if measured["status"] == "cancelled":
                raise InterruptedError("PROFILE_CANCELLED")
            if measured["status"] not in {"success", "command_failed"}:
                raise RuntimeError("PROFILE_COMMAND_ABORTED: " + measured["status"])
            result = {
                "argv": argv,
                "seconds": time.monotonic() - before,
                "exit_code": measured["returncode"],
                "resource_evidence": str(measurement.relative_to(output)),
                "log": log.name,
                "sha256": sha(log),
            }
        finally:
            if args.backend == "docker":
                subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=30)
                remaining = subprocess.check_output(
                    ["docker", "ps", "-aq", "--filter", f"name=^/{name}$"], timeout=30
                )
                if remaining.strip():
                    raise RuntimeError("CONTAINER_CLEANUP_UNCONFIRMED")
        if log.stat().st_size > 4 * 1024 * 1024:
            raise RuntimeError("PROFILE_LOG_LIMIT")
        return result

    def sample(
        variant, repeat, *, generator="Ninja", use_cache=False, incremental=False, expected=True
    ):
        if not incremental:
            if build.exists():
                shutil.rmtree(build)
            build.mkdir(mode=0o777)
            build.chmod(0o777)
        label = f"{variant}-{repeat}"
        row = {
            "variant": variant,
            "repeat": repeat,
            "generator": generator,
            "compiler_cache": use_cache,
            "incremental": incremental,
            "expected_pass": expected,
        }
        before = time.monotonic()
        if not incremental:
            config = [*CONFIGURE, f"-DCMAKE_CXX_FLAGS_RELEASE=-{args.optimization} -DNDEBUG"]
            config[config.index("Ninja")] = generator
            if use_cache:
                config += [
                    "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache",
                    "-DCMAKE_C_COMPILER_LAUNCHER=ccache",
                ]
            row["configure"] = command(config, label + "-configure", use_cache)
            if row["configure"]["exit_code"]:
                raise RuntimeError("PROFILE_CONFIGURE_FAILED")
        row["build"] = command(
            [
                "cmake",
                "--build",
                "/build",
                "--target",
                args.target,
                "--parallel",
                str(args.build_jobs),
            ],
            label + "-build",
            use_cache,
        )
        row["test"] = None
        if row["build"]["exit_code"] == 0:
            row["test"] = command(
                [
                    "ctest",
                    "--test-dir",
                    "/build",
                    "--output-on-failure",
                    "--no-tests=error",
                    "-R",
                    "^" + re.escape(args.target) + "$",
                    "--output-junit",
                    "/build/profile-results.xml",
                ],
                label + "-test",
                use_cache,
            )
            xml = ET.parse(build / "profile-results.xml")
            tests = xml.findall(".//testcase")
            row["tests"] = [
                {
                    "name": t.attrib["name"],
                    "passed": t.find("failure") is None
                    and t.find("skipped") is None
                    and t.find("error") is None,
                }
                for t in tests
            ]
            shutil.copyfile(build / "profile-results.xml", output / (label + ".xml"))
        row["passed"] = bool(
            row["test"]
            and row["test"]["exit_code"] == 0
            and row.get("tests") == [{"name": args.target, "passed": True}]
        )
        row["seconds"] = time.monotonic() - before
        row["build_bytes"] = disk_tree(build)["allocated_bytes"]
        row["cache_bytes"] = disk_tree(cache)["allocated_bytes"]
        summary["samples"].append(row)
        save(output / "profile.json", summary)
        if row["passed"] != expected:
            raise RuntimeError("CACHE_OR_BUILD_VERDICT_MISMATCH")
        return row

    try:
        for repeat in range(args.repeats):
            sample("cold-make", repeat, generator="Unix Makefiles")
            sample("cold-ninja", repeat)
        sample("cache-fill", 0, use_cache=True)
        for repeat in range(args.repeats):
            sample("cache-warm-fresh-build", repeat, use_cache=True)
            sample("incremental-unchanged", repeat, use_cache=True, incremental=True)
        # A real header/source edit must invalidate cached objects and recover the original failure.
        git(source, "apply", "-R", str(output / "reference.patch"))
        sample("reference-reverted", 0, use_cache=True, incremental=True, expected=False)
        git(source, "apply", str(output / "reference.patch"))
        sample("reference-reapplied", 0, use_cache=True, incremental=True)
        sample("final-cold", 0)
        summary["ccache_stats"] = command(["ccache", "--show-stats"], "ccache-stats", True)
        summary["medians_seconds"] = {
            variant: statistics.median(
                r["seconds"] for r in summary["samples"] if r["variant"] == variant
            )
            for variant in sorted({r["variant"] for r in summary["samples"]})
        }
        summary["status"] = "PASSED"
    except Exception as error:
        summary.update(
            status="CANCELLED" if isinstance(error, InterruptedError) else "FAILED",
            error_type=type(error).__name__,
            error=str(error),
        )
        raise
    finally:
        summary["wall_seconds"] = time.monotonic() - started
        summary["final_build_bytes"] = disk_tree(build)["allocated_bytes"]
        summary["final_cache_bytes"] = disk_tree(cache)["allocated_bytes"]
        save(output / "profile.json", summary)
    print(
        json.dumps(
            {
                "status": summary["status"],
                "medians_seconds": summary["medians_seconds"],
                "model_requests": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
