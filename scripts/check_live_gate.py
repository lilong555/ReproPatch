"""准备或显式执行一次真实模型验收；不自动重试失败的 Run。"""

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

from repropatch.artifacts import EvidenceRef, private_write
from repropatch.errors import ReproPatchError
from repropatch.events import read_events
from repropatch.harness import Harness, implementation_sha256
from repropatch.models import ResponsesConfig, validate_model_options
from repropatch.reports import committed_state, evidence_errors, inspect_run, load_result
from repropatch.task import Task


def live_observations(directory):
    """核对工具回传实际出现在下一请求中，并保留真实修复结局。"""
    directory = Path(directory)
    snapshot = read_events(directory, directory.name)
    state = committed_state(snapshot)
    report = load_result(directory, snapshot, state)
    failures = []
    if report["engine"]["kind"] != "agents-sdk" or report["usage"]["synthetic"]:
        failures.append("REAL_ENGINE_REQUIRED")
    if report["provenance"]["implementation_sha256"] != implementation_sha256():
        failures.append("IMPLEMENTATION_MISMATCH")
    if report["agent"]["agent_stop_reason"] != "MODEL_FINISHED":
        failures.append("MODEL_NOT_FINISHED")
    if not report["cleanup"]["active_code_stopped"]:
        failures.append("CLEANUP_UNCONFIRMED")
    if (
        evidence_errors(directory, snapshot, report)
        or not inspect_run(directory)["artifacts_complete"]
    ):
        failures.append("EVIDENCE_UNVERIFIABLE")
    native_outputs = {}
    native_inputs = []
    tools = []
    for event in snapshot.events:
        payload = event["payload"]
        if event["type"] == "model_finished":
            reference = EvidenceRef(**payload["native"])
            native = json.loads(reference.read(directory, limit=2 * 1024 * 1024))
            native_outputs[event["step_id"]] = native["output"]
        elif event["type"] == "model_started":
            reference = EvidenceRef(**payload["native_input"])
            native = json.loads(reference.read(directory, limit=512 * 1024))
            native_inputs.append((event, native["input"]))
        elif event["type"] == "tool_finished" and payload["ok"]:
            tools.append(event)
    round_trips = []
    for event in tools:
        payload = event["payload"]
        provider_id = payload["provider_call_id"]
        calls = native_outputs.get(event["step_id"], [])
        if not any(
            item.get("type") == "function_call"
            and item.get("call_id") == provider_id
            and item.get("name") == payload["name"]
            for item in calls
        ):
            continue
        result = json.loads(
            EvidenceRef(**payload["result_ref"]).read(directory, limit=2 * 1024 * 1024)
        )
        for later, items in native_inputs:
            if (
                later["seq"] <= event["seq"]
                or later["step_id"] <= event["step_id"]
                or later["step_id"] not in native_outputs
            ):
                continue
            for item in items:
                if item.get("type") != "function_call_output" or item.get("call_id") != provider_id:
                    continue
                try:
                    output = json.loads(item["output"])
                except (TypeError, ValueError):
                    continue
                if output == result:
                    round_trips.append(
                        {
                            "tool_call_id": event["tool_call_id"],
                            "tool_name": payload["name"],
                            "provider_call_id": provider_id,
                            "tool_finished_seq": event["seq"],
                            "next_model_started_seq": later["seq"],
                        }
                    )
                    break
            else:
                continue
            break
    if not round_trips:
        failures.append("TOOL_ROUND_TRIP_MISSING")
    return {
        "gate": "V-LIVE",
        "status": "passed" if not failures else "failed",
        "failures": failures,
        "run_id": report["run_id"],
        "engine": report["engine"],
        "agent": report["agent"],
        "usage": report["usage"],
        "cost": report["cost"],
        "outcome": report["outcome"],
        "reason_code": report["reason_code"],
        "implementation_sha256": report["provenance"]["implementation_sha256"],
        "tool_round_trips": round_trips,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-base", default="https://api.openai.com/v1")
    parser.add_argument("--key-env", default="OPENAI_API_KEY")
    parser.add_argument(
        "--use-env-proxy", action="store_true", help="显式信任宿主代理及 TLS 环境配置"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="执行新的真实模型 Run")
    parser.add_argument("--allow-paid-model", action="store_true", help="授权本次费用及数据发送")
    args = parser.parse_args(argv)
    created = False
    try:
        validate_model_options(args.model, args.api_base, args.key_env, True)
        task = Task.load(args.task)
        plan = {
            "gate": "V-LIVE",
            "status": "prepared",
            "model_name": args.model,
            "api_base": args.api_base,
            "key_env": args.key_env,
            "use_env_proxy": args.use_env_proxy,
            "task_file": str(args.task.absolute()),
            "task_id": task.id,
            "task_source_sha256": hashlib.sha256(task.source_bytes).hexdigest(),
            "base_commit": task.revision,
            "image": task.environment.image,
            "budget": asdict(task.budget),
            "output": str(args.output.absolute()),
            "outbound_data": ["任务描述", "工具 schema", "工具读取的源码及命令输出", "原生上下文"],
            "automatic_run_retries": 0,
            "cost_usd": None,
            "implementation_sha256": implementation_sha256(),
        }
        if not args.execute:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            return 0
        if not args.allow_paid_model:
            raise ReproPatchError("PAID_MODEL_CONSENT_REQUIRED: 执行必须显式授权")
        args.output.mkdir(mode=0o700, parents=True)
        created = True
        private_write(
            args.output / "plan.json", json.dumps(plan, ensure_ascii=False).encode() + b"\n"
        )
        report = Harness(
            task,
            ResponsesConfig(args.model, args.api_base, args.key_env, True, args.use_env_proxy),
            output_root=args.output / "runs",
        ).run()
        result = live_observations(Path(report["artifact_directory"]))
        result["plan"] = "plan.json"
        private_write(
            args.output / "summary.json",
            json.dumps(result, ensure_ascii=False, indent=2).encode() + b"\n",
        )
        print(json.dumps(result, ensure_ascii=True, indent=2))
        if report["outcome"] == "CANCELLED":
            return 130
        return 0 if result["status"] == "passed" else 3
    except (ReproPatchError, OSError, ValueError, TypeError, KeyError) as exc:
        if created:
            diagnostic = {
                "gate": "V-LIVE",
                "status": "failed",
                "error_type": type(exc).__name__,
                "model_name": args.model,
                "api_base": args.api_base,
                "automatic_run_retries": 0,
            }
            try:
                private_write(args.output / "summary.json", json.dumps(diagnostic).encode() + b"\n")
            except (OSError, ReproPatchError):
                pass
        print(f"V-LIVE: {str(exc).split(':', 1)[0]}", file=sys.stderr)
        return 3 if args.execute and args.allow_paid_model else 2


if __name__ == "__main__":
    raise SystemExit(main())
