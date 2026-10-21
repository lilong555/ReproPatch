"""启动一个原生 Agent 并导出补丁；本入口不调度批次，也不替代公共 Oracle。"""

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from benchmark_budget import POLICY, BudgetHooks, BudgetLedger


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    path.chmod(0o600)


def repropatch_agent(args, hooks):
    import httpx2

    import repropatch.models as models
    from repropatch.harness import Harness
    from repropatch.task import Task

    factory = models.responses_model

    @asynccontextmanager
    async def metered(*values, **options):
        async with httpx2.AsyncClient(
            trust_env=True,
            follow_redirects=False,
            event_hooks={"request": [hooks.async_request], "response": [hooks.async_response]},
        ) as client:
            async with factory(*values, **options, http_client=client) as model:
                yield model

    # 只注入已有公开 http_client 参数，Runner、工具和独立验收均使用原实现。
    models.responses_model = metered
    try:
        report = Harness(
            Task.load(args.task),
            model=models.ResponsesConfig(
                model=POLICY["model"],
                url="https://api.deepseek.com",
                key_env="DEEPSEEK_API_KEY",
                allow_paid=True,
                use_env_proxy=True,
            ),
            output_root=args.output / "runs",
        ).run()
    finally:
        models.responses_model = factory
    directory = Path(report["artifact_directory"])
    from repropatch.artifacts import EvidenceRef

    reference = (report.get("candidate") or {}).get("patch")
    if reference is not None:
        patch = EvidenceRef(**reference).read(directory, limit=8 * 1024 * 1024)
        (args.output / "candidate.patch").write_bytes(patch)
    elif (directory / "patch.diff").is_file():
        (args.output / "candidate.patch").write_bytes((directory / "patch.diff").read_bytes())
    elif (directory / "diagnostics/unverified.patch").is_file():
        (args.output / "candidate.patch").write_bytes(
            (directory / "diagnostics/unverified.patch").read_bytes()
        )
    return {
        "native_run_id": report["run_id"],
        "native_outcome": report["outcome"],
        "native_reason": report["reason_code"],
        "native_artifact_dir": str(directory),
        "tool_calls": report["tool_calls"],
        "model_steps": report["model_steps"],
        "container_deleted": report["cleanup_confirmed"],
    }


