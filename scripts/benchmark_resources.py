#!/usr/bin/env python3
"""Run one command with bounded logs, a deadline, and sampled Linux resource evidence.

Example: python scripts/benchmark_resources.py --output /tmp/measure --timeout 900 \
    --watch build=/tmp/build -- cmake --build /tmp/build -j 4
Host/cgroup observations include other activity; sampled peaks are lower bounds.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path


def read_int(path: str) -> int | None:
    try:
        return int(Path(path).read_text().strip())
    except (OSError, ValueError):
        return None


def disk_tree(path: Path) -> dict:
    """Allocated bytes, deduplicating hardlinks; report inaccessible paths explicitly."""
    total, errors, seen = 0, 0, set()
    if not path.exists():
        return {"allocated_bytes": None, "status": "missing"}

    def error(_exc):
        nonlocal errors
        errors += 1

    paths = ((Path(root), names) for root, _, names in os.walk(path, onerror=error))
    if path.is_file():
        paths = ((path.parent, [path.name]),)
    for root, names in paths:
        items = [root / name for name in names]
        if path.is_dir():
            items.append(root)
        for item in items:
            try:
                info = item.lstat()
                identity = (info.st_dev, info.st_ino)
                if identity not in seen and not stat.S_ISLNK(info.st_mode):
                    total += info.st_blocks * 512
                    seen.add(identity)
            except OSError:
                errors += 1
    return {"allocated_bytes": total, "status": "partial" if errors else "ok", "errors": errors}


def sample(output: Path, root_pid: int | None) -> dict:
    usage = shutil.disk_usage(output)
    data = {"filesystem_used_bytes": usage.used, "filesystem_free_bytes": usage.free}
    try:
        fields = [int(x) for x in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
        data["host_cpu_ticks"] = sum(fields[:8])
        data["host_cpu_idle_ticks"] = fields[3] + fields[4]
        mem = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
        total = int(mem["MemTotal"].split()[0]) * 1024
        data["host_memory_used_bytes"] = total - int(mem["MemAvailable"].split()[0]) * 1024
        data["host_memory_total_bytes"] = total
    except (OSError, ValueError, KeyError, IndexError):
        pass
    data["cgroup_memory_current_bytes"] = read_int("/sys/fs/cgroup/memory.current")
    data["cgroup_memory_limit_bytes"] = read_int("/sys/fs/cgroup/memory.max")
    processes, groups, children = {}, {}, {}
    page_size = os.sysconf("SC_PAGE_SIZE")
    for entry in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = entry.read_text().rsplit(")", 1)[1].split()
            pid, parent, group = int(entry.parent.name), int(fields[1]), int(fields[2])
            rss = max(0, int(fields[21])) * page_size
            processes[pid] = rss
            children.setdefault(parent, []).append(pid)
            groups[group] = groups.get(group, 0) + rss
        except (OSError, ValueError, IndexError):
            continue
    # A sandbox may expose outer /proc while Popen.pid is in an inner namespace.
    # Our measured command is a direct child; map only those children via NSpid.
    proc_root_pid = root_pid
    if root_pid is not None:
        try:
            proc_self = int(Path("/proc/self/stat").read_text().split()[0])
            if proc_self != os.getpid():
                proc_root_pid = None
                for pid in children.get(proc_self, ()):
                    status = Path(f"/proc/{pid}/status").read_text().splitlines()
                    ids = next(line.split()[1:] for line in status if line.startswith("NSpid:"))
                    if int(ids[-1]) == root_pid:
                        proc_root_pid = pid
                        break
        except (OSError, ValueError, StopIteration, IndexError):
            proc_root_pid = None
    # Compilers and nested command wrappers can create their own session/group.
    # Follow PPid independently of pgrp so those live descendants are included.
    pending = [proc_root_pid] if proc_root_pid is not None else []
    seen, tree_rss = set(), 0
    while pending:
        pid = pending.pop()
        if pid in seen:
            continue
        seen.add(pid)
        tree_rss += processes.get(pid, 0)
        pending.extend(children.get(pid, ()))
    data["proc_root_pid"] = proc_root_pid
    data["process_group_rss_bytes"] = groups.get(proc_root_pid, 0)
    data["process_tree_rss_bytes"] = tree_rss
    return data


def terminate_group(pid: int, signum: int) -> None:
    try:
        os.killpg(pid, signum)
    except ProcessLookupError:
        pass


def run(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    names = ("telemetry.json", "samples.jsonl", "stdout.log", "stderr.log")
    if any((output / name).exists() for name in names):
        raise ValueError("output already contains measurement files; use a new attempt directory")
    watched = {}
    for entry in args.watch:
        name, sep, path = entry.partition("=")
        if not sep or not name or not path or name in watched:
            raise ValueError("each --watch must have a unique name=PATH")
        watched[name] = Path(path).resolve()
    started = time.monotonic()
    result = {
        "schema_version": 1,
        "status": "running",
        "started_at": datetime.now(UTC).isoformat(),
        "command": args.command,
        "cwd": os.getcwd(),
        "timeout_seconds": args.timeout,
        "sample_interval_seconds": args.interval,
        "watch_interval_seconds": args.watch_interval,
        "kill_grace_seconds": getattr(args, "kill_grace_seconds", 2.0),
        "log_limit_bytes_per_stream": args.log_limit_bytes,
        "watched_paths": {name: str(path) for name, path in watched.items()},
        "peaks": {},
        "watched_peaks_allocated_bytes": {},
        "sample_count": 0,
        "measurement_scope": (
            "host/cgroup shared; group RSS uses root process group; tree RSS follows live PPid "
            "descendants including new sessions, excluding reparented children and Docker "
            "daemon-owned containers; summed RSS may count shared pages repeatedly; "
            "peaks are sampled lower bounds"
        ),
        "runtime": {
            "cpu_count": os.cpu_count(),
            "kernel": os.uname().release,
            "python": sys.version.split()[0],
            "runner": {
                key: os.environ[key]
                for key in (
                    "GITHUB_RUN_ID",
                    "GITHUB_RUN_ATTEMPT",
                    "GITHUB_SHA",
                    "GITHUB_REF",
                    "RUNNER_OS",
                    "RUNNER_ARCH",
                    "ImageOS",
                    "ImageVersion",
                )
                if key in os.environ
            },
        },
    }
    telemetry = output / "telemetry.json"
    telemetry.write_text(json.dumps(result, indent=2) + "\n")
    interrupted = []
    previous = {
        s: signal.signal(s, lambda s, _f: interrupted.append(s))
        for s in (signal.SIGINT, signal.SIGTERM)
    }
    process, selector = None, selectors.DefaultSelector()
    received, written = {"stdout": 0, "stderr": 0}, {"stdout": 0, "stderr": 0}
    stop_started, next_sample, next_watch = None, 0.0, 0.0
    term_sent, kill_sent = False, False
    last_cpu = None
    latest_dirs = {}
    observer_seconds = 0.0
    try:
        with (output / "stdout.log").open("xb") as out, (output / "stderr.log").open("xb") as err:
            logs = {"stdout": out, "stderr": err}
            process = subprocess.Popen(
                args.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                env=getattr(args, "environment", None),
            )
            for name, pipe in (("stdout", process.stdout), ("stderr", process.stderr)):
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ, name)
            with (output / "samples.jsonl").open("x") as samples:
                while selector.get_map() or process.poll() is None:
                    now = time.monotonic()
                    if interrupted and stop_started is None:
                        result["status"] = "cancelled"
                        result["signal"] = interrupted[0]
                        stop_started = now
                    if now - started >= args.timeout and stop_started is None:
                        result["status"] = "timeout"
                        stop_started = now
                    if stop_started is not None:
                        if not term_sent:
                            terminate_group(process.pid, signal.SIGTERM)
                            term_sent = True
                        if now - stop_started >= result["kill_grace_seconds"] and not kill_sent:
                            terminate_group(process.pid, signal.SIGKILL)
                            kill_sent = True
                    if now >= next_sample:
                        observer_started = time.monotonic()
                        row = sample(output, process.pid)
                        if now >= next_watch:
                            latest_dirs = {name: disk_tree(path) for name, path in watched.items()}
                            next_watch = now + args.watch_interval
                        row.update(elapsed_seconds=now - started, directories=latest_dirs)
                        cpu = (row.get("host_cpu_ticks"), row.get("host_cpu_idle_ticks"))
                        if last_cpu and None not in cpu and cpu[0] > last_cpu[0]:
                            row["host_cpu_percent"] = 100 * (
                                1 - (cpu[1] - last_cpu[1]) / (cpu[0] - last_cpu[0])
                            )
                        last_cpu = cpu if None not in cpu else None
                        for key, value in row.items():
                            if isinstance(value, (int, float)) and (
                                key.endswith("_bytes") or key == "host_cpu_percent"
                            ):
                                result["peaks"][key] = max(result["peaks"].get(key, 0), value)
                        result["filesystem_min_free_bytes"] = min(
                            result.get("filesystem_min_free_bytes", row["filesystem_free_bytes"]),
                            row["filesystem_free_bytes"],
                        )
                        for name, entry in latest_dirs.items():
                            size = entry["allocated_bytes"]
                            if size is not None:
                                old = result["watched_peaks_allocated_bytes"].get(name, 0)
                                result["watched_peaks_allocated_bytes"][name] = max(old, size)
                        samples.write(json.dumps(row) + "\n")
                        samples.flush()
                        result["sample_count"] += 1
                        next_sample = now + args.interval
                        observer_seconds += time.monotonic() - observer_started
                    for key, _ in selector.select(timeout=0.1):
                        data = os.read(key.fileobj.fileno(), 65536)
                        if not data:
                            selector.unregister(key.fileobj)
                            key.fileobj.close()
                            continue
                        name = key.data
                        received[name] += len(data)
                        keep = data[: max(0, args.log_limit_bytes - written[name])]
                        logs[name].write(keep)
                        written[name] += len(keep)
                        if received[name] > args.log_limit_bytes and stop_started is None:
                            result["status"] = "output_limit_exceeded"
                            stop_started = time.monotonic()
                result["returncode"] = process.wait()
                if result["status"] == "running":
                    result["status"] = "success" if process.returncode == 0 else "command_failed"
    except OSError as exc:
        result.update(status="infrastructure_error", error=str(exc))
    finally:
        if process is not None:
            terminate_group(process.pid, signal.SIGKILL)
            process.wait()
            result.setdefault("returncode", process.returncode)
        selector.close()
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        result.update(
            wall_seconds=time.monotonic() - started,
            log_bytes_received=received,
            log_bytes_written=written,
            observer_seconds=observer_seconds,
            finished_at=datetime.now(UTC).isoformat(),
        )
        result["final_resources"] = sample(output, None)
        for key, value in result["final_resources"].items():
            if isinstance(value, (int, float)) and key.endswith("_bytes"):
                result["peaks"][key] = max(result["peaks"].get(key, 0), value)
        final_free = result["final_resources"]["filesystem_free_bytes"]
        result["filesystem_min_free_bytes"] = min(
            result.get("filesystem_min_free_bytes", final_free), final_free
        )
        result["final_directories"] = {name: disk_tree(path) for name, path in watched.items()}
        result["logs_truncated"] = any(received[name] > written[name] for name in received)
        for name, entry in result["final_directories"].items():
            size = entry["allocated_bytes"]
            if size is not None:
                old = result["watched_peaks_allocated_bytes"].get(name, 0)
                result["watched_peaks_allocated_bytes"][name] = max(old, size)
        telemetry.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "telemetry": str(telemetry)}))
    return {
        "success": 0,
        "timeout": 124,
        "output_limit_exceeded": 125,
        "infrastructure_error": 127,
        "cancelled": 130,
    }.get(result["status"], 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", type=float, required=True)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--watch-interval", type=float, default=30.0)
    parser.add_argument("--kill-grace-seconds", type=float, default=2.0)
    parser.add_argument("--log-limit-bytes", type=int, default=4 * 1024 * 1024)
    parser.add_argument("--watch", action="append", default=[])
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command[:1] == ["--"]:
        args.command = args.command[1:]
    limits = (
        args.timeout,
        args.interval,
        args.watch_interval,
        args.log_limit_bytes,
        args.kill_grace_seconds,
    )
    if not args.command or any(not math.isfinite(value) or value <= 0 for value in limits):
        parser.error("command and positive timeout/interval/log limits are required")
    try:
        return run(args)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
