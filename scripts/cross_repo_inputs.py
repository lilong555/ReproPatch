"""恢复已冻结的 Actions 资格归档、固定工具链与原生 CLI。"""

import argparse
import base64
import hashlib
import io
import json
import os
import subprocess
import tarfile
import urllib.request
from pathlib import Path

from cross_repo_campaign import task_environment, validate_protocol
from qualify_cpp_batch import sha

ROOT = Path(__file__).resolve().parents[1]


def extract_verified(archive, destination, expected_sha):
    if sha(archive) != expected_sha:
        raise ValueError("CROSS_QUALIFICATION_ARCHIVE_MISMATCH")
    with tarfile.open(archive) as data:
        inventory = json.load(data.extractfile("archive-manifest.json"))
        for row in inventory["files"]:
            stream = data.extractfile(row["path"])
            content = stream.read() if stream else b""
            if (
                len(content) != row["size_bytes"]
                or hashlib.sha256(content).hexdigest() != row["sha256"]
            ):
                raise ValueError("CROSS_ARCHIVE_MEMBER_IDENTITY_MISMATCH")
        data.extractall(destination, filter="data")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--instance", required=True)
    args = parser.parse_args()
    p = json.loads(args.protocol.read_text())
    validate_protocol(p)
    if args.instance not in p["tasks"]:
        parser.error("实例须在冻结协议中登记")
    repository = os.environ["GITHUB_REPOSITORY"]
    entry = next(a for a in p["qualification_archives"] if args.instance in a["instances"])
    directory = ROOT / ".repropatch/cross-archive-input"
    subprocess.run(
        [
            "gh",
            "run",
            "download",
            str(entry["run_id"]),
            "--repo",
            repository,
            "--name",
            entry["artifact"],
            "--dir",
            str(directory),
        ],
        check=True,
    )
    extract_verified(
        directory / "cross-evidence.tar.gz",
        ROOT / ".repropatch/cross-qualification",
        entry["sha256"],
    )
    subprocess.run(
        [
            "gh",
            "run",
            "download",
            str(entry["run_id"]),
            "--repo",
            repository,
            "--name",
            f"cross-inputs-{entry['run_id']}",
            "--dir",
            str(ROOT / ".repropatch"),
        ],
        check=True,
    )
    subprocess.run(["docker", "pull", task_environment(p, args.instance)["image"]], check=True)
    mini = ROOT / ".repropatch/mini-source"
    subprocess.run(["git", "init", "--template=", "-q", str(mini)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(mini),
            "fetch",
            "--depth=1",
            "https://github.com/SWE-agent/mini-swe-agent.git",
            p["mini_commit"],
        ],
        check=True,
    )
    subprocess.run(["git", "-C", str(mini), "checkout", "--detach", "FETCH_HEAD"], check=True)
    environment = ROOT / ".repropatch/mini-env"
    subprocess.run(["python", "-m", "venv", str(environment)], check=True)
    subprocess.run(
        [
            str(environment / "bin/python"),
            "-m",
            "pip",
            "install",
            "-c",
            "requirements/formal-mini.txt",
            "-e",
            ".",
            "litellm==1.106.1",
            "httpx2==2.16.0",
            "mcp==2.3.0",
            "mcp-types==2.3.0",
            "rich",
            "jinja2",
            "tenacity",
            "python-dotenv",
            "platformdirs",
        ],
        cwd=ROOT,
        check=True,
    )
    with urllib.request.urlopen(p["codex_tarball"], timeout=120) as response:
        content = response.read()
    if (
        "sha512-" + base64.b64encode(hashlib.sha512(content).digest()).decode()
        != p["codex_tarball_integrity"]
    ):
        raise ValueError("CODEX_TARBALL_IDENTITY_MISMATCH")
    codex = ROOT / ".repropatch/codex"
    codex.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(content)) as archive:
        archive.extractall(codex, filter="data")
    binary = ROOT / p["codex_binary"]
    if (
        sha(binary) != p["codex_sha256"]
        or sha(binary.with_name("codex-code-mode-host")) != p["code_host_sha256"]
    ):
        raise ValueError("CODEX_BINARY_IDENTITY_MISMATCH")


if __name__ == "__main__":
    main()
