import argparse
import json
import shutil
import sys
from pathlib import Path

from . import __version__
from .errors import ReproPatchError
from .events import read_events, run_directory, validate_run_id
from .harness import Harness
from .process import run_process
from .reports import export_report, historical_report, inspect_run, markdown
from .resources import RunLock
from .task import Task, inspect_image


def parser():
    root = argparse.ArgumentParser(prog="repropatch", description="Reproducible C++ repair harness")
    root.add_argument("--version", action="version", version=f"{__version__} (Task v2)")
    commands = root.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Check host tools and local Docker image")
    doctor.add_argument("--image")
    doctor.add_argument("--json", action="store_true")
    check = commands.add_parser("validate-task", help="Validate task YAML without executing code")
    check.add_argument("task", type=Path)
    run = commands.add_parser("run", help="Reproduce, repair, independently verify")
    run.add_argument("task", type=Path)
    run.add_argument("--output-root", type=Path)
    run.add_argument("--engine", choices=["fake", "agents-sdk", "sdk"], default="fake")
    run.add_argument("--mock-script", type=Path, help="fake 引擎的原生 ScriptedModel JSON")
    run.add_argument("--model", "--model-name", dest="model_name")
    run.add_argument("--api-base", default="https://api.openai.com/v1")
    run.add_argument("--key-env", default="OPENAI_API_KEY")
    run.add_argument("--use-env-proxy", action="store_true", help="显式信任宿主代理及 TLS 环境配置")
    run.add_argument("--allow-paid-model", action="store_true")
    run.add_argument("--json", action="store_true")
    run.add_argument("--pause-after-step", type=int, help="在累计 N 个 turn 后的完整输入边界暂停")
    verify = commands.add_parser("verify-patch", help="无需模型的独立补丁验收")
    verify.add_argument("task", type=Path)
    verify.add_argument("--patch", required=True, type=Path)
    verify.add_argument("--producer")
    verify.add_argument("--producer-trace", type=Path)
    verify.add_argument("--output-root", type=Path)
    verify.add_argument("--json", action="store_true")
    for name, help_text in (
        ("inspect", "只读查询运行事实和证据完整性"),
        ("report", "从已提交事实重建报告"),
    ):
        query = commands.add_parser(name, help=help_text)
        query.add_argument("run_id")
        query.add_argument("--root", type=Path, default=Path(".repropatch/runs"))
        if name == "inspect":
            query.add_argument("--json", action="store_true")
        else:
            query.add_argument("--format", choices=["md", "json"], default="md")
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command in {"inspect", "report"}:
        try:
            validate_run_id(args.run_id)
        except ValueError as exc:
            print(f"repropatch: {exc}", file=sys.stderr)
            return 2
        try:
            directory = run_directory(args.root, args.run_id)
            if args.command == "inspect":
                result = inspect_run(directory)
                print(json.dumps(result, ensure_ascii=True, indent=None if args.json else 2))
                return 0
            snapshot = read_events(directory, args.run_id)
            if snapshot.version == 0:
                result = historical_report(directory, snapshot)
                print(json.dumps(result, ensure_ascii=True, indent=2))
                return 0
            lock = RunLock(directory)
            try:
                result = export_report(directory, snapshot)
            finally:
                lock.close()
            print(
                json.dumps(result, ensure_ascii=True, indent=2)
                if args.format == "json"
                else markdown(result),
                end="\n",
            )
            if result.get("command_error"):
                print(f"repropatch: {result['command_error']}", file=sys.stderr)
                return 3
            return 0
        except (ReproPatchError, OSError) as exc:
            print(f"repropatch: {exc}", file=sys.stderr)
            return 3
    try:
        if args.command == "doctor":
            checks = {
                "python": sys.version.split()[0],
                "git": shutil.which("git"),
                "docker": shutil.which("docker"),
                "daemon": False,
                "image": None,
            }
            if checks["docker"]:
                checks["daemon"] = run_process([checks["docker"], "info"], timeout=10).ok
                if checks["daemon"] and args.image:
                    try:
                        image = inspect_image(args.image)
                        checks["image"] = {
                            "id": image.image_id,
                            "repo_digests": image.repo_digests,
                            "platform": image.platform,
                        }
                    except ReproPatchError as exc:
                        checks["image"] = False
                        checks["error"] = str(exc)
            print(json.dumps(checks, indent=2))
            valid = all(checks[key] for key in ("python", "git", "docker", "daemon"))
            return 0 if valid and (not args.image or checks["image"]) else 2
        task = Task.load(args.task)
        if args.command == "validate-task":
            print(
                json.dumps(
                    {
                        "valid": True,
                        "version": task.version,
                        "id": task.id,
                        "repository": str(task.repository),
                        "commit": task.revision,
                        "image": task.environment.image,
                    }
                )
            )
            return 0
        if args.command == "verify-patch":
            harness = Harness(
                task,
                output_root=args.output_root,
                patch_file=args.patch,
                producer=args.producer,
                producer_trace=args.producer_trace,
            )
        else:
            from .models import load_sdk_script

            if (
                args.pause_after_step is not None
                and not 1 <= args.pause_after_step < task.budget.max_steps
            ):
                raise ReproPatchError("PAUSE_STEP_INVALID: 暂停 turn 须为 1 <= N < max_steps")

            if args.engine == "fake":
                if not args.mock_script:
                    raise ReproPatchError("fake 引擎必须提供 --mock-script")
                if (
                    args.model_name
                    or args.allow_paid_model
                    or args.api_base != "https://api.openai.com/v1"
                    or args.key_env != "OPENAI_API_KEY"
                    or args.use_env_proxy
                ):
                    raise ReproPatchError("fake 引擎不能提供真实模型参数")
                model, source = load_sdk_script(args.mock_script, with_source=True)
                harness = Harness(
                    task,
                    model,
                    args.output_root,
                    pause_after_step=args.pause_after_step,
                    script_source=source,
                )
            else:
                if args.mock_script:
                    raise ReproPatchError("sdk 引擎不接受 --mock-script")
                if not args.model_name:
                    raise ReproPatchError("必须提供 --model（也支持 --model-name）")
                if not args.allow_paid_model:
                    raise ReproPatchError(
                        "PAID_MODEL_CONSENT_REQUIRED: 必须显式 --allow-paid-model"
                    )
                from .models import ResponsesConfig

                config = ResponsesConfig(
                    args.model_name, args.api_base, args.key_env, True, args.use_env_proxy
                )
                harness = Harness(
                    task,
                    config,
                    args.output_root,
                    **(
                        {"pause_after_step": args.pause_after_step}
                        if args.pause_after_step is not None
                        else {}
                    ),
                )
        try:
            report = harness.run()
        except (ReproPatchError, OSError) as exc:
            print(f"repropatch: 运行失败：{exc}", file=sys.stderr)
            return 3
        if "outcome" in report:
            summary = {
                "run_id": report["run_id"],
                "task_id": report["task_id"],
                "input_mode": report["input_mode"],
                "state": report["state"],
                "outcome": report["outcome"],
                "reason_code": report["reason_code"],
                "paused": report.get("paused", False),
                "artifact_dir": report["artifact_directory"],
                "artifacts_complete": report.get("artifacts_complete", True),
                "command_error": report.get("command_error"),
            }
            if summary["paused"]:
                summary["checkpoint"] = report["checkpoint"]
            print(
                json.dumps(
                    summary,
                    ensure_ascii=False,
                    separators=(",", ":") if getattr(args, "json", False) else None,
                )
            )
            if summary["command_error"]:
                print(f"repropatch: {summary['command_error']}", file=sys.stderr)
                return 3
            if summary["paused"]:
                return 0
            if report["outcome"] == "CANCELLED":
                return 130
            if report["outcome"] in {"ERROR", "INCONCLUSIVE"}:
                return 3
            return 0 if report["outcome"] == "ACCEPTED" else 1
        print(
            json.dumps(
                {
                    key: report[key]
                    for key in (
                        "run_id",
                        "status",
                        "isolated",
                        "duration_seconds",
                        "artifact_directory",
                    )
                }
            )
        )
        return (
            3
            if report["status"] in {"error", "internal_error"}
            else 0
            if report["status"] == "passed"
            else 1
        )
    except (ReproPatchError, OSError) as exc:
        print(f"repropatch: {exc}", file=sys.stderr)
        return 2
