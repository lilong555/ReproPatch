"""从 Actions 原始归档提取资格失败诊断，模型请求数为零。"""

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import tarfile
from pathlib import Path


def inspect(entry, output):
    run, instance = entry["run_id"], entry["instance_id"]
    if type(run) is not int or not re.fullmatch(r"[\w.-]+__[\w.-]+-\d+", instance):
        raise ValueError("QUALIFICATION_SOURCE_INVALID")
    name = f"cross-evidence-{run}-{instance}"
    directory = output / name
    subprocess.run(
        [
            "gh",
            "run",
            "download",
            str(run),
            "--repo",
            os.environ["GITHUB_REPOSITORY"],
            "--name",
            name,
            "--dir",
            str(directory),
        ],
        check=True,
        timeout=600,
    )
    path = directory / "cross-evidence.tar.gz"
    digest = hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
    if path.with_suffix(".gz.sha256").read_text().split()[0] != digest:
        raise ValueError("ARCHIVE_CHECKSUM_MISMATCH")
    if entry.get("finalize_task"):
        from finalize_qualification_task import finalize

        finalize(entry, path, output / "finalized")
    logs = {}
    with tarfile.open(path) as archive:
        result = json.load(archive.extractfile(instance + "/result.json"))
        for member in archive.getmembers():
            if not member.isfile() or not member.name.startswith(instance + "/"):
                continue
            if member.name.endswith((".log", "native-results.json")):
                content = archive.extractfile(member).read().decode(errors="replace")
                lines = content.splitlines()
                errors = [
                    line
                    for line in lines
                    if re.search(
                        r"error:|fatal error|FAILED|failed|CMake Error|not found|Permission denied",
                        line,
                        re.IGNORECASE,
                    )
                ]
                logs[member.name] = {
                    "errors": errors[:35],
                    "tail": "\n".join(lines[-35:])[-12000:],
                }
    return {"source": entry, "archive_sha256": digest, "result": result, "logs": logs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text())
    if request.get("model_requests") != 0 or not 1 <= len(request["sources"]) <= 30:
        raise ValueError("ZERO_REQUEST_DIAGNOSTIC_REQUIRED")
    args.output.mkdir(parents=True, exist_ok=False)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        reports = list(pool.map(lambda entry: inspect(entry, args.output), request["sources"]))
    result = {"model_requests": 0, "reports": reports}
    (args.output / "diagnostics.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    for report in reports:
        record = report["result"]
        print(
            json.dumps(
                {key: record.get(key) for key in ("instance_id", "status", "diagnostic")},
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
