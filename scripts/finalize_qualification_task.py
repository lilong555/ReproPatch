"""复用已通过的原生测试证据，完成超长问题描述的 Task 导出。"""

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

from actions_benchmark import pack
from check_native_cpp_candidate import restore_repository
from cpp_native_adapter import source_manifest
from cross_repo_inputs import extract_verified
from qualify_cpp_batch import save, sha
from qualify_cross_repo import manifest, write_task
from summarize_candidate_qualification import qualification_gate_errors

ROOT = Path(__file__).resolve().parents[1]


def finalize(entry, archive, output):
    instance = entry["instance_id"]
    extract_verified(archive, output, entry["archive_sha256"])
    directory = output / instance
    result = json.loads((directory / "result.json").read_text())
    original_sha = sha(directory / "result.json")
    if (
        result["status"] != "PREPARATION_FAILED"
        or not result.get("diagnostic", "").startswith("bug.description:")
        or result["backend"] != "docker"
        or result["model_requests"] != 0
    ):
        raise ValueError("COMPLETED_NATIVE_QUALIFICATION_REQUIRED")
    source = directory / "repository"
    restore_repository(directory, result, source)
    if source_manifest(source) != json.loads(
        (directory / "control/prepared-source-manifest.json").read_text()
    ):
        raise ValueError("PREPARED_SOURCE_CHANGED")
    contract = json.loads((source / "repropatch-native/contract.json").read_text())
    native = json.loads((directory / "native-oracle-native-results.json").read_text())
    single_path = directory / "single-header-native-results.json"
    errors = qualification_gate_errors(
        result,
        contract,
        native,
        json.loads(single_path.read_text()) if single_path.exists() else None,
    )
    if errors:
        raise ValueError("NATIVE_QUALIFICATION_INCOMPLETE:" + ",".join(errors))
    save(directory / "control/source-result.json", result)
    record = json.loads((directory / "control/record.json").read_text())
    task = write_task(
        record,
        source,
        directory,
        result["image_id"],
        result["configuration"],
        result["f2p"],
        result["p2p"],
    )
    result.update(
        status="QUALIFIED",
        task_path=str(task),
        task_file_sha256=sha(task),
        finalization={
            "operation": "TASK_DESCRIPTION_EXPORT",
            "source_run_id": entry["run_id"],
            "source_archive_sha256": entry["archive_sha256"],
            "source_result_sha256": original_sha,
            "native_tests_reused": True,
            "model_requests": 0,
            "prepared_source_unchanged": True,
        },
    )
    for key in ("failure_type", "diagnostic"):
        result.pop(key, None)
    save(directory / "result.json", result)
    manifest(directory)
    implementations = {}
    for name in ("qualify_cross_repo.py", "finalize_qualification_task.py"):
        target = output / "finalization-code" / name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes((ROOT / "scripts" / name).read_bytes())
        implementations[name] = sha(target)
    save(output / "finalization-source-manifest.json", implementations)
    (output / "archive-manifest.json").rename(output / "source-archive-manifest.json")
    pack(SimpleNamespace(source=output, output=output.parent / "cross-evidence.tar.gz"))
    inputs = output.parent / "finalization-inputs"
    subprocess.run(
        [
            "gh",
            "run",
            "download",
            str(entry["run_id"]),
            "--repo",
            os.environ["GITHUB_REPOSITORY"],
            "--name",
            f"cross-inputs-{entry['run_id']}",
            "--dir",
            str(inputs),
        ],
        check=True,
        timeout=600,
    )
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
        stream.write("finalized_instance=" + instance + "\n")
    return result
