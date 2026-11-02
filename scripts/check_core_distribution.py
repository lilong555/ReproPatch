"""以 core-only 环境核验最终 wheel 的真实 Docker 外部补丁验收。"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import UTC, datetime
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

VERSION = "0.4.0"
EXPECTED = {
    "correct": (0, "ACCEPTED", "VERIFICATION_PASSED"),
    "wrong": (1, "REJECTED", "F2P_FAILED"),
}
FIXTURE_FILES = (
    "scripts/init_example.py",
    "examples/cpp-bugs/CMakeLists.txt",
    "examples/cpp-bugs/src/stats.cpp",
    "examples/cpp-bugs/src/stats.hpp",
    "examples/cpp-bugs/tests/stats_test.cpp",
    "examples/patches/negative-maximum.correct.patch",
    "examples/patches/negative-maximum.wrong.patch",
)
INSTALLATION_PROBE = """
import importlib.util, json, sys, sysconfig
from importlib.metadata import distribution, distributions
from pathlib import Path
import repropatch
from repropatch.harness import implementation_sha256
installed = distribution('repropatch')
print(json.dumps({
    'version': installed.version,
    'module_version': repropatch.__version__,
    'module_origin': str(Path(repropatch.__file__).resolve()),
    'distribution_origin': str(installed.locate_file('repropatch/__init__.py').resolve()),
    'site_packages': sorted({sysconfig.get_path('purelib'), sysconfig.get_path('platlib')}),
    'origin': json.loads(installed.read_text('direct_url.json') or '{}'),
    'implementation_sha256': implementation_sha256(),
    'executable': sys.executable, 'python': sys.version,
    'prefix': sys.prefix, 'base_prefix': sys.base_prefix,
    'cwd': str(Path.cwd()), 'isolated': bool(sys.flags.isolated),
    'optional_modules': {name: importlib.util.find_spec(name) is not None
                         for name in ('agents', 'openai')},
    'distributions': sorted(({'name': item.metadata['Name'], 'version': item.version}
                             for item in distributions()), key=lambda item: item['name']),
}))
"""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fingerprint(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        require(not path.is_symlink(), f"证据包含链接：{path}")
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
        else:
            require(path.is_dir(), f"证据包含特殊文件：{path}")
    return result


def validate_installation(value, wheel):
    wheel = wheel.resolve(strict=True)
    require(wheel.is_file() and wheel.suffix == ".whl", "--wheel 须为最终 wheel 文件")
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    require(value["version"] == value["module_version"] == VERSION, "安装版本须为 0.4.0")
    require(value["isolated"] is True, "安装身份查询须使用 Python 隔离模式")
    require(value["prefix"] != value["base_prefix"], "门禁须由 core-only venv 的 Python 启动")
    require(
        value["optional_modules"] == {"agents": False, "openai": False},
        "core-only 环境须保持 agents、openai 模块缺省",
    )
    names = {row["name"].lower().replace("_", "-") for row in value["distributions"]}
    require(not {"openai-agents", "openai"} & names, "core-only 环境须保持 SDK 分发包缺省")
    origin = value["origin"]
    require(origin.get("dir_info", {}).get("editable", False) is False, "须使用非 editable 安装")
    require(origin.get("url") == wheel.as_uri(), "安装来源须为 --wheel 指定文件")
    archive = origin.get("archive_info", {})
    recorded = archive.get("hashes", {}).get("sha256") or archive.get("hash", "").removeprefix(
        "sha256="
    )
    require(recorded == digest, "安装来源 SHA256 与最终 wheel 不一致")
    module = Path(value["module_origin"]).resolve(strict=True)
    sites = [Path(path).resolve() for path in value["site_packages"]]
    require(
        module == Path(value["distribution_origin"]).resolve(strict=True)
        and module.name == "__init__.py"
        and module.parent.name == "repropatch"
        and any(module.is_relative_to(site) and site.name == "site-packages" for site in sites),
        "包须来自 venv 的非 editable site-packages",
    )
    payload = {}
    with zipfile.ZipFile(wheel) as source:
        require(len(source.namelist()) == len(set(source.namelist())), "wheel 文件身份重复")
        metadata = [name for name in source.namelist() if name.endswith(".dist-info/METADATA")]
        require(len(metadata) == 1, "wheel 须包含唯一分发身份")
        identity = BytesParser().parsebytes(source.read(metadata[0]))
        require(
            identity["Name"] == "repropatch" and identity["Version"] == VERSION,
            "最终 wheel 分发身份须为 repropatch 0.4.0",
        )
        for name in source.namelist():
            if not name.startswith("repropatch/") or name.endswith("/"):
                continue
            relative = PurePosixPath(name)
            require(".." not in relative.parts, "wheel 包路径包含父目录跳转")
            installed = module.parent.joinpath(*relative.parts[1:])
            require(not installed.is_symlink(), "安装的 wheel 包文件须为普通文件")
            content = source.read(name)
            require(installed.read_bytes() == content, f"安装包文件与 wheel 不一致：{name}")
            payload[name] = hashlib.sha256(content).hexdigest()
    require("repropatch/__init__.py" in payload, "wheel 缺少包入口")
    return {**value, "wheel": str(wheel), "wheel_sha256": digest, "wheel_files": payload}


def execute(summary, logs, cwd, name, argv, *, expected=0, timeout=60):
    record = {
        "name": name,
        "argv": argv,
        "cwd": str(cwd),
        "expected_returncode": expected,
        "returncode": None,
        "started_at": datetime.now(UTC).isoformat(),
    }
    summary["commands"].append(record)
    started = time.monotonic()
    print(f"执行 {name}", flush=True)
    try:
        with (
            (logs / f"{name}.stdout").open("wb") as stdout,
            (logs / f"{name}.stderr").open("wb") as stderr,
        ):
            result = subprocess.run(argv, cwd=cwd, stdout=stdout, stderr=stderr, timeout=timeout)
        record["returncode"] = result.returncode
        require(
            expected is None or result.returncode == expected,
            f"{name} 退出码为 {result.returncode}",
        )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        record["duration_seconds"] = time.monotonic() - started
        for stream in ("stdout", "stderr"):
            path = logs / f"{name}.{stream}"
            if path.exists():
                record[stream] = {
                    "path": f"commands/{path.name}",
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "size_bytes": path.stat().st_size,
                }
    return (logs / f"{name}.stdout").read_text(encoding="utf-8")


def validate_report(report, scenario, task, fixture, installation, directory):
    from repropatch.events import read_events
    from repropatch.verification import (
        EvaluationEvidence,
        baseline_result,
        candidate_result,
        validate_evidence,
    )

    _, outcome, reason = EXPECTED[scenario]
    require(
        (report["outcome"], report["reason_code"]) == (outcome, reason),
        f"{scenario} 验收终态不符合预期",
    )
    require(
        report["state"] == "FINISHED" and report["input_mode"] == "verify-patch", "须完成纯补丁验收"
    )
    for name in ("isolated", "reproduced", "candidate_roundtrip_verified", "artifacts_complete"):
        require(report[name] is True, f"{scenario} 缺少 {name} 核验")
    require(report["engine"]["kind"] == "none", "外部补丁须使用 none 引擎")
    require(
        all(
            type(report["agent"][name]) is int and report["agent"][name] == 0
            for name in ("steps_used", "tool_calls_used", "http_attempts")
        ),
        "外部补丁验收须保留零模型请求与零工具调用",
    )
    provenance = report["provenance"]
    require(
        report["harness_version"] == provenance["software_version"] == VERSION
        and provenance["implementation_sha256"] == installation["implementation_sha256"]
        and provenance["image_id"] == fixture["image_id"]
        and report["base_commit"] == fixture["commit"]
        and report["task_sha256"] == fixture["task_sha256"],
        "运行的版本、实现、镜像、commit 与 Task 身份须匹配",
    )
    baseline = EvaluationEvidence.from_dict(report["baseline"], None)
    independent = EvaluationEvidence.from_dict(report["independent"], None)
    require(
        baseline_result(SimpleNamespace(task=task), baseline) == (None, "BASELINE_PASSED"),
        "基线须完成编译、缺陷签名复现和 P2P 检查",
    )
    require(candidate_result(independent) == (outcome, reason), "独立验收证据与终态不一致")
    require(
        report["evaluations"] == [report["baseline"], report["independent"]]
        and baseline.identities == independent.identities
        and [(item.name, item.group) for item in baseline.tests]
        == [(item.name, item.group) for item in independent.tests]
        and all(item.result is not None for item in independent.tests)
        and baseline.source_tree_sha256 != independent.source_tree_sha256,
        "须保留基线与独立候选的同一测试身份和不同源码身份",
    )
    containers = []
    for role, evidence in (("baseline", baseline), ("independent", independent)):
        require(
            evidence.evaluation_role == role
            and evidence.isolated is True
            and evidence.image_id == fixture["image_id"]
            and evidence.inventory is not None
            and all(
                command is not None and command.ok and not command.output_truncated
                for command in (evidence.configure, evidence.build, evidence.discovery)
            )
            and evidence.compiler_cache is None
            and evidence.cleanup["confirmed"] is True
            and evidence.cleanup["errors"] == []
            and evidence.container_name
            and evidence.cleanup["container_id"],
            f"{role} 须使用已清理的独立冷构建 Docker 容器",
        )
        validate_evidence(evidence, directory)
        containers.append({"name": evidence.container_name, "id": evidence.cleanup["container_id"]})
    require(
        len({item["id"] for item in containers}) == len({item["name"] for item in containers}) == 2,
        "基线与独立验收须使用两个全新容器",
    )
    require(
        report["cleanup"]["active_code_stopped"] is True and report["cleanup"]["errors"] == [],
        "运行须确认活动代码与所属容器清理完成",
    )
    events = read_events(directory, directory.name).events
    require(
        not any(
            event["type"] in {"model_started", "model_finished", "tool_started"} for event in events
        ),
        "外部补丁轨迹须保持零模型请求",
    )
    return {
        "containers": containers,
        "model_requests": 0,
        "baseline": report["baseline"],
        "independent": report["independent"],
        "provenance": provenance,
    }


def audit_run(row, scenario, runs_root, task, fixture, installation, invoke):
    from repropatch.events import validate_run_id

    validate_run_id(row["run_id"])
    directory = runs_root / row["run_id"]
    require(Path(row["artifact_dir"]).absolute() == directory, "Run 目录须属于本场景")
    before = fingerprint(directory)
    require("events.sqlite3" in before, "运行须保留原始 SQLite 记录")
    report = json.loads((directory / "report.json").read_bytes())
    require(
        all(row[name] == report[name] for name in ("run_id", "state", "outcome", "reason_code"))
        and report["run_id"] == directory.name,
        "CLI 摘要与原始运行报告身份须匹配",
    )
    audit = validate_report(report, scenario, task, fixture, installation, directory)
    for command in ("inspect", "diagnose"):
        value = json.loads(
            invoke(
                f"{scenario}-{command}",
                [
                    sys.executable,
                    "-I",
                    "-m",
                    "repropatch",
                    command,
                    row["run_id"],
                    "--root",
                    str(runs_root),
                    "--json",
                ],
            )
        )
        require(
            value["run_id"] == row["run_id"]
            and value["evidence_complete"] is True
            and value["outcome"] == row["outcome"],
            f"{command} 须确认相同终态和完整证据",
        )
    require(before == fingerprint(directory), "只读查询修改了原始 Run 文件")
    remaining = invoke(
        f"{scenario}-container-cleanup",
        ["docker", "ps", "--all", "--quiet", "--filter", f"label=repropatch.run={row['run_id']}"],
    )
    require(not remaining.strip(), "所属 Docker 容器清理后须为空")
    return {
        "scenario": scenario,
        "run_id": row["run_id"],
        "outcome": row["outcome"],
        "reason_code": row["reason_code"],
        "artifact_directory": str(directory),
        **audit,
        "readonly_queries_preserved_all_files": True,
        "containers_removed": True,
        "original_files": before,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True, type=Path, help="新的证据目录")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    from repropatch.demo import _output_path
    from repropatch.errors import ReproPatchError
    from repropatch.task import Task

    try:
        output = _output_path(args.output)
        require(
            not any(
                output.is_relative_to(root / name) or (root / name).is_relative_to(output)
                for name in ("src", "examples", "scripts", "tests", "docker")
            ),
            "输出目录须与源码、测试及示例隔离",
        )
        output.mkdir(parents=True, mode=0o700)
        logs = output / "commands"
        logs.mkdir(mode=0o700)
    except (ReproPatchError, OSError, ValueError) as exc:
        parser.error(f"创建证据目录失败：{exc}")
    summary = {
        "schema": "repropatch.core-distribution-gate.v1",
        "status": "failed",
        "started_at": datetime.now(UTC).isoformat(),
        "requested_image": args.image,
        "gate_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "model_requests": 0,
        "paid_model_requests": 0,
        "commands": [],
        "scenarios": [],
        "manifest": "SHA256SUMS",
    }
    exit_code = 1
    try:
        with tempfile.TemporaryDirectory(prefix="repropatch-core-", dir="/tmp") as temporary:
            cwd = Path(temporary)
            summary["cli_cwd"] = str(cwd)
            require(not cwd.is_relative_to(root), "CLI 临时 cwd 须位于源码外")

            def invoke(name, argv, **options):
                return execute(summary, logs, cwd, name, argv, **options)

            identity = json.loads(
                invoke(
                    "installation",
                    [sys.executable, "-I", "-c", INSTALLATION_PROBE],
                )
            )
            summary["installation"] = identity
            summary["installation"] = validate_installation(identity, args.wheel)
            doctor = json.loads(
                invoke(
                    "doctor",
                    [
                        sys.executable,
                        "-I",
                        "-m",
                        "repropatch",
                        "doctor",
                        "--image",
                        args.image,
                        "--json",
                    ],
                    expected=None,
                )
            )
            summary["docker"] = doctor
            require(
                summary["commands"][-1]["returncode"] == 0 and doctor["ready"] is True,
                "DOCKER_UNAVAILABLE: Docker CLI、daemon 与指定本地镜像须就绪",
            )
            image_id = doctor["image"]["id"]
            summary["image_id"] = image_id
            fixture_root = output / "fixture"
            for name in FIXTURE_FILES:
                source, target = root / name, fixture_root / name
                require(source.is_file() and not source.is_symlink(), f"示例须为普通文件：{name}")
                target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
                shutil.copyfile(source, target)
            task_path = fixture_root / "task.yaml"
            fixture = json.loads(
                invoke(
                    "init-example",
                    [
                        sys.executable,
                        "-I",
                        str(fixture_root / "scripts/init_example.py"),
                        "--write-task",
                        str(task_path),
                        "--image",
                        image_id,
                    ],
                )
            )
            require(fixture["image_id"] == image_id, "示例 Task 须锁定已核验镜像")
            summary["fixture"] = fixture
            task = Task.load(task_path)
            for scenario, (expected_exit, _, _) in EXPECTED.items():
                runs_root = output / "runs" / scenario
                row = json.loads(
                    invoke(
                        f"{scenario}-verify-patch",
                        [
                            sys.executable,
                            "-I",
                            "-m",
                            "repropatch",
                            "verify-patch",
                            str(task_path),
                            "--patch",
                            str(
                                fixture_root
                                / "examples/patches"
                                / f"negative-maximum.{scenario}.patch"
                            ),
                            "--producer",
                            "core-distribution-gate",
                            "--output-root",
                            str(runs_root),
                            "--json",
                        ],
                        expected=expected_exit,
                        timeout=1000,
                    )
                )
                summary["scenarios"].append(
                    audit_run(
                        row,
                        scenario,
                        runs_root,
                        task,
                        fixture,
                        summary["installation"],
                        invoke,
                    )
                )
            summary["status"] = "passed"
            exit_code = 0
    except (
        ReproPatchError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
        zipfile.BadZipFile,
    ) as exc:
        summary["error"] = f"{type(exc).__name__}: {exc}"
    except KeyboardInterrupt:
        summary.update(status="interrupted", error="门禁被中断")
        exit_code = 130
    finally:
        summary["temporary_cwd_removed"] = not Path(summary.get("cli_cwd", "/")).exists()
        summary["finished_at"] = datetime.now(UTC).isoformat()
        (output / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (output / "SHA256SUMS").write_text(
            "".join(f"{digest}  {name}\n" for name, digest in fingerprint(output).items()),
            encoding="utf-8",
        )
    print(json.dumps({"status": summary["status"], "evidence": str(output)}, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
