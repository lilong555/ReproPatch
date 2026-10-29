"""复用同镜像的完整原生验收证据，登记小写任务标签。"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from check_native_cpp_candidate import restore_repository
from cpp_native_adapter import source_manifest
from cpp_sources import encoded, load_records
from cross_repo_inputs import extract_verified
from qualify_cpp_batch import save, sha
from qualify_cross_repo import manifest, write_task
from verify_qualification_evidence import required_task_artifacts, verify_tree


def register(directory, record, image_id, archive_sha):
    directory = directory.resolve()
    result_file = directory / "result.json"
    original = result_file.read_bytes()
    result = json.loads(original)
    if (
        result["instance_id"] != record["instance_id"]
        or result["image_id"] != image_id
        or result["backend"] != "docker"
        or result["optimization"] != "O3"
        or result["qualification_policy"] != "baseline-native-v1"
        or result["status"] != "PREPARATION_FAILED"
        or not result.get("diagnostic", "").startswith("id: 期望小写任务标签")
        or result["phases"]["baseline"]["status"] != "TESTS_FAILED"
        or result["phases"]["native_oracle"]["status"] != "PASSED"
        or result.get("native_oracle", {}).get("passed") is not True
        or result.get("cleanup", {}).get("status") != "SUCCEEDED"
        or not result.get("f2p")
        or not result.get("p2p")
        or set(result["f2p"] + result["p2p"]) != set(result["required_tests"])
    ):
        raise ValueError("NATIVE_QUALIFICATION_REUSE_IDENTITY_MISMATCH")
    stored = json.loads((directory / "control/record.json").read_text())
    if encoded(stored) != encoded(record):
        raise ValueError("NATIVE_QUALIFICATION_REUSE_RECORD_MISMATCH")
    inventory = json.loads((directory / "manifest.json").read_text())
    required = required_task_artifacts({**result, "status": "QUALIFIED"}) - {"task.yaml"}
    stored_inventory = {
        name: value for name, value in inventory.items() if not name.startswith("repository/")
    }
    stored_required = {name for name in required if not name.startswith("repository/")}
    if verify_tree(directory, stored_inventory, stored_required):
        raise ValueError("NATIVE_QUALIFICATION_REUSE_EVIDENCE_INCOMPLETE")
    source = directory / "repository"
    restored = directory.parent / (directory.name + "-registration-repository")
    restore_repository(directory, result, restored)
    expected = json.loads((directory / "control/prepared-source-manifest.json").read_text())
    if source_manifest(restored) != expected:
        raise ValueError("NATIVE_QUALIFICATION_REUSE_PREPARED_SOURCE_MISMATCH")
    if source.exists():
        shutil.rmtree(source)
    restored.rename(source)
    if verify_tree(directory, inventory, required):
        raise ValueError("NATIVE_QUALIFICATION_REUSE_RESTORED_EVIDENCE_INCOMPLETE")
    (directory / "original-result.json").write_bytes(original)
    task = write_task(
        record, source, directory, image_id, result["configuration"], result["f2p"], result["p2p"]
    )
    result.pop("failure_type", None)
    result.pop("diagnostic", None)
    result.update(
        status="QUALIFIED",
        task_path=str(task),
        task_file_sha256=sha(task),
        registration={
            "source_archive_sha256": archive_sha,
            "original_result_sha256": hashlib.sha256(original).hexdigest(),
            "registrar_sha256": sha(Path(__file__)),
            "model_requests": 0,
            "native_builds": 0,
        },
    )
    save(result_file, result)
    manifest(directory)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output = args.output.resolve()
    plan = json.loads(args.plan.read_text())
    entry = plan.get("reusable_qualifications", {}).get(args.instance)
    if not entry or entry["image_id"] != args.image_id:
        return
    archive_directory = args.output.parent / "reuse-input"
    subprocess.run(
        [
            "gh",
            "run",
            "download",
            str(entry["run_id"]),
            "--repo",
            os.environ["GITHUB_REPOSITORY"],
            "--name",
            entry["artifact"],
            "--dir",
            str(archive_directory),
        ],
        check=True,
    )
    extract_verified(
        archive_directory / "cross-evidence.tar.gz", args.output, entry["archive_sha256"]
    )
    # 原归档清单保留为来源证据，新批次生成独立的打包清单。
    (args.output / "archive-manifest.json").rename(args.output / "source-archive-manifest.json")
    records = {row["instance_id"]: row for row in load_records(args.dataset)}
    result = register(
        args.output / args.instance, records[args.instance], args.image_id, entry["archive_sha256"]
    )
    save(
        args.output / "batch-summary.json",
        {"schema_version": 2, "model_requests": 0, "tasks": [result]},
    )
    with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
        stream.write("reused=true\n")


if __name__ == "__main__":
    main()
