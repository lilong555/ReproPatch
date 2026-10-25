"""Protect zero-spend plans, result provenance, bounded commands, and archived evidence."""

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "actions_benchmark", ROOT / "scripts/actions_benchmark.py"
)
BENCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCH)


def make_plan(tmp_path, monkeypatch, **changes):
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    options = dict(
        batch="review-check",
        mode="qualify",
        tasks="smoke",
        parallel=2,
        frameworks=",".join(BENCH.FRAMEWORKS),
        requests=12,
        model="recorded-only",
        total_request_cap=0,
        allow_paid_model=False,
        cache_inputs=False,
        estimates=None,
        backend="native",
        optimization="O0",
        output=tmp_path / "plan.json",
    )
    options.update(changes)
    args = argparse.Namespace(**options)
    BENCH.plan(args)
    return args.output, BENCH.read_plan(args.output)


def shard_summary(plan):
    task = plan["tasks"][0]
    return {
        "dataset_revision": plan["dataset_revision"],
        "backend": "native",
        "optimization": "O0",
        "results": [
            {
                "instance_id": task["instance_id"],
                "upstream_commit": task["base_commit"],
                "status": "HOST_QUALIFIED",
                "evidence_status": "VERIFIED",
                "wall_seconds": 3.5,
                "optimization": "O0",
                "f2p": ["format-test"],
                "p2p": ["other-test"],
                "exposure": {"split": "development"},
                "phases": {
                    "baseline": {"status": "TESTS_FAILED"},
                    "reference": {"status": "PASSED"},
                },
            }
        ],
    }


def save_summary(path, summary):
    audit_path = path.parent / "audit.json"
    BENCH.save(
        audit_path,
        {
            "tasks": [
                {"instance_id": row["instance_id"], "status": "VERIFIED"}
                for row in summary["results"]
            ]
        },
    )
    summary["evidence_audit"] = {"path": "audit.json", "sha256": BENCH.sha(audit_path)}
    BENCH.save(path, summary)


def test_formal_plan_never_authorizes_spend_and_preserves_unexecuted_tasks(tmp_path, monkeypatch):
    plan_path, plan = make_plan(tmp_path, monkeypatch, mode="plan-formal", total_request_cap=96)
    assert plan["proposed_request_cap"] == 96
    assert plan["executed_request_cap"] == 0 and not plan["model_execution_authorized"]
    assert len(plan["proposed_attempts"]) == 8
    assert len({row["attempt_id"] for row in plan["proposed_attempts"]}) == 8
    BENCH.aggregate(
        argparse.Namespace(plan=plan_path, source=tmp_path / "missing", output=tmp_path / "r")
    )
    report = json.loads((tmp_path / "r/summary.json").read_text())
    assert report["status_counts"] == {"NOT_EXECUTED": 2}
    assert report["task_duration_seconds"]["sample_count"] == 0
    assert report["model_cost"] == "UNKNOWN_NOT_EXECUTED"


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"allow_paid_model": True}, "PAID_EXECUTION_REQUIRES"),
        ({"mode": "plan-formal", "total_request_cap": 95}, "GLOBAL_REQUEST_CAP_TOO_SMALL"),
    ],
)
def test_rejects_unapproved_or_underfunded_execution(tmp_path, monkeypatch, changes, reason):
    with pytest.raises(ValueError, match=reason):
        make_plan(tmp_path, monkeypatch, **changes)
    assert not (tmp_path / "plan.json").exists()


@pytest.mark.parametrize("image", ["ghcr.io/example/toolchain:latest", "ubuntu:24.04"])
def test_shared_toolchain_requires_an_immutable_registry_digest(tmp_path, monkeypatch, image):
    with pytest.raises(ValueError, match="TOOLCHAIN_REQUIRES_FIXED"):
        make_plan(tmp_path, monkeypatch, backend="docker", toolchain_image=image)