def mini_agent(args, hooks):
    os.environ["MSWEA_GLOBAL_CONFIG_DIR"] = str(args.output / "mini-settings")
    os.environ["MSWEA_SILENT_STARTUP"] = "1"
    os.environ["MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT"] = "1"
    os.environ["MSWEA_GLOBAL_COST_LIMIT"] = "0"
    os.environ["MSWEA_GLOBAL_CALL_LIMIT"] = "0"
    os.environ["MSWEA_COST_TRACKING"] = "default"
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    sys.path.insert(0, str(args.mini_source / "src"))
    import httpx
    import litellm
    import yaml
    from litellm.llms.custom_httpx.http_handler import HTTPHandler
    from minisweagent.agents.default import DefaultAgent
    from minisweagent.environments import get_environment
    from minisweagent.exceptions import LimitsExceeded
    from minisweagent.models.litellm_response_model import LitellmResponseModel

    from repropatch.task import Task, canonical_json

    for name in ("LiteLLM", "litellm", "httpx", "openai"):
        logging.getLogger(name).disabled = True
    litellm.telemetry = False
    litellm.num_retries = 0
    litellm.suppress_debug_info = True
    litellm.register_model(
        {
            "openai/deepseek-flash": {
                "input_cost_per_token": 0.3e-6,
                "output_cost_per_token": 1.2e-6,
                "cache_read_input_token_cost": 0.006e-6,
                "max_input_tokens": 1048576,
                "max_output_tokens": 393216,
                "litellm_provider": "openai",
                "mode": "responses",
            }
        }
    )
    task = Task.load(args.task)
    config = json.loads(args.mini_environment.read_text())
    preparation = json.loads((args.mini_environment.parent / "preparation.json").read_text())
    for name, digest in preparation["native_source_sha256"].items():
        if (
            hashlib.sha256((args.mini_source / "src/minisweagent" / name).read_bytes()).hexdigest()
            != digest
        ):
            raise ValueError("MINI_NATIVE_SOURCE_CHANGED")
    if config["image"] != task.environment.image or config.get("forward_env"):
        raise ValueError("MINI_ENVIRONMENT_MISMATCH")
    initial = json.loads(args.common_input.read_text())["input"]
    if len(initial) != 1 or initial[0]["role"] != "user":
        raise ValueError("COMMON_INITIAL_INPUT_INVALID")
    task_input = initial[0]["content"]
    if json.loads(task_input)["task"] != task.prompt:
        raise ValueError("COMMON_ISSUE_MISMATCH")
    native = LitellmResponseModel(
        model_name="openai/deepseek-flash",
        model_kwargs={
            "api_base": "https://api.deepseek.com",
            "max_output_tokens": POLICY["max_output_tokens"],
            "stream": False,
            "store": False,
            "num_retries": 0,
            "timeout": task.budget.model_timeout_seconds,
        },
    )
    source = Path(
        json.loads((args.mini_environment.parent / "preparation.json").read_text()).get(
            "source", args.mini_environment.parent / "source"
        )
    )
    env = None
    calls = 0
    started = time.monotonic()
    deadline = started + args.agent_seconds
    http = httpx.Client(
        trust_env=True,
        follow_redirects=False,
        timeout=task.budget.model_timeout_seconds,
        event_hooks={"request": [hooks.request], "response": [hooks.response]},
    )
    handler = HTTPHandler(client=http, follow_redirects=False)

    class ModelTransport:
        def __getattr__(self, name):
            return getattr(native, name)

        def query(self, messages):
            nonlocal calls
            prepared = native._prepare_messages_for_api(messages)
            if len(canonical_json({"input": prepared})) > 256 * 1024:
                raise LimitsExceeded(
                    {
                        "role": "exit",
                        "content": "CONTEXT_LIMIT",
                        "extra": {"exit_status": "CONTEXT_LIMIT"},
                    }
                )
            try:
                result = native.query(messages, client=handler)
            except Exception as error:
                raise RuntimeError("MODEL_REQUEST_FAILED:" + type(error).__name__) from None
            actions = result.get("extra", {}).get("actions", [])
            if len(actions) > 8 or calls + len(actions) > task.budget.max_tool_calls:
                raise LimitsExceeded(
                    {
                        "role": "exit",
                        "content": "TOOL_BUDGET",
                        "extra": {"exit_status": "TOOL_BUDGET"},
                    }
                )
            calls += len(actions)
            return result

    class EnvironmentDeadline:
        def __getattr__(self, name):
            return getattr(env, name)

        def execute(self, action):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("AGENT_DEADLINE")
            result = env.execute(action, timeout=min(task.timeout_seconds, remaining))
            if result.get("exception_info"):
                raise RuntimeError("TOOL_EXECUTION_UNKNOWN")
            return result

    deleted = False
    try:
        env = get_environment(config)
        info = json.loads(
            subprocess.check_output(
                ["docker", "inspect", env.container_id],
                timeout=30,
            )
        )[0]
        host = info["HostConfig"]
        expected = {
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges:true"],
            "Memory": task.environment.memory_mib * 1024 * 1024,
            "MemorySwap": task.environment.memory_mib * 1024 * 1024,
            "PidsLimit": task.environment.pids_limit,
            "NanoCpus": round(task.environment.cpu_limit * 1_000_000_000),
        }
        if info["Config"]["User"] != "65534:65534" or any(
            host.get(k) != v for k, v in expected.items()
        ):
            raise ValueError("MINI_ACTUAL_CONTAINER_PROFILE_MISMATCH")
        writable = {m["Destination"] for m in info["Mounts"] if m["Type"] == "bind" and m["RW"]}
        if writable != {"/src/" + name for name in task.editable_paths}:
            raise ValueError("MINI_ACTUAL_EDITABLE_SCOPE_MISMATCH")
        save(
            args.output / "owned-container.json",
            {
                "container_id": env.container_id,
                "profile": expected,
                "user": "65534:65534",
                "writable_bind_destinations": sorted(writable),
            },
        )
        templates = yaml.safe_load(
            (args.mini_source / "src/minisweagent/config/mini.yaml").read_text()
        )
        system = templates["agent"]["system_template"]
        system += (
            "\nWork in /src. Only the supplied editable files allow in-place writes. "
            "Their directories, tests and Git metadata are read-only. Do not use atomic "
            "replacement or create files in /src; use /tmp or /build for scratch work. "
            "Python Path.write_text supports in-place writes here. "
            "Use echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT to finish; "
            "the host exports the patch and independently evaluates it."
        )
        agent = DefaultAgent(
            ModelTransport(),
            EnvironmentDeadline(),
            system_template=system,
            instance_template=templates["agent"]["instance_template"],
            step_limit=task.budget.max_steps,
            cost_limit=0,
            wall_time_limit_seconds=args.agent_seconds,
            output_path=args.output / "trajectory.json",
        )
        result = agent.run(task_input)
    finally:
        http.close()
        if env is not None and env.container_id is not None:
            identity = env.container_id
            env.cleanup()
            subprocess.run(["docker", "rm", "-f", identity], capture_output=True, timeout=30)
            remaining = subprocess.check_output(
                [
                    "docker",
                    "ps",
                    "-a",
                    "--no-trunc",
                    "--filter",
                    f"id={identity}",
                    "--format",
                    "{{.ID}}",
                ],
                timeout=30,
            )
            deleted = not remaining.strip()
            env.container_id = None
        save(args.output / "cleanup.json", {"container_deleted": deleted})
        if deleted:
            patch = subprocess.check_output(
                [
                    "git",
                    "-C",
                    str(source),
                    "-c",
                    "core.hooksPath=/dev/null",
                    "diff",
                    "--binary",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--",
                    *task.editable_paths,
                ],
                timeout=30,
            )
            (args.output / "candidate.patch").write_bytes(patch)
    if not deleted:
        raise RuntimeError("CONTAINER_CLEANUP_UNCONFIRMED")
    return {
        "native_exit_status": result.get("exit_status"),
        "tool_calls_admitted": calls,
        "model_steps": agent.n_calls,
        "container_deleted": deleted,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=("repropatch", "mini"), required=True)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mini-source", type=Path)
    parser.add_argument("--mini-environment", type=Path)
    parser.add_argument("--common-input", type=Path)
    parser.add_argument("--agent-seconds", type=int, default=800)
    args = parser.parse_args()
    from repropatch.task import Task

    task = Task.load(args.task)
    if (
        task.budget.max_output_tokens != POLICY["max_output_tokens"]
        or task.budget.max_steps != POLICY["request_limit_per_attempt"]
    ):
        parser.error("Task 与冻结模型预算不一致")
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    ledger = BudgetLedger(args.ledger)
    hooks = BudgetHooks(ledger, args.attempt, args.output / "http-native")
    started = time.monotonic()
    result = {"agent": args.agent, "attempt": args.attempt, "oracle_resolved": None}
    result["adapter_source_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (Path(__file__), Path(__file__).with_name("benchmark_budget.py"))
    }
    code = 1
    try:
        result.update(
            repropatch_agent(args, hooks) if args.agent == "repropatch" else mini_agent(args, hooks)
        )
        code = 0
    except Exception as error:
        result["error_type"] = type(error).__name__
    finally:
        result.update(
            duration_seconds=time.monotonic() - started, money=ledger.summary(args.attempt)
        )
        save(args.output / "result.json", result)
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
