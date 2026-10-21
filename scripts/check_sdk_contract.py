"""在安装 agent extra 的 Python 中执行离线公开 API 契约，保存版本与原始证据。"""

import argparse
import hashlib
import json
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="尚不存在的证据目录")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output or root / ".repropatch/sdk-gates" / uuid.uuid4().hex
    output = output.resolve()
    output.mkdir(parents=True)
    record = {"status": "error", "started_at": datetime.now(UTC).isoformat(), "commands": []}
    result_code = 1
    try:
        from repropatch import __version__
        from repropatch.models import SDK_VERSIONS, prepare_sdk

        prepare_sdk()
        record.update(
            product_version=__version__,
            python=sys.version.split()[0],
            packages={
                name: version(name) for name in (*SDK_VERSIONS, "httpx2", "pydantic", "pytest")
            },
            real_model_verified=False,
            network="socket 连接由测试夹具拒绝；HTTP 仅使用 MockTransport",
        )
        paths = [
            path
            for directory in ("src/repropatch", "tests", "scripts", "requirements")
            for path in (root / directory).rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        ] + [root / "pyproject.toml", root / "uv.lock"]
        manifest = {
            str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)
        }
        (output / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        argv = [
            sys.executable,
            "-I",
            "-m",
            "pytest",
            str(root / "tests"),
            "-m",
            "sdk and not docker",
            "-v",
            f"--junitxml={output / 'results.xml'}",
        ]
        with (output / "tests.log").open("wb") as stream:
            result = subprocess.run(
                argv, cwd=root, stdout=stream, stderr=subprocess.STDOUT, timeout=300
            )
        record["commands"].append({"argv": argv, "returncode": result.returncode})
        cases = list(ET.parse(output / "results.xml").iter("testcase"))
        if (
            result.returncode
            or not {
                "test_native_items_roundtrip_and_public_hook_order",
                "test_last_turn_tools_execute_and_patch_is_independently_verified",
                "test_six_tools_and_policy_feedback_use_native_items",
            }
            <= {case.get("name") for case in cases}
            or any(child.tag in {"skipped", "error", "failure"} for case in cases for child in case)
        ):
            raise RuntimeError("SDK 基础与生产契约必须实际通过，不能失败或跳过")
        record.update(status="passed", tests_passed=len(cases), tests_failed=0, tests_skipped=0)
        result_code = 0
    except Exception as exc:
        # 只记录分类，避免将供应商异常内容写入交付证据。
        record["error_type"] = type(exc).__name__
    record["finished_at"] = datetime.now(UTC).isoformat()
    (output / "summary.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(record, indent=2, ensure_ascii=False))
    return result_code


if __name__ == "__main__":
    raise SystemExit(main())