def test_aggregate_rejects_a_shard_with_a_different_toolchain(tmp_path, monkeypatch):
    image = "ghcr.io/example/toolchain@sha256:" + "a" * 64
    plan_path, plan = make_plan(tmp_path, monkeypatch, backend="docker", toolchain_image=image)
    summary = shard_summary(plan)
    summary["backend"] = "docker"
    directory = tmp_path / "inputs"
    save_summary(directory / "batch-summary.json", summary)
    BENCH.save(
        directory / "toolchain.json",
        {"image": image.replace("a" * 64, "b" * 64), "image_id": "sha256:" + "c" * 64},
    )
    with pytest.raises(ValueError, match="SHARED_TOOLCHAIN_IDENTITY_MISMATCH"):
        BENCH.aggregate(
            argparse.Namespace(plan=plan_path, source=directory, output=tmp_path / "report")
        )


def test_aggregate_preserves_missing_tasks_and_real_qualifier_fields(tmp_path, monkeypatch):
    plan_path, plan = make_plan(tmp_path, monkeypatch)
    save_summary(tmp_path / "inputs/shard-1/batch-summary.json", shard_summary(plan))
    BENCH.aggregate(
        argparse.Namespace(plan=plan_path, source=tmp_path / "inputs", output=tmp_path / "r")
    )
    report = json.loads((tmp_path / "r/summary.json").read_text())
    assert report["registered_tasks"] == 2
    assert report["status_counts"] == {"HOST_QUALIFIED": 1, "NOT_EXECUTED": 1}
    assert report["phase_status_counts"]["baseline"] == {"TESTS_FAILED": 1}
    assert report["task_duration_seconds"]["total"] == 3.5
    assert report["task_duration_seconds"]["p95"] == 3.5
    with (tmp_path / "r/summary.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["duration_seconds"] == "3.5" and rows[0]["f2p_count"] == "1"
    assert rows[0]["p2p_count"] == "1" and rows[0]["optimization"] == "O0"
    assert json.loads(rows[0]["exposure"]) == {"split": "development"}
    assert rows[1]["duration_seconds"] == ""


@pytest.mark.parametrize("damage", ["missing_audit", "changed_audit", "incomplete_task"])
def test_aggregate_does_not_count_passes_without_intact_evidence(tmp_path, monkeypatch, damage):
    plan_path, plan = make_plan(tmp_path, monkeypatch)
    summary_path = tmp_path / "inputs/shard-1/batch-summary.json"
    summary = shard_summary(plan)
    if damage == "incomplete_task":
        summary["results"][0]["evidence_status"] = "INCOMPLETE"
    save_summary(summary_path, summary)
    if damage == "missing_audit":
        (summary_path.parent / "audit.json").unlink()
    elif damage == "changed_audit":
        (summary_path.parent / "audit.json").write_text("changed\n")
    BENCH.aggregate(
        argparse.Namespace(plan=plan_path, source=tmp_path / "inputs", output=tmp_path / "r")
    )
    report = json.loads((tmp_path / "r/summary.json").read_text())
    assert report["status_counts"] == {"EVIDENCE_INCOMPLETE": 1, "NOT_EXECUTED": 1}
    assert report["tasks"][0]["execution_status"] == "HOST_QUALIFIED"


def receipt_arguments(tmp_path):
    downloaded = tmp_path / "downloaded.tar.gz"
    downloaded.write_bytes(b"frozen archive bytes\n")
    metadata = tmp_path / "archive.metadata.json"
    BENCH.save(metadata, {"status": "LOCAL_ARCHIVE_VERIFIED", "sha256": BENCH.sha(downloaded)})
    return argparse.Namespace(
        metadata=metadata,
        downloaded=downloaded,
        artifact_url="https://github.com/example/project/actions/runs/1/artifacts/2",
        artifact_id="2",
        upload_status="success",
        download_status="success",
        output=tmp_path / "archive-receipt.json",
    )


def test_archive_receipt_requires_downloaded_bytes_and_is_immutable(tmp_path):
    args = receipt_arguments(tmp_path)
    assert BENCH.archive_receipt(args) == 0
    receipt = json.loads(args.output.read_text())
    assert receipt["status"] == "ARCHIVE_VERIFIED_REMOTE"
    assert receipt["local_archive_sha256"] == receipt["downloaded_archive_sha256"]
    assert receipt["local_metadata_sha256"] == BENCH.sha(args.metadata)
    with pytest.raises(FileExistsError, match="ARCHIVE_RECEIPT_ALREADY_EXISTS"):
        BENCH.archive_receipt(args)


def test_archive_receipt_records_transfer_missing_and_checksum_failures(tmp_path):
    for damage, expected in (
        ("upload", "ARCHIVE_UPLOAD_FAILED"),
        ("download", "ARCHIVE_DOWNLOAD_FAILED"),
        ("missing", "ARCHIVE_EVIDENCE_MISSING"),
        ("checksum", "ARCHIVE_CHECKSUM_MISMATCH"),
    ):
        directory = tmp_path / damage
        directory.mkdir()
        args = receipt_arguments(directory)
        if damage == "upload":
            args.upload_status = "failure"
        elif damage == "download":
            args.download_status = "failure"
        elif damage == "missing":
            args.downloaded.unlink()
        else:
            args.downloaded.write_bytes(b"truncated archive")
        assert BENCH.archive_receipt(args) == 1
        assert json.loads(args.output.read_text())["status"] == expected


def test_cloud_aggregate_requires_a_verified_remote_archive_receipt(tmp_path, monkeypatch):
    plan_path, plan = make_plan(tmp_path, monkeypatch)
    summary_path = tmp_path / "inputs/shard-1/batch-summary.json"
    save_summary(summary_path, shard_summary(plan))
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    args = argparse.Namespace(plan=plan_path, source=tmp_path / "inputs", output=tmp_path / "r1")
    BENCH.aggregate(args)
    report = json.loads((args.output / "summary.json").read_text())
    assert report["status_counts"] == {"EVIDENCE_INCOMPLETE": 1, "NOT_EXECUTED": 1}
    assert report["tasks"][0]["execution_status"] == "HOST_QUALIFIED"
    assert report["tasks"][0]["archive_status"] == "ARCHIVE_RECEIPT_MISSING"
    receipt_args = receipt_arguments(summary_path.parent)
    assert BENCH.archive_receipt(receipt_args) == 0
    args.output = tmp_path / "r2"
    BENCH.aggregate(args)
    report = json.loads((args.output / "summary.json").read_text())
    assert report["status_counts"] == {"HOST_QUALIFIED": 1, "NOT_EXECUTED": 1}
    assert report["archive_status_counts"]["ARCHIVE_VERIFIED_REMOTE"] == 1
    monkeypatch.delenv("GITHUB_RUN_ID")
    receipt = json.loads(receipt_args.output.read_text())
    receipt["downloaded_archive_sha256"] = "0" * 64
    BENCH.save(receipt_args.output, receipt)
    args.output = tmp_path / "r3"
    BENCH.aggregate(args)
    report = json.loads((args.output / "summary.json").read_text())
    assert report["tasks"][0]["archive_status"] == "ARCHIVE_RECEIPT_INVALID"
    assert report["tasks"][0]["status"] == "EVIDENCE_INCOMPLETE"


@pytest.mark.parametrize("kind", ["dataset", "commit", "optimization", "duplicate"])
def test_aggregate_rejects_mixed_identities_and_duplicate_attempts(tmp_path, monkeypatch, kind):
    plan_path, plan = make_plan(tmp_path, monkeypatch)
    summary = shard_summary(plan)
    if kind == "dataset":
        summary["dataset_revision"] = "changed"
    elif kind == "commit":
        summary["results"][0]["upstream_commit"] = "0" * 40
    elif kind == "optimization":
        summary["optimization"] = "O3"
    else:
        save_summary(tmp_path / "inputs/duplicate/batch-summary.json", summary)
    save_summary(tmp_path / "inputs/original/batch-summary.json", summary)
    with pytest.raises(ValueError, match="MISMATCH|DUPLICATE"):
        BENCH.aggregate(
            argparse.Namespace(plan=plan_path, source=tmp_path / "inputs", output=tmp_path / "r")
        )
    assert not (tmp_path / "r/summary.json").exists()


def test_archive_omits_cancelled_builds_and_verifies_included_evidence(tmp_path):
    source = tmp_path / "evidence"
    for path in (
        "task/result.json",
        "task/control/reference.patch",
        "execution-source/scripts/qualify_cpp_batch.py",
        "task/baseline-build/object.o",
        "task/control/native-source/binary",
        "profile/ccache/object",
        "task/repository/.git",
    ):
        target = source / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path + "\n")
    output = tmp_path / "archive/evidence.tar.gz"
    BENCH.pack(argparse.Namespace(source=source, output=output))
    with tarfile.open(output) as archive:
        names = set(archive.getnames())
        assert names == {
            "task/result.json",
            "task/control/reference.patch",
            "execution-source/scripts/qualify_cpp_batch.py",
            "archive-manifest.json",
        }
        manifest = json.load(archive.extractfile("archive-manifest.json"))
        for entry in manifest["files"]:
            payload = archive.extractfile(entry["path"]).read()
            assert hashlib.sha256(payload).hexdigest() == entry["sha256"]
    assert output.with_name(output.name + ".sha256").read_text().split()[0] == BENCH.sha(output)
    assert not output.with_name(output.name + ".partial").exists()
    with pytest.raises(FileExistsError):
        BENCH.pack(argparse.Namespace(source=source, output=output))


