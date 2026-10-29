"""在 Actions 中恢复完整资格证据并冻结正式协议，模型请求数为零。"""

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

from check_native_cpp_candidate import restore_repository
from cross_repo_inputs import extract_verified
from freeze_cross_repo import freeze
from qualify_cpp_batch import save, sha
from summarize_candidate_qualification import inspect_archive

ROOT = Path(__file__).resolve().parents[1]


def validate_request(request, registry):
    sources = request.get("qualification_sources", [])
    selected = registry["instances"]
    if (
        request.get("model_requests") != 0
        or len(selected) != 30
        or len(sources) != 30
        or {row["instance_id"] for row in sources} != set(selected)
        or len(set(request.get("repeat_instances", []))) != 6
        or not set(request["repeat_instances"]) <= set(selected)
        or not re.fullmatch(r"[0-9a-f]{40}", request.get("source_commit", ""))
    ):
        raise ValueError("COMPLETE_ZERO_REQUEST_FREEZE_REQUIRED")
    for row in sources:
        run = row["run_id"]
        if (
            type(run) is not int
            or run <= 0
            or row["artifact"] != f"cross-evidence-{run}-{row['instance_id']}"
            or not re.fullmatch(r"[0-9a-f]{64}", row.get("archive_sha256", ""))
        ):
            raise ValueError("FROZEN_QUALIFICATION_SOURCE_REQUIRED")
    for key in ("ci_run", "calibration_run", "development_run"):
        if type(request.get(key)) is not int or request[key] <= 0:
            raise ValueError("FROZEN_PREREQUISITE_RUN_REQUIRED")


def download(run, name, directory, repository):
    subprocess.run(
        [
            "gh",
            "run",
            "download",
            str(run),
            "--repo",
            repository,
            "--name",
            name,
            "--dir",
            str(directory),
        ],
        check=True,
        timeout=600,
    )


def restore_source(entry, registry, output, repository):
    artifact = output / "archives" / entry["artifact"]
    download(entry["run_id"], entry["artifact"], artifact, repository)
    archive = artifact / "cross-evidence.tar.gz"
    if sha(archive) != entry["archive_sha256"]:
        raise ValueError("FROZEN_QUALIFICATION_ARCHIVE_MISMATCH")
    environment = registry.get("task_environments", {}).get(
        entry["instance_id"], {"image": registry["image"], "image_id": registry["image_id"]}
    )
    rows = inspect_archive(archive, environment["image_id"])
    if len(rows) != 1 or rows[0]["instance_id"] != entry["instance_id"] or not rows[0]["eligible"]:
        raise ValueError("QUALIFICATION_EVIDENCE_INCOMPLETE")
    unpacked = artifact / "unpacked"
    extract_verified(archive, unpacked, entry["archive_sha256"])
    directory = output / "qualification" / entry["instance_id"]
    directory.parent.mkdir(exist_ok=True)
    shutil.move(str(unpacked / entry["instance_id"]), directory)
    result = json.loads((directory / "result.json").read_text())
    restore_repository(directory, result, directory / "repository")
    return rows[0]


def run(request_path, output):
    request = json.loads(request_path.read_text())
    registry = json.loads((ROOT / "benchmarks/cross-repo/formal-preparation.json").read_text())
    validate_request(request, registry)
    repository = os.environ["GITHUB_REPOSITORY"]
    ci = json.loads(
        subprocess.check_output(
            ["gh", "api", f"repos/{repository}/actions/runs/{request['ci_run']}"], timeout=60
        )
    )
    if (
        ci["name"] != "CI"
        or ci["conclusion"] != "success"
        or ci["head_sha"] != request["source_commit"]
    ):
        raise ValueError("EXACT_SOURCE_CI_REQUIRED")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", request["source_commit"], "HEAD"], check=True
    )
    output.mkdir(parents=True, exist_ok=False)
    save(output / "request.json", request)
    # 资格归档独立下载、核验与恢复，共用已固定的测试合同。
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        jobs = [
            pool.submit(restore_source, entry, registry, output, repository)
            for entry in request["qualification_sources"]
        ]
        rows = [job.result() for job in jobs]
    calibration = output / "calibration"
    development = output / "development"
    download(
        request["calibration_run"],
        f"cross-network-calibration-{request['calibration_run']}",
        calibration,
        repository,
    )
    download(
        request["development_run"],
        f"cross-results-{request['development_run']}",
        development,
        repository,
    )
    protocol = output / "formal-protocol.json"
    value = freeze(
        SimpleNamespace(
            phase="formal",
            instances=",".join(registry["instances"]),
            qualification=output / "qualification",
            archives=output / "archives",
            calibration=calibration / "calibration.json",
            calibration_run=request["calibration_run"],
            qualification_run=sorted({row["run_id"] for row in request["qualification_sources"]}),
            image=registry["image"],
            image_id=registry["image_id"],
            ci_run=request["ci_run"],
            source_commit=request["source_commit"],
            output=protocol,
            development_results=development / "results.json",
            development_run=request["development_run"],
            selection_review=ROOT / "benchmarks/cross-repo/formal-selection-review.json",
            repeat_instances=",".join(request["repeat_instances"]),
            formal_protocol=None,
            preparation_failures=None,
            prior_attempts=None,
            max_parallel=3,
            prior_rescore_run=None,
        )
    )
    result = {
        "status": "FROZEN",
        "model_requests": 0,
        "tasks": len(value["tasks"]),
        "attempts": len(value["attempts"]),
        "formal_request_cap": value["formal_request_cap"],
        "max_cpa_parallel": value["max_parallel"],
        "protocol_sha256": sha(protocol),
        "request_sha256": sha(request_path),
        "qualification": rows,
    }
    save(output / "freeze-summary.json", result)
    print(json.dumps({key: result[key] for key in ("status", "tasks", "attempts")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    run(arguments.request, arguments.output.resolve())
