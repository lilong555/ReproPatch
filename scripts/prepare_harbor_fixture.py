"""生成无模型 Harbor fixture 配置；作业仍由原生 harbor CLI 启动。"""

import argparse
import hashlib
import io
import json
import re
import subprocess
import tarfile
from pathlib import Path

import yaml

from repropatch.task import Task

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task", type=Path, default=ROOT / "examples/tasks/negative-maximum.v2.yaml"
    )
    parser.add_argument(
        "--fixture-patch",
        type=Path,
        default=ROOT / "examples/patches/negative-maximum.correct.patch",
    )
    parser.add_argument(
        "--producer-image", required=True, help="已准备且包含 Git、Python 的本地 producer 镜像 tag"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._/:-]{0,199}", args.producer_image):
        parser.error("producer 镜像 tag 不合法")
    task = Task.load(args.task)
    if task.id not in {"negative-maximum", "negative-maximum-live"}:
        parser.error("此入口只准备已审核的自有 fixture，不能代替真实任务适配")
    identity = (
        subprocess.check_output(
            ["docker", "image", "inspect", args.producer_image, "--format", "{{.Id}}"], timeout=15
        )
        .decode()
        .strip()
    )
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    directory = output / "tasks" / task.id
    for name in ("environment", "solution", "tests"):
        (directory / name).mkdir(parents=True)
    # 只导出固定提交的文件，不复制宿主 Git 配置、历史或凭据。
    raw = subprocess.check_output(
        ["git", "-C", str(task.repository), "archive", task.revision], timeout=30
    )
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        archive.extractall(directory / "environment/source", filter="data")
    (directory / "environment/Dockerfile").write_text(
        f"FROM {args.producer_image}\nUSER root\nENV HOME=/tmp\n"
        "COPY source /workspace\nWORKDIR /workspace\n"
        "RUN git -c core.hooksPath=/dev/null init && git add . && "
        "git -c user.name=Fixture -c user.email=fixture@example.invalid "
        "-c commit.gpgsign=false commit -qm baseline\n"
    )
    (directory / "instruction.md").write_text(
        task.prompt + "\n将源码差异导出到 /logs/artifacts/candidate.patch。\n"
    )
    (directory / "task.toml").write_text(
        'schema_version = "1.0"\n'
        'artifacts = [{source = "/logs/artifacts/candidate.patch", '
        'destination = "candidate.patch"}]\n'
        f'[task]\nname = "repropatch/{task.id}"\n'
        '[agent]\ntimeout_sec = 30.0\nnetwork_mode = "public"\n'
        "[environment]\ncpus = 2\nmemory_mb = 2048\n"
    )
    (directory / "tests/test.sh").write_text(
        "#!/bin/bash\necho '本任务仅生成补丁，Harbor 验证必须关闭' >&2\nexit 97\n"
    )
    patch = args.fixture_patch.read_bytes()
    (directory / "solution/producer.patch").write_bytes(patch)
    (directory / "solution/solve.sh").write_text(
        "#!/bin/bash\nset -eu\ncd /workspace\ngit apply /solution/producer.patch\n"
        "mkdir -p /logs/artifacts\n"
        "git diff --binary --no-ext-diff > /logs/artifacts/candidate.patch\n"
    )
    job = {
        "job_name": "fixture-bridge",
        "jobs_dir": str(output / "jobs"),
        "n_attempts": 1,
        "n_concurrent_trials": 1,
        "retry": {"max_retries": 0},
        "environment": {"type": "docker", "delete": True, "force_build": True},
        "verifier": {"disable": True},
        "agents": [{"name": "oracle"}],
        "tasks": [{"path": str(directory)}],
    }
    (output / "job.yaml").write_text(yaml.safe_dump(job, sort_keys=False))
    manifest = {
        "schema_version": 1,
        "scope": "deterministic_fixture_only",
        "paid_model_requests": 0,
        "harbor_version": "0.24.0",
        "producer_image_id": identity,
        "producer_image_tag": args.producer_image,
        "base_commit": task.revision,
        "task_yaml_sha256": hashlib.sha256(task.source_bytes).hexdigest(),
        "fixture_patch_sha256": hashlib.sha256(patch).hexdigest(),
        "producer_user": "root",
        "producer_network": "public",
        "strict_same_model_comparison_ready": False,
    }
    (output / "preparation.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(output / "job.yaml")


if __name__ == "__main__":
    main()