def test_deadline_allows_one_cleanup_signal_without_reporting_success(tmp_path):
    command = (
        "import signal,time,sys\n"
        "def stop(*_):\n print('cleanup',flush=True); time.sleep(.2); sys.exit(0)\n"
        "signal.signal(signal.SIGTERM,stop)\nprint('ready',flush=True)\ntime.sleep(10)"
    )
    output = tmp_path / "deadline"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/benchmark_resources.py"),
            "--output",
            str(output),
            "--timeout",
            ".4",
            "--kill-grace-seconds",
            "1",
            "--",
            sys.executable,
            "-c",
            command,
        ],
        capture_output=True,
        timeout=5,
    )
    report = json.loads((output / "telemetry.json").read_text())
    assert result.returncode == 124 and report["status"] == "timeout"
    assert report["returncode"] == 0
    assert (output / "stdout.log").read_text().count("cleanup") == 1


def test_output_overflow_is_a_bounded_failure(tmp_path):
    output = tmp_path / "overflow"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/benchmark_resources.py"),
            "--output",
            str(output),
            "--timeout",
            "5",
            "--log-limit-bytes",
            "1024",
            "--",
            sys.executable,
            "-c",
            "import os; os.write(1,b'x'*100000)",
        ],
        capture_output=True,
        timeout=5,
    )
    report = json.loads((output / "telemetry.json").read_text())
    assert result.returncode == 125 and report["status"] == "output_limit_exceeded"
    assert (output / "stdout.log").stat().st_size == 1024
    assert report["logs_truncated"] is True


