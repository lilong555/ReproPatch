"""Small, model-free Actions planner, input cache and verifiable batch archives."""

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import tarfile
import time
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ("fmtlib__fmt-4055", "fmtlib__fmt-3863")
FRAMEWORKS = ("repropatch", "repropatch-no-checks", "mini", "codex")


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_plan(path):
    data = json.loads(path.read_text())
    recorded = data.pop("plan_sha256")
    if hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest() != recorded:
        raise ValueError("PLAN_HASH_MISMATCH")
    data["plan_sha256"] = recorded
    return data


def plan(args):
    toolchain_image = getattr(args, "toolchain_image", "")
    if toolchain_image and (
        args.backend != "docker"
        or not re.fullmatch(r"ghcr\.io/[a-z0-9._/-]+@sha256:[0-9a-f]{64}", toolchain_image)
    ):
        raise ValueError("TOOLCHAIN_REQUIRES_FIXED_GHCR_DIGEST_AND_DOCKER")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", args.batch):
        raise ValueError("INVALID_BATCH_ID")
    if not 1 <= args.parallel <= 4 or not 1 <= args.requests <= 12:
        raise ValueError("PARALLEL_MUST_BE_1_TO_4_AND_REQUESTS_1_TO_12")
    if args.total_request_cap < 0:
        raise ValueError("TOTAL_REQUEST_CAP_MUST_BE_NONNEGATIVE")
    coverage = json.loads((ROOT / "benchmarks/coverage.json").read_text())
    available = {
        row["instance_id"]: row for row in coverage["records"] if row["repository"] == "fmtlib/fmt"
    }
    identifiers = (
        list(SMOKE)
        if args.tasks == "smoke"
        else sorted(available)
        if args.tasks == "fmt-all"
        else args.tasks.split(",")
    )
    if len(set(identifiers)) != len(identifiers) or not set(identifiers) <= available.keys():
        raise ValueError("TASKS_MUST_BE_UNIQUE_FROZEN_FMT_INSTANCES")
    if args.mode == "profile" and SMOKE[0] not in identifiers:
        raise ValueError("PROFILE_REQUIRES_FMT_4055")
    frameworks = args.frameworks.split(",")
    if not set(frameworks) <= set(FRAMEWORKS) or len(set(frameworks)) != len(frameworks):
        raise ValueError("INVALID_FRAMEWORKS")
    if args.allow_paid_model:
        raise ValueError(
            "PAID_EXECUTION_REQUIRES_A_REVIEWED_PROVIDER_COST_POLICY; this workflow is model-free"
        )
    tasks = [available[identifier] for identifier in identifiers]
    estimates = json.loads(args.estimates.read_text()) if args.estimates else {}
    shards = [
        {"shard": i, "instances": [], "estimated_seconds": 0}
        for i in range(min(args.parallel, len(tasks)))
    ]
    # Longest-processing-time greedy partition; historical measured estimates are optional.
    for row in sorted(
        tasks, key=lambda r: (-estimates.get(r["instance_id"], 600), r["instance_id"])
    ):
        shard = min(shards, key=lambda s: (s["estimated_seconds"], s["shard"]))
        shard["instances"].append(row["instance_id"])
        shard["estimated_seconds"] += estimates.get(row["instance_id"], 600)
    for shard in shards:
        shard["instances"] = ",".join(shard["instances"])
        shard["inputs_key"] = hashlib.sha256(shard["instances"].encode()).hexdigest()[:16]
    formal = args.mode == "plan-formal"
    attempts = (
        [
            {
                "attempt_id": f"{args.batch}/{identifier}/{framework}/first",
                "instance_id": identifier,
                "framework": framework,
                "request_cap": args.requests,
                "status": "NOT_EXECUTED",
            }
            for identifier in identifiers
            for framework in frameworks
        ]
        if formal
        else []
    )
    proposed = sum(a["request_cap"] for a in attempts)
    if formal and args.total_request_cap and proposed > args.total_request_cap:
        raise ValueError("GLOBAL_REQUEST_CAP_TOO_SMALL_FOR_ALL_PREREGISTERED_ATTEMPTS")
    result = {
        "schema_version": 1,
        "batch_id": args.batch,
        "created_at": datetime.now(UTC).isoformat(),
        "mode": args.mode,
        "code_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "dataset_revision": coverage["revision"],
        "coverage_sha256": sha(ROOT / "benchmarks/coverage.json"),
        "estimates_sha256": sha(args.estimates) if args.estimates else None,
        "implementation_sha256": {
            str(path.relative_to(ROOT)): sha(path)
            for path in [
                ROOT / "scripts/actions_benchmark.py",
                ROOT / "scripts/qualify_cpp_batch.py",
                ROOT / "scripts/verify_qualification_evidence.py",
                ROOT / "scripts/profile_cpp_build.py",
                ROOT / "scripts/benchmark_resources.py",
                ROOT / "scripts/profile_cpp_concurrency.py",
                ROOT / "scripts/check_qualified_cpp_candidate.py",
                ROOT / "scripts/score_benchmark_attempt.py",
                ROOT / "scripts/run_benchmark_agent.py",
                ROOT / "scripts/run_codex_benchmark.py",
                ROOT / "docker/Dockerfile",
            ]
        },
        "tasks": tasks,
        "matrix": {"include": shards},
        "model": args.model,
        "frameworks": frameworks,
        "model_execution_authorized": False,
        "executed_request_cap": 0,
        "proposed_request_cap": proposed,
        "proposed_attempts": attempts,
        "cost": "UNKNOWN",
        "status": "PLANNED_ONLY" if formal else "REGISTERED_NO_MODEL",
        "resource_policy": {
            "build_jobs": 2,
            "parallel_jobs": args.parallel,
            "task_timeout_seconds": 1800,
            "backend": args.backend,
            "optimization": args.optimization,
            "toolchain_scope": (
                "shared-ghcr-digest"
                if toolchain_image
                else "per-job-local-image"
                if args.backend == "docker"
                else "native-host"
            ),
            "toolchain_image": toolchain_image or None,
            "actions_input_cache": args.cache_inputs,
        },
        "notes": [
            "Attempt allocations are immutable; reruns use a new batch and retain prior attempts.",
            "A plan is not authorization to spend; no model credentials enter this workflow.",
            "Historical task estimates guide relative shard balance, not promised Runner times.",
        ],
    }
    result["plan_sha256"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    if args.output.exists():
        raise FileExistsError("BATCH_PLAN_ALREADY_EXISTS")
    save(args.output, result)
    if os.environ.get("GITHUB_OUTPUT"):
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as out:
            out.write("matrix=" + json.dumps(result["matrix"], separators=(",", ":")) + "\n")
            out.write("execute=" + str(not formal).lower() + "\n")
    print(
        json.dumps(
            {
                "tasks": len(tasks),
                "shards": len(shards),
                "model_requests": 0,
                "proposed_request_cap": proposed,
                "plan_sha256": result["plan_sha256"],
            }
        )
    )


def prepare(args):
    frozen = read_plan(args.plan)
    coverage = json.loads((ROOT / "benchmarks/coverage.json").read_text())
    if sha(ROOT / "benchmarks/coverage.json") != frozen["coverage_sha256"]:
        raise ValueError("COVERAGE_CHANGED")
    if any(sha(ROOT / path) != digest for path, digest in frozen["implementation_sha256"].items()):
        raise ValueError("IMPLEMENTATION_CHANGED_AFTER_PLAN")
    selected = set(args.instances.split(","))
    rows = [r for r in frozen["tasks"] if r["instance_id"] in selected]
    if len(rows) != len(selected):
        raise ValueError("UNREGISTERED_TASK")
    dataset = args.output / "dataset"
    path = dataset / "cpp/fmtlib__fmt_dataset.jsonl"
    source = next(r for r in coverage["source_files"] if r["path"] == path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or sha(path) != source["sha256"]:
        url = (
            "https://huggingface.co/datasets/ByteDance-Seed/Multi-SWE-bench/resolve/"
            + frozen["dataset_revision"]
            + "/cpp/"
            + path.name
        )
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read(source["size"] + 1)
        if len(data) != source["size"] or hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise ValueError("DATASET_HASH_MISMATCH")
        path.write_bytes(data)
    (dataset / "revision.txt").write_text(frozen["dataset_revision"] + "\n")
    repository = args.output / "fmt"
    repository.mkdir(parents=True, exist_ok=True)

    def git(*argv, check=True):
        return subprocess.run(
            ["git", "-c", "core.hooksPath=/dev/null", "-C", str(repository), *argv],
            check=check,
            capture_output=True,
            timeout=180,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )

    if not (repository / ".git").exists():
        git("init", "--template=", "-q")
    for row in rows:
        commit = row["base_commit"]
        if git("cat-file", "-e", commit + "^{commit}", check=False).returncode:
            git(
                "fetch",
                "--no-tags",
                "--depth=1",
                "https://github.com/fmtlib/fmt.git",
                commit + ":refs/repropatch/" + commit,
            )
    save(
        args.output / "inputs.json",
        {
            "dataset_revision": frozen["dataset_revision"],
            "dataset_sha256": sha(path),
            "commits": [r["base_commit"] for r in rows],
        },
    )
    print(
        json.dumps({"prepared": len(rows), "dataset": str(dataset), "repository": str(repository)})
    )


def pack(args):
    started = time.monotonic()
    source, target = args.source.resolve(), args.output.resolve()
    if not source.is_dir():
        raise ValueError("EVIDENCE_DIRECTORY_MISSING")
    if target.is_relative_to(source):
        raise ValueError("ARCHIVE_MUST_BE_OUTSIDE_EVIDENCE_DIRECTORY")
    if target.exists():
        raise FileExistsError("ARCHIVE_ALREADY_EXISTS")
    excluded = {".git", "repository", "source", "build", "ccache", "workspaces", "inputs"}
    paths = sorted(
        p
        for p in source.rglob("*")
        if p.is_file()
        and not (set(p.relative_to(source).parts) & excluded)
        and not any(
            part != "execution-source" and part.endswith(("-build", "-source"))
            for part in p.relative_to(source).parts[:-1]
        )
    )
    if not paths:
        raise ValueError("NO_EVIDENCE_FILES")
    records = []
    for path in paths:
        if path.is_symlink():
            raise ValueError("EVIDENCE_SYMLINK")
        records.append(
            {
                "path": path.relative_to(source).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha(path),
            }
        )
    manifest = source / "archive-manifest.json"
    if manifest.exists():
        raise FileExistsError("EVIDENCE_ALREADY_PACKED")
    save(
        manifest,
        {
            "schema_version": 1,
            "files": records,
            "excluded_reconstructible_directories": sorted(excluded),
            "excluded_directory_suffixes": ["-build", "-source"],
            "retained_directory_exceptions": ["execution-source"],
        },
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".partial")
    with tarfile.open(temporary, "x:gz", compresslevel=6) as archive:
        for path in [*paths, manifest]:
            archive.add(path, arcname=path.relative_to(source).as_posix(), recursive=False)
    with tarfile.open(temporary) as archive:
        for record in records:
            stream = archive.extractfile(record["path"])
            if (
                stream is None
                or hashlib.file_digest(stream, "sha256").hexdigest() != record["sha256"]
            ):
                raise ValueError("ARCHIVE_VERIFICATION_FAILED")
    temporary.replace(target)
    digest = sha(target)
    target.with_name(target.name + ".sha256").write_text(f"{digest}  {target.name}\n")
    result = {
        "status": "LOCAL_ARCHIVE_VERIFIED",
        "remote_archive_status": "NOT_UPLOADED",
        "sha256": digest,
        "files": len(records),
        "uncompressed_bytes": sum(r["size_bytes"] for r in records),
        "archive_bytes": target.stat().st_size,
        "pack_seconds": time.monotonic() - started,
    }
    save(target.with_suffix(".metadata.json"), result)
    print(json.dumps(result))


def archive_receipt(args):
    """Confirm the uploaded artifact by hashing its downloaded archive bytes."""
    if args.output.exists():
        raise FileExistsError("ARCHIVE_RECEIPT_ALREADY_EXISTS")
    receipt = {
        "schema_version": 1,
        "checked_at": datetime.now(UTC).isoformat(),
        "status": "ARCHIVE_EVIDENCE_MISSING",
        "artifact_url": args.artifact_url,
        "artifact_id": args.artifact_id,
        "upload_status": args.upload_status,
        "download_status": args.download_status,
    }
    if args.upload_status != "success":
        receipt["status"] = "ARCHIVE_UPLOAD_FAILED"
    elif args.download_status != "success":
        receipt["status"] = "ARCHIVE_DOWNLOAD_FAILED"
    elif not (
        args.metadata.is_file()
        and args.downloaded.is_file()
        and args.artifact_url
        and args.artifact_id
    ):
        receipt["status"] = "ARCHIVE_EVIDENCE_MISSING"
    else:
        try:
            metadata = json.loads(args.metadata.read_text())
            expected = metadata.get("sha256", "")
            receipt.update(
                local_metadata_sha256=sha(args.metadata),
                local_archive_sha256=expected,
                downloaded_archive_sha256=sha(args.downloaded),
                downloaded_archive_bytes=args.downloaded.stat().st_size,
            )
            if metadata.get("status") != "LOCAL_ARCHIVE_VERIFIED" or not re.fullmatch(
                r"[0-9a-f]{64}", expected
            ):
                receipt["status"] = "ARCHIVE_LOCAL_METADATA_INVALID"
            elif receipt["downloaded_archive_sha256"] != expected:
                receipt["status"] = "ARCHIVE_CHECKSUM_MISMATCH"
            else:
                receipt["status"] = "ARCHIVE_VERIFIED_REMOTE"
        except (OSError, ValueError, TypeError, AttributeError) as error:
            receipt.update(status="ARCHIVE_EVIDENCE_INVALID", diagnostic=str(error)[:1000])
    save(args.output, receipt)
    print(json.dumps(receipt))
    return 0 if receipt["status"] == "ARCHIVE_VERIFIED_REMOTE" else 1


def aggregate(args):
    frozen = read_plan(args.plan)
    registered = {r["instance_id"]: r for r in frozen["tasks"]}
    found = {}
    duplicates = []
    for path in sorted(args.source.rglob("batch-summary.json")):
        data = json.loads(path.read_text())
        if data.get("dataset_revision") != frozen["dataset_revision"]:
            raise ValueError("RESULT_DATASET_MISMATCH")
        policy = frozen["resource_policy"]
        expected_image = policy.get("toolchain_image")
        if expected_image:
            environment_path = path.parent / "toolchain.json"
            if not environment_path.is_file():
                raise ValueError("SHARED_TOOLCHAIN_RECEIPT_MISSING")
            environment = json.loads(environment_path.read_text())
            if (
                environment.get("image") != expected_image
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", environment.get("image_id", ""))
                or any(
                    row.get("image_id") != environment["image_id"]
                    for row in data.get("tasks", data.get("results", []))
                    if row.get("status") == "QUALIFIED"
                )
            ):
                raise ValueError("SHARED_TOOLCHAIN_IDENTITY_MISMATCH")
        for field in ("backend", "optimization"):
            if field in policy and data.get(field) != policy[field]:
                raise ValueError("RESULT_CONFIGURATION_MISMATCH: " + field)
        audit_reference = data.get("evidence_audit", {})
        audit_path = path.parent / audit_reference.get("path", "MISSING")
        audit_valid = (
            audit_path.resolve().is_relative_to(path.parent.resolve())
            and audit_path.is_file()
            and sha(audit_path) == audit_reference.get("sha256")
        )
        receipt_path = path.parent / "archive-receipt.json"
        remote_required = bool(os.environ.get("GITHUB_RUN_ID")) or receipt_path.exists()
        archive_status = "NOT_REQUIRED_LOCAL_AGGREGATION"
        if remote_required:
            archive_status = "ARCHIVE_RECEIPT_MISSING"
            if receipt_path.is_file():
                try:
                    receipt = json.loads(receipt_path.read_text())
                    archive_status = receipt.get("status", "ARCHIVE_RECEIPT_INVALID")
                    if archive_status == "ARCHIVE_VERIFIED_REMOTE" and not (
                        receipt.get("upload_status") == "success"
                        and receipt.get("download_status") == "success"
                        and receipt.get("artifact_id")
                        and receipt.get("artifact_url")
                        and re.fullmatch(r"[0-9a-f]{64}", receipt.get("local_archive_sha256", ""))
                        and receipt.get("local_archive_sha256")
                        == receipt.get("downloaded_archive_sha256")
                    ):
                        archive_status = "ARCHIVE_RECEIPT_INVALID"
                except (OSError, ValueError, TypeError, AttributeError):
                    archive_status = "ARCHIVE_RECEIPT_INVALID"
        for row in data.get("tasks", data.get("results", [])):
            identifier = row["instance_id"]
            if identifier not in registered:
                raise ValueError("UNREGISTERED_RESULTS")
            if row.get("upstream_commit") != registered[identifier]["base_commit"]:
                raise ValueError("RESULT_COMMIT_MISMATCH: " + identifier)
            if identifier in found:
                duplicates.append(identifier)
            row = dict(row)
            row["archive_status"] = archive_status
            if receipt_path.is_file():
                row["archive_receipt_sha256"] = sha(receipt_path)
            if row["status"] in {"QUALIFIED", "HOST_QUALIFIED"} and (
                row.get("evidence_status") not in {"VERIFIED", "RECOVERED_EXACT"}
                or not audit_valid
                or (remote_required and archive_status != "ARCHIVE_VERIFIED_REMOTE")
            ):
                row["execution_status"] = row.get("execution_status", row["status"])
                row["status"] = "EVIDENCE_INCOMPLETE"
                row["evidence_status"] = row.get("evidence_status", "MISSING")
                row["diagnostic"] = (
                    "Qualification evidence, its audit, or required remote archive is incomplete"
                )
            found[identifier] = {
                **row,
                "duration_seconds": row.get("wall_seconds"),
                "reason": row.get("diagnostic", row.get("failure_type", "")),
            }
    if duplicates:
        raise ValueError("DUPLICATE_ATTEMPTS: " + ",".join(sorted(set(duplicates))))
    if frozen["mode"] == "plan-formal" and found:
        raise ValueError("FORMAL_PROPOSAL_CANNOT_CONTAIN_EXECUTED_RESULTS")
    rows = [
        found.get(r["instance_id"], {"instance_id": r["instance_id"], "status": "NOT_EXECUTED"})
        for r in frozen["tasks"]
    ]
    durations = sorted(
        r["duration_seconds"] for r in rows if isinstance(r.get("duration_seconds"), (int, float))
    )

    def percentile(fraction):
        if not durations:
            return None
        position = (len(durations) - 1) * fraction
        left = int(position)
        right = min(left + 1, len(durations) - 1)
        return durations[left] + (durations[right] - durations[left]) * (position - left)

    phases = {}
    for row in rows:
        for phase, detail in row.get("phases", {}).items():
            phases.setdefault(phase, Counter())[detail["status"]] += 1
        row["f2p_count"] = len(row["f2p"]) if "f2p" in row else None
        row["p2p_count"] = len(row["p2p"]) if "p2p" in row else None
    statuses = dict(Counter(r["status"] for r in rows))
    result = {
        "schema_version": 1,
        "batch_id": frozen["batch_id"],
        "plan_sha256": frozen["plan_sha256"],
        "registered_tasks": len(rows),
        "status_counts": statuses,
        "archive_status_counts": dict(
            Counter(r.get("archive_status", "NOT_RECORDED") for r in rows)
        ),
        "phase_status_counts": phases,
        "task_duration_seconds": {
            "sample_count": len(durations),
            "total": sum(durations),
            "p50": percentile(0.5),
            "p90": percentile(0.9),
            "p95": percentile(0.95),
            "scope": "sum of task wall times; not Runner minutes or batch wall time",
            "percentile_method": "linear interpolation at (sample_count - 1) * fraction",
        },
        "model_requests": 0,
        "model_tokens": {"input": 0, "output": 0},
        "model_cost": (
            "UNKNOWN_NOT_EXECUTED"
            if frozen["mode"] == "plan-formal"
            else "NOT_APPLICABLE_NO_MODEL_CALLS"
        ),
        "github_run_url": os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        + "/"
        + os.environ.get("GITHUB_REPOSITORY", "lilong555/ReproPatch")
        + "/actions/runs/"
        + os.environ["GITHUB_RUN_ID"]
        if os.environ.get("GITHUB_RUN_ID")
        else "NOT_MEASURED",
        "tasks": rows,
        "proposed_attempts": frozen["proposed_attempts"],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    save(args.output / "summary.json", result)
    with (args.output / "summary.csv").open("w", newline="") as out:
        writer = csv.DictWriter(
            out,
            fieldnames=[
                "instance_id",
                "status",
                "execution_status",
                "evidence_status",
                "archive_status",
                "reason",
                "wall_seconds",
                "duration_seconds",
                "f2p_count",
                "p2p_count",
                "optimization",
                "exposure",
            ],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(
            {
                **r,
                "exposure": json.dumps(r["exposure"], ensure_ascii=False)
                if isinstance(r.get("exposure"), (dict, list))
                else r.get("exposure", ""),
            }
            for r in rows
        )
    lines = [
        "# C++ qualification batch",
        "",
        f"Batch: `{frozen['batch_id']}`; registered: {len(rows)}; model requests: **0**.",
        f"Observed task times: {len(durations)}; total {sum(durations):.3f} seconds "
        "(task wall-time sum, not Runner minutes).",
        "",
        "| Task | Status | Reason |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        f"| {r['instance_id']} | {r['status']} | {str(r.get('reason', '')).replace('|', '/')} |"
        for r in rows
    )
    lines += [
        "",
        "`HOST_QUALIFIED` records a native-host precheck. Docker has its own toolchain identity.",
        "A passed qualification requires a verified evidence audit; "
        "incomplete evidence is explicit.",
        "Cloud aggregation also requires an archive receipt whose downloaded bytes match "
        "the locally verified archive SHA-256.",
        "Missing results remain NOT_EXECUTED; recorded cancellations retain their status.",
        "Formal model results are reported separately.",
        "",
    ]
    (args.output / "summary.md").write_text("\n".join(lines))
    print(json.dumps({"registered_tasks": len(rows), "statuses": statuses, "model_requests": 0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("plan")
    p.add_argument("--mode", choices=("qualify", "profile", "plan-formal"), default="qualify")
    p.add_argument("--tasks", default="smoke")
    p.add_argument("--parallel", type=int, default=2)
    p.add_argument("--batch", required=True)
    p.add_argument("--model", default="gpt-6-luna")
    p.add_argument("--frameworks", default=",".join(FRAMEWORKS))
    p.add_argument("--requests", type=int, default=12)
    p.add_argument("--total-request-cap", type=int, default=0)
    p.add_argument("--allow-paid-model", action="store_true")
    p.add_argument("--cache-inputs", action="store_true")
    p.add_argument("--backend", choices=("docker", "native"), default="docker")
    p.add_argument("--toolchain-image", default="")
    p.add_argument("--optimization", choices=("O0", "O1", "O2", "O3"), default="O3")
    p.add_argument("--estimates", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(function=plan)
    p = commands.add_parser("prepare")
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--instances", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(function=prepare)
    p = commands.add_parser("pack")
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(function=pack)
    p = commands.add_parser("aggregate")
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(function=aggregate)
    p = commands.add_parser("archive-receipt")
    p.add_argument("--metadata", type=Path, required=True)
    p.add_argument("--downloaded", type=Path, required=True)
    p.add_argument("--artifact-url", required=True)
    p.add_argument("--artifact-id", required=True)
    p.add_argument("--upload-status", required=True)
    p.add_argument("--download-status", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(function=archive_receipt)
    args = parser.parse_args()
    return args.function(args)


if __name__ == "__main__":
    raise SystemExit(main())
