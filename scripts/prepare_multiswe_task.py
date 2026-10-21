"""为已审查的 Catch2 实例准备 Task v2；不运行 Agent 或改写官方 Oracle。"""

import argparse
import hashlib
import io
import json
import os
import subprocess
import tarfile
from pathlib import Path

import yaml
from screen_multiswe import screen

from repropatch.task import IMAGE_ID, Task

ROOT = Path(__file__).resolve().parents[1]


def git(repository, *args):
    env = dict(
        os.environ,
        GIT_AUTHOR_DATE="2026-10-21T00:00:00Z",
        GIT_COMMITTER_DATE="2026-10-21T00:00:00Z",
    )
    return subprocess.check_output(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.name=ReproPatch Benchmark",
            "-c",
            "user.email=benchmark@example.invalid",
            *args,
        ],
        env=env,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--instance", default="catchorg__Catch2-2723")
    parser.add_argument("--image", required=True)
    parser.add_argument(
        "--inventory", type=Path, required=True, help="相同固定环境实际导出的 CTest JSON inventory"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.instance != "catchorg__Catch2-2723":
        parser.error("仅支持已审查的 Catch2-2723 准备布局；其他实例须独立审查")
    dataset = args.dataset / "cpp" if (args.dataset / "cpp").is_dir() else args.dataset
    matches = [
        (json.loads(line), path.name, number)
        for path in dataset.glob("*_dataset.jsonl")
        for number, line in enumerate(path.read_text().splitlines(), 1)
        if line.strip() and json.loads(line).get("instance_id") == args.instance
    ]
    if len(matches) != 1:
        parser.error("实例缺失或重复")
    record, filename, line = matches[0]
    review = screen(record, filename, line)
    if review["status"] != "candidate_pending_runtime":
        parser.error("实例尚未满足静态准备条件")
    if not IMAGE_ID.fullmatch(args.image):
        parser.error("需要已经核验并移除解答材料的本地固定 image ID")
    inventory_bytes = args.inventory.read_bytes()
    inventory = json.loads(inventory_bytes)
    names = [item["name"] for item in inventory["tests"]]
    mapped = {name.lower(): name for name in names}
    if len(mapped) != len(names):
        parser.error("CTest 名称归一化存在冲突，拒绝猜测身份")
    f2p = review["test_phase_f2p"]
    missing_f2p = [name for name in f2p if name not in mapped]
    configure_probes = [name for name in review["test_phase_p2p"] if name not in mapped]
    if missing_f2p or any(not name.startswith("have_flag_") for name in configure_probes):
        parser.error("缺少真正的 CTest 回归测试，不能丢弃后继续")
    p2p = [name for name in review["test_phase_p2p"] if name in mapped]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    repository = output / "repository"
    repository.mkdir()
    upstream = args.repository.resolve()
    raw = git(upstream, "archive", record["base"]["sha"])
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        archive.extractall(repository, filter="data")
    test_patch = output / "official-test.patch"
    test_patch.write_text(record["test_patch"])
    reference = output / "reference.patch"
    reference.write_text(record["fix_patch"])
    git(repository, "init", "-q")
    git(repository, "apply", "--", str(test_patch))
    git(repository, "add", ".")
    git(repository, "commit", "-qm", "固定原缺陷与官方测试输入")
    prepared = git(repository, "rev-parse", "HEAD").decode().strip()
    editable = sorted(
        p.relative_to(repository).as_posix()
        for p in (repository / "src/catch2").rglob("*")
        if p.is_file() and p.suffix in {".cpp", ".hpp", ".h"}
    )
    issues = "\n\n".join(
        i["title"] + "\n" + (i.get("body") or "") for i in record["resolved_issues"]
    )
    task = {
        "version": 2,
        "id": args.instance.lower().replace("__", "-"),
        "repository": {"path": str(repository), "commit": prepared},
        "environment": {
            "image": args.image,
            "cpu_limit": 2.0,
            "memory_mib": 2048,
            "pids_limit": 128,
            "build_tmpfs_mib": 1024,
        },
        "bug": {"description": issues},
        "commands": {
            "configure": [
                "cmake",
                "-S",
                "/src",
                "-B",
                "/build",
                "-DCATCH_DEVELOPMENT_BUILD=ON",
                "-DCMAKE_BUILD_TYPE=Debug",
            ],
            "build": ["cmake", "--build", "/build", "--parallel", "2"],
            "reproduce": [
                "ctest",
                "--test-dir",
                "/build",
                "--output-on-failure",
                "--no-tests=error",
            ],
            "verify": ["ctest", "--test-dir", "/build", "--output-on-failure", "--no-tests=error"],
        },
        "tests": {
            "fail_to_pass": [
                {
                    "name": mapped[name],
                    "expected_exit_code": 8,
                    "output_contains": "The following tests FAILED:",
                }
                for name in f2p
            ],
            "pass_to_pass": [mapped[name] for name in p2p],
            "protected_paths": ["tests/", "CMakeLists.txt", "tools/"],
        },
        "files": {"readable": ["src/", "tests/", "CMakeLists.txt", "tools/"], "editable": editable},
        "budget": {
            "max_steps": 12,
            "max_tool_calls": 24,
            "wall_seconds": 1800,
            "verification_reserve_seconds": 900,
            "model_timeout_seconds": 45,
            "command_timeout_seconds": 300,
            "max_output_tokens": 2048,
        },
        "workspace": {"root": str(output / "workspaces")},
        "outputs": {"root": str(output / "runs")},
    }
    path = output / "task.yaml"
    path.write_text(yaml.safe_dump(task, sort_keys=False, allow_unicode=True))
    Task.load(path)
    provenance = {
        "schema_version": 1,
        "instance_id": args.instance,
        "dataset_revision": (args.dataset / "revision.txt").read_text().strip(),
        "upstream_commit": record["base"]["sha"],
        "prepared_commit": prepared,
        "test_patch_sha256": hashlib.sha256(test_patch.read_bytes()).hexdigest(),
        "reference_patch_sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
        "task_yaml_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "image": args.image,
        "adaptation": "prepared_test_commit",
        "regression_tests_visible_in_source": True,
        "ctest_inventory_sha256": hashlib.sha256(inventory_bytes).hexdigest(),
        "ctest_name_mapping": {name: mapped[name] for name in f2p + p2p},
        "official_configure_probes_not_ctest_nodes": configure_probes,
        "configure_probe_validation": (
            "必须由官方外部 Oracle 单独核验，不计为本 Harness 已执行的 CTest"
        ),
        "official_oracle_parity_verified": False,
        "runtime_verified": False,
        "model_attempts": 0,
        "editable_scope": "全部 src/catch2 生产 C++ 源码，并非参考补丁路径提示",
    }
    (output / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({"task": str(path), "prepared_commit": prepared}, ensure_ascii=False))


if __name__ == "__main__":
    main()
