"""初始化受信任示例，并从本地真实 commit/image 生成 Task v2。"""

import argparse
import json
import os
import tempfile
from pathlib import Path

import yaml

from repropatch.task import CTEST_TEMPLATE, Task, inspect_image, resolve_task
from repropatch.workspace import git


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-task", type=Path, help="写入锁定后的 Task v2")
    parser.add_argument(
        "--image", default="repropatch-cpp:0.1", help="已存在的本地镜像，不会自动拉取"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    repo = root / "examples/cpp-bugs"
    if not (repo / ".git").exists():
        git(repo, "init", "-b", "main")
        git(repo, "add", "CMakeLists.txt", "src", "tests")
        git(
            repo,
            "-c",
            "user.name=ReproPatch Example",
            "-c",
            "user.email=example@localhost",
            "commit",
            "-m",
            "初始化最大值计算缺陷示例",
        )
    commit = git(repo, "rev-parse", "HEAD").strip()
    identity = {"repository": str(repo), "commit": commit}
    if args.write_task is not None:
        path = args.write_task.resolve()
        image = inspect_image(args.image)
        raw = {
            "version": 2,
            "id": "negative-maximum",
            "repository": {"path": os.path.relpath(repo, path.parent), "commit": commit},
            "environment": {"image": image.image_id},
            "bug": {
                "description": "修复 maximum_sample 对非空全负输入返回 0 的错误，"
                "保留空输入与完整 int 值域的行为。"
            },
            "commands": {
                "configure": ["cmake", "-S", "/src", "-B", "/build", "-DCMAKE_BUILD_TYPE=Debug"],
                "build": ["cmake", "--build", "/build", "--parallel", "2"],
                "reproduce": list(CTEST_TEMPLATE),
                "verify": list(CTEST_TEMPLATE),
            },
            "tests": {
                "fail_to_pass": [
                    {
                        "name": "negative_values",
                        "expected_exit_code": 8,
                        "output_contains": "expected -3, got 0",
                    }
                ],
                "pass_to_pass": ["positive_values", "empty_values", "mixed_values"],
                "protected_paths": ["CMakeLists.txt", "tests/"],
            },
            "files": {
                "readable": ["CMakeLists.txt", "src/", "tests/"],
                "editable": ["src/stats.cpp"],
            },
            "budget": {"max_steps": 12},
            "workspace": {"root": os.path.relpath(root / ".repropatch/workspaces", path.parent)},
            "outputs": {"root": os.path.relpath(root / ".repropatch/runs", path.parent)},
        }
        source = yaml.safe_dump(raw, allow_unicode=True, sort_keys=False).encode("utf-8")
        task = Task.from_dict(raw, path.parent, source_bytes=source)
        resolved = resolve_task(task, image_identity=image)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(source)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        identity.update(image_id=image.image_id, task_sha256=resolved.task_sha256, task=str(path))
    print(json.dumps(identity, ensure_ascii=False))


if __name__ == "__main__":
    main()
