"""通过安装后的 CLI 核验工程演示、独立验收和只读诊断。"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from importlib.metadata import distribution
from pathlib import Path

EXPECTED = {"repair": "ACCEPTED", "rejection": "REJECTED", "recovery": "ACCEPTED"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fingerprint(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        require(not path.is_symlink(), f"证据包含链接：{path.name}")
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
        else:
            require(path.is_dir(), f"证据包含特殊文件：{path.name}")
    require("events.sqlite3" in result, "运行缺少 SQLite 原始记录")
    return result


def validate_demo(value, demo_root):
    from repropatch.events import validate_run_id

    require(value.get("status") == "passed", "演示场景未全部达到预期")
    require(value.get("model_kind") == "scripted", "演示模型身份应为 scripted")
    require(
        type(value.get("paid_model_requests")) is int and value["paid_model_requests"] == 0,
        "演示须明确记录零付费模型请求",
    )
    require(len(value.get("runs", [])) == len(EXPECTED), "演示须包含三个独立场景")
    rows = {}
    for row in value["runs"]:
        scenario = row["scenario"]
        require(scenario in EXPECTED and scenario not in rows, "场景身份缺失或重复")
        validate_run_id(row["run_id"])
        directory = Path(row["artifact_directory"]).resolve()
        require(directory.name == row["run_id"], "Run ID 与产物目录身份不一致")
        require(directory.is_relative_to(demo_root.resolve()), "运行产物超出演示目录")
        require(row["outcome"] == EXPECTED[scenario], f"{scenario} 终态不符合预期")
        rows[scenario] = row
    return rows


def audit_run(row, query_root, execute):
    from repropatch.verification import EvaluationEvidence

    directory = Path(row["artifact_directory"]).resolve()
    run_id, scenario = row["run_id"], row["scenario"]
    root_args = [run_id, "--root", str(directory.parent)]
    before = fingerprint(directory)
    queries = {}
    for command, extra in (
        ("inspect", ["--json"]),
        ("diagnose", ["--json"]),
        ("replay", ["--mode", "trace", "--json"]),
    ):
        raw = execute(f"{scenario}-{command}", [command, *root_args, *extra])
        value = json.loads(raw)
        require(value["run_id"] == run_id, f"{command} 的 Run ID 不一致")
        require(value["evidence_complete"] is True, f"{command} 发现证据不完整")
        queries[command] = value
    trace_path = query_root / f"{scenario}-events.jsonl"
    execute(
        f"{scenario}-export",
        ["export-trace", *root_args, "--output", str(trace_path)],
    )
    require(before == fingerprint(directory), "只读查询修改了原始运行文件")
    events = [json.loads(line) for line in trace_path.read_text().splitlines()]
    require(bool(events), "导出的运行事件为空")
    require(
        [event["seq"] for event in events] == list(range(1, len(events) + 1)),
        "导出事件序号存在缺口",
    )
    report = json.loads(execute(f"{scenario}-report", ["report", *root_args, "--format", "json"]))
    require(report["outcome"] == EXPECTED[scenario], "派生报告终态与场景不一致")
    require(report["isolated"] is True, "演示须通过真实 Docker 隔离执行")
    require(report["reproduced"] is True, "原始缺陷须先完成真实复现")
    require(report["candidate_roundtrip_verified"] is True, "候选补丁往返核验缺失")
    require(report["artifacts_complete"] is True, "运行产物完整性核验失败")
    require(report["engine"]["kind"] == "fake", "演示运行须使用脚本模型")
    require(
        type(report["agent"]["http_attempts"]) is int and report["agent"]["http_attempts"] == 0,
        "演示运行须保留零 HTTP 模型请求记录",
    )
    independent = EvaluationEvidence.from_dict(report["independent"], None)
    require(
        independent.successful is (scenario != "rejection"),
        "独立验收结果与预期不一致",
    )
    event_counts = {
        name: sum(event["type"] == name for event in events)
        for name in ("baseline_finished", "model_started", "recovery_started")
    }
    if scenario == "recovery":
        edits = [
            event
            for event in events
            if event["type"] == "tool_started" and event["payload"]["name"] == "edit_file"
        ]
        require(event_counts["baseline_finished"] == 1, "恢复重复执行了基线")
        require(event_counts["recovery_started"] == 1, "恢复次数与场景不一致")
        require(len(edits) == 1, "恢复重复执行了编辑工具")
    return {
        "scenario": scenario,
        "run_id": run_id,
        "outcome": report["outcome"],
        "reason_code": report["reason_code"],
        "isolated": report["isolated"],
        "evidence_complete": queries["inspect"]["evidence_complete"],
        "readonly_queries_preserved_all_files": True,
        "independent_successful": independent.successful,
        "original_files": before,
        "event_counts": event_counts,
        "usage": report["usage"],
        "timing": report["timing"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="repropatch-cpp:0.1")
    parser.add_argument("--output", type=Path, required=True, help="新的证据目录")
    parser.add_argument("--require-installed-wheel", action="store_true")
    args = parser.parse_args()

    from repropatch.demo import _output_path
    from repropatch.errors import ReproPatchError

    try:
        output = _output_path(args.output)
        output.mkdir(mode=0o700, parents=True)
        query_root = output / "queries"
        query_root.mkdir(mode=0o700)
    except (ReproPatchError, OSError) as exc:
        parser.error(f"创建证据目录失败：{exc}")
    summary = {
        "schema": "repropatch.engineering-gate.v1",
        "status": "failed",
        "started_at": datetime.now(UTC).isoformat(),
        "paid_model_requests": 0,
        "commands": [],
        "scenarios": [],
    }

    def execute(name, arguments):
        argv = [sys.executable, "-I", "-m", "repropatch", *arguments]
        started = time.monotonic()
        print(f"{datetime.now(UTC).isoformat()} 执行 {name}", flush=True)
        record = {"name": name, "argv": argv, "returncode": None}
        summary["commands"].append(record)
        try:
            with (
                (query_root / f"{name}.stdout").open("wb") as stdout,
                (query_root / f"{name}.stderr").open("wb") as stderr,
            ):
                result = subprocess.run(argv, stdout=stdout, stderr=stderr, timeout=600)
            record["returncode"] = result.returncode
            require(result.returncode == 0, f"{name} 退出码为 {result.returncode}")
        except (OSError, subprocess.SubprocessError) as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            record["duration_seconds"] = time.monotonic() - started
        return (query_root / f"{name}.stdout").read_text()

    try:
        import repropatch
        from repropatch.harness import implementation_sha256

        installed = distribution("repropatch")
        origin = json.loads(installed.read_text("direct_url.json") or "{}")
        editable = origin.get("dir_info", {}).get("editable", False)
        if args.require_installed_wheel:
            require(
                not editable and origin.get("url", "").endswith(".whl"),
                "验收环境须安装指定 wheel",
            )
        summary["installation"] = {
            "version": installed.version,
            "editable": editable,
            "origin": origin,
            "package_directory": str(Path(repropatch.__file__).parent),
            "implementation_sha256": implementation_sha256(),
        }
        demo_root = output / "demo"
        demo = json.loads(
            execute(
                "demo",
                [
                    "demo",
                    "--image",
                    args.image,
                    "--output",
                    str(demo_root),
                    "--scenario",
                    "all",
                    "--json",
                ],
            )
        )
        rows = validate_demo(demo, demo_root)
        summary["image_id"] = demo["image_id"]
        for scenario in EXPECTED:
            summary["scenarios"].append(audit_run(rows[scenario], query_root, execute))
        summary["status"] = "passed"
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        summary["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        summary["finished_at"] = datetime.now(UTC).isoformat()
        (output / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
        )
    print(
        json.dumps(
            {
                "status": summary["status"],
                "evidence": str(output),
                "scenarios": len(summary["scenarios"]),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
