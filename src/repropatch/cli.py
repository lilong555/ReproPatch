import argparse
import json
import shutil
import sys
from pathlib import Path

from . import __version__
from .errors import ReproPatchError
from .harness import Harness
from .models import MockModel, OpenAICompatibleModel
from .process import run_process
from .task import Task


def parser():
    root = argparse.ArgumentParser(prog="repropatch", description="Reproducible C++ repair harness")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Check host tools and local Docker image")
    doctor.add_argument("--image", default="repropatch-cpp:0.1")
    check = commands.add_parser("validate-task", help="Validate task YAML without executing code")
    check.add_argument("task", type=Path)
    run = commands.add_parser("run", help="Reproduce, repair, independently verify")
    run.add_argument("task", type=Path)
    run.add_argument("--output", type=Path, default=Path(".repropatch/runs"))
    run.add_argument("--image", default="repropatch-cpp:0.1")
    run.add_argument("--model", choices=["mock", "openai-compatible"], default="mock")
    run.add_argument("--script", type=Path, help="Required for mock model")
    run.add_argument("--model-name")
    run.add_argument("--api-base", default="https://api.openai.com/v1")
    run.add_argument("--key-env", default="OPENAI_API_KEY")
    run.add_argument("--allow-paid-model", action="store_true")
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "doctor":
            checks = {
                "python": sys.version.split()[0],
                "git": shutil.which("git"),
                "docker": shutil.which("docker"),
                "daemon": False,
                "image": False,
            }
            if checks["docker"]:
                checks["daemon"] = run_process([checks["docker"], "info"], timeout=10).ok
                if checks["daemon"]:
                    checks["image"] = run_process(
                        [checks["docker"], "image", "inspect", args.image], timeout=10
                    ).ok
            print(json.dumps(checks, indent=2))
            return 0 if all(checks.values()) else 2
        task = Task.load(args.task)
        if args.command == "validate-task":
            print(json.dumps({"valid": True, "id": task.id, "repository": str(task.repository)}))
            return 0
        if args.model == "mock":
            if not args.script:
                raise ReproPatchError("--script is required for the mock model")
            model = MockModel.load(args.script)
        else:
            if not args.model_name:
                raise ReproPatchError("--model-name is required")
            model = OpenAICompatibleModel(
                args.model_name,
                base_url=args.api_base,
                key_env=args.key_env,
                allow_paid=args.allow_paid_model,
            )
        report = Harness(task, model, args.output, image=args.image).run()
        print(
            json.dumps(
                {
                    k: report[k]
                    for k in (
                        "run_id",
                        "status",
                        "isolated",
                        "duration_seconds",
                        "artifact_directory",
                    )
                },
                indent=2,
            )
        )
        return 0 if report["status"] == "passed" else 1
    except (ReproPatchError, OSError) as exc:
        print(f"repropatch: {exc}", file=sys.stderr)
        return 2