@pytest.mark.skipif(not Path("/proc/self/stat").exists(), reason="Linux /proc measurement")
def test_process_tree_rss_includes_child_in_new_session(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "benchmark_resources", ROOT / "scripts/benchmark_resources.py"
    )
    resources = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(resources)
    # Child publishes readiness only after touching its memory; no timing guess.
    child_code = (
        "import os,time; allocation=bytearray(80*1024*1024); "
        "print(os.getpid(),flush=True); time.sleep(10)"
    )
    parent_code = (
        "import subprocess,sys; "
        f"child=subprocess.Popen([sys.executable,'-c',{child_code!r}], "
        "start_new_session=True); child.wait()"
    )
    parent = subprocess.Popen(
        [sys.executable, "-c", parent_code],
        stdout=subprocess.PIPE,
        start_new_session=True,
        text=True,
    )
    child_pid = None
    try:
        child_pid = int(parent.stdout.readline().strip())
        assert os.getpgid(child_pid) != parent.pid
        observed = resources.sample(tmp_path, parent.pid)
        assert observed["process_tree_rss_bytes"] > 80 * 1024 * 1024
        assert observed["process_tree_rss_bytes"] - observed["process_group_rss_bytes"] > (
            70 * 1024 * 1024
        )
    finally:
        if child_pid is not None:
            os.kill(child_pid, signal.SIGTERM)
        parent.wait(timeout=5)
        parent.stdout.close()
