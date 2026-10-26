"""启动一个原生 Agent 并导出补丁；本入口不调度批次，也不替代公共 Oracle。"""

import argparse
import hashlib
import json
import logging
import os
import shlex
import sqlite3
import subprocess
import sys
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import asdict
from pathlib import Path

from benchmark_budget import (
    POLICY,
    BudgetHooks,
    BudgetLedger,
    BudgetLimit,
    LocalUsageLedger,
    check_pricing_date,
    validate_task_budget,
)


def provider(args):
    """保留冻结的 DeepSeek 配置，显式选择用户提供的 CPA 对照配置。"""
    if args.provider == "local-luna":
        return "gpt-6-luna", "https://cpa.liyinlong.me/v1", "OPENAI_API_KEY", True
    return POLICY["model"], "https://api.deepseek.com", "DEEPSEEK_API_KEY", True


def reasoning_parameters(args):
    """Luna 默认使用 max；显式参数用于冻结各次实验配置。"""
    effort = args.reasoning_effort
    if args.provider == "local-luna":
        return {"reasoning": {"effort": effort or "max"}}
    if effort is not None:
        raise BudgetLimit("REASONING_EFFORT_REQUIRES_LUNA")
    return {}


def responses_client(args, hooks, *, transport=None):
    """在公开请求构造入口设置推理参数，计量保存实际发送的正文。"""
    import httpx2

    parameters = reasoning_parameters(args)

    class ConfiguredClient(httpx2.AsyncClient):
        def build_request(self, method, url, **options):
            if parameters:
                body = {**json.loads(options["content"]), **parameters}
                options["content"] = json.dumps(
                    body, ensure_ascii=False, separators=(",", ":")
                ).encode()
                headers = httpx2.Headers(options.get("headers"))
                headers.pop("content-length", None)
                options["headers"] = headers
            return super().build_request(method, url, **options)

    return ConfiguredClient(
        trust_env=provider(args)[3],
        follow_redirects=False,
        transport=transport,
        event_hooks={"request": [hooks.async_request], "response": [hooks.async_response]},
    )


def mini_inputs(args, task):
    """只读检查原生 mini 材料与共同输入，不加载模型或启动容器。"""
    from prepare_mini_environment import MINI_COMMIT

    from repropatch.workspace import git_tree

    if any(value is None for value in (args.mini_source, args.mini_environment, args.common_input)):
        raise BudgetLimit("BENCHMARK_MINI_ARGUMENT_MISSING")
    if args.agent_seconds <= 0:
        raise BudgetLimit("BENCHMARK_AGENT_TIME_INVALID")
    config = json.loads(args.mini_environment.read_text())
    preparation = json.loads((args.mini_environment.parent / "preparation.json").read_text())
    head = (
        subprocess.check_output(
            ["git", "-C", str(args.mini_source), "rev-parse", "HEAD"],
            stderr=subprocess.PIPE,
            timeout=30,
        )
        .decode()
        .strip()
    )
    if head != MINI_COMMIT or preparation["mini_commit"] != MINI_COMMIT:
        raise BudgetLimit("MINI_NATIVE_SOURCE_CHANGED")
    subprocess.check_output(
        ["git", "-C", str(args.mini_source), "diff", "--quiet", "HEAD", "--", "src"],
        stderr=subprocess.PIPE,
        timeout=30,
    )
    for name, digest in preparation["native_source_sha256"].items():
        if (
            hashlib.sha256((args.mini_source / "src/minisweagent" / name).read_bytes()).hexdigest()
            != digest
        ):
            raise BudgetLimit("MINI_NATIVE_SOURCE_CHANGED")
    if (
        config["image"] != task.environment.image
        or config.get("forward_env")
        or preparation["base_commit"] != task.revision
        or preparation["image_id"] != task.environment.image
        or sorted(preparation["editable_files"]) != sorted(task.editable_paths)
    ):
        raise BudgetLimit("MINI_ENVIRONMENT_MISMATCH")
    initial = json.loads(args.common_input.read_text())["input"]
    if len(initial) != 1 or initial[0]["role"] != "user":
        raise BudgetLimit("COMMON_INITIAL_INPUT_INVALID")
    task_input = initial[0]["content"]
    common = json.loads(task_input)
    tracked = {entry.path for entry in git_tree(task.repository, task.revision)}
    readable = {
        path
        for name in task.readable_paths
        for path in tracked
        if path == name or (name.endswith("/") and path.startswith(name))
    }
    if (
        common["task"] != task.prompt
        or common["base_commit"] != task.revision
        or common["image_id"] != task.environment.image
        or common["editable"] != sorted(task.editable_paths)
        or common["readable"] != sorted(readable)
        or common["budget"] != asdict(task.budget)
    ):
        raise BudgetLimit("COMMON_TASK_MISMATCH")
    source = Path(preparation.get("source", args.mini_environment.parent / "source"))
    if source.stat().st_mode & 0o005 != 0o005:
        raise BudgetLimit("MINI_SOURCE_NOT_READABLE")
    return (
        config,
        task_input,
        source,
    )


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    path.chmod(0o600)


def attempt_identity(task, attempt):
    """跨框架绑定同一份 Task 文件；原生 resolved contract SHA 另行记录。"""
    return {
        "attempt_id": attempt,
        "task_id": task.id,
        "task_sha256": hashlib.sha256(task.source_bytes).hexdigest(),
        "task_sha256_kind": "task_source_bytes",
        "prepared_commit": task.revision,
        "image_id": task.environment.image,
    }


def candidate_metadata(patch):
    return {
        "candidate_available": bool(patch),
        "candidate_bytes": len(patch),
        "candidate_sha256": hashlib.sha256(patch).hexdigest() if patch else None,
    }


def export_repropatch_candidate(report, directory, output):
    """按来源优先级选择首个非空补丁，证据引用的校验错误原样传播。"""
    from repropatch.artifacts import EvidenceRef

    if report.get("benchmark", {}).get("tool_mode") == "shell-only" and report.get(
        "reason_code"
    ) in {"FORBIDDEN_PATCH", "SOURCE_CHANGED"}:
        return {
            **candidate_metadata(b""),
            "candidate_source": None,
            "candidate_rejected": report["reason_code"],
            "recovered_from_unverified_patch": False,
        }
    reference = (report.get("candidate") or {}).get("patch")
    patch = (
        EvidenceRef(**reference).read(directory, limit=8 * 1024 * 1024)
        if reference is not None
        else b""
    )
    candidate_source = "candidate_ref" if patch else None
    for source, path in (
        ("patch_diff", directory / "patch.diff"),
        ("unverified_diagnostics", directory / "diagnostics/unverified.patch"),
    ):
        if patch:
            break
        if path.is_file():
            patch = path.read_bytes()
            candidate_source = source if patch else None
    if patch:
        (output / "candidate.patch").write_bytes(patch)
    return {
        **candidate_metadata(patch),
        "candidate_source": candidate_source,
        "recovered_from_unverified_patch": candidate_source == "unverified_diagnostics",
    }


@contextmanager
def intermediate_checks(harness, enabled=True):
    """消融组保留四个文件工具，基线与最终独立验收沿用 Harness。"""
    if enabled:
        yield
        return
    import repropatch.tools as tools_module

    original_tools = tools_module.sdk_tools
    original_instructions = harness.instructions
    replacements = (
        (
            "make a minimal correct repair, and run verification.",
            "make a minimal correct repair using the available file tools.",
        ),
        (
            'then use run_command("reproduce") for focused F2P feedback. '
            "Prefer focused symbol searches\n"
            'and line ranges. Use run_command("verify") when budget permits '
            "a P2P regression check\n"
            "and further repair; the harness always performs final independent acceptance.\n"
            "The baseline has already run; use its observed failures "
            "before repeating a full build.",
            "then review the change using focused symbol searches and line ranges.\n"
            "Intermediate command execution is disabled for this experiment.\n"
            "Use the observed baseline failures; "
            "the harness performs final independent acceptance.",
        ),
        (
            "Both commands configure and build in a fresh environment: "
            "reproduce runs only F2P target\n"
            "CTest checks; verify runs F2P and P2P. "
            "When editable files include both modular headers",
            "When editable files include both modular headers",
        ),
        (
            "Each run_shell call has an empty disposable /build; "
            "combine dependent shell commands in\n"
            "one call, and persist source changes through edit_file.",
            "Persist source changes through edit_file.",
        ),
        (
            "Once a concrete repair hypothesis is supported by the code, edit and test it before\n"
            "expanding the search. Reserve at least two tool calls "
            "for an edit and verification, and\n"
            "a model step to interpret the verification result. "
            "Use the remaining steps to correct\n"
            "observed failures.",
            "Once a concrete repair hypothesis is supported by the code, edit it before\n"
            "expanding the search. Reserve at least two tool calls for an edit and source review,\n"
            "and a model step to assess the change against the observed baseline failures.",
        ),
    )
    instructions = original_instructions
    for old, new in replacements:
        if instructions.count(old) != 1:
            raise ValueError("ABLATION_PROMPT_IDENTITY")
        instructions = instructions.replace(old, new)

    def file_tools(*args, **kwargs):
        return [
            tool
            for tool in original_tools(*args, **kwargs)
            if tool.name not in {"run_command", "run_shell"}
        ]

    harness.instructions = instructions
    tools_module.sdk_tools = file_tools
    try:
        yield
    finally:
        tools_module.sdk_tools = original_tools
        harness.instructions = original_instructions


def repropatch_agent(args, hooks, task):
    import repropatch.models as models
    from repropatch.harness import Harness

    factory = models.responses_model
    model_name, base_url, key_env, use_proxy = provider(args)

    @asynccontextmanager
    async def metered(*values, **options):
        async with responses_client(args, hooks) as client:
            async with factory(*values, **options, http_client=client) as model:
                yield model

    # 计量经公开 http_client 注入；候选模式保留冻结与补丁往返检查。
    models.responses_model = metered
    try:
        harness = Harness(
            task,
            model=models.ResponsesConfig(
                model=model_name,
                url=base_url,
                key_env=key_env,
                allow_paid=True,
                use_env_proxy=use_proxy,
            ),
            output_root=args.output / "runs",
            candidate_only=getattr(args, "candidate_only", False),
            compiler_cache=getattr(args, "compiler_cache", False),
            tool_mode=getattr(args, "tool_mode", "legacy"),
        )
        with intermediate_checks(
            harness, enabled=getattr(args, "intermediate_checks", "enabled") == "enabled"
        ):
            report = harness.run()
    finally:
        models.responses_model = factory
    directory = Path(report["artifact_directory"])
    candidate = export_repropatch_candidate(report, directory, args.output)
    return {
        "native_run_id": report["run_id"],
        "native_status": report["outcome"] or report["state"],
        "native_outcome": report["outcome"],
        "native_reason": report["reason_code"],
        "native_artifact_dir": str(directory),
        "native_task_sha256": report["provenance"]["task_sha256"],
        "native_image_id": report["provenance"]["image_id"],
        "baseline_eligible": report["reproduced"],
        "candidate_roundtrip_verified": report["candidate_roundtrip_verified"],
        "internal_verification_status": report["benchmark"]["internal_verification"],
        "internal_acceptance": report["verified"],
        "benchmark": report["benchmark"],
        **candidate,
        "tool_calls": report["tool_calls"],
        "model_steps": report["model_steps"],
        "container_deleted": report["cleanup_confirmed"],
    }


def mini_agent(args, hooks, task):
    from repropatch.task import canonical_json

    model_name, base_url, _, use_proxy = provider(args)
    config, task_input, source = mini_inputs(args, task)
    os.environ["MSWEA_GLOBAL_CONFIG_DIR"] = str(args.output / "mini-settings")
    os.environ["MSWEA_SILENT_STARTUP"] = "1"
    os.environ["MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT"] = "1"
    os.environ["MSWEA_GLOBAL_COST_LIMIT"] = "0"
    os.environ["MSWEA_GLOBAL_CALL_LIMIT"] = "0"
    os.environ["MSWEA_COST_TRACKING"] = (
        "ignore_errors" if args.provider == "local-luna" else "default"
    )
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    sys.path.insert(0, str(args.mini_source / "src"))
    import httpx
    import litellm
    import yaml
    from litellm.llms.custom_httpx.http_handler import HTTPHandler
    from minisweagent.agents.default import DefaultAgent
    from minisweagent.environments import get_environment
    from minisweagent.exceptions import InterruptAgentFlow, LimitsExceeded
    from minisweagent.models.litellm_response_model import LitellmResponseModel

    for name in ("LiteLLM", "litellm", "httpx", "openai"):
        logging.getLogger(name).disabled = True
    litellm.telemetry = False
    litellm.num_retries = 0
    litellm.suppress_debug_info = True
    litellm.register_model(
        {
            "openai/" + model_name: {
                "input_cost_per_token": 0 if args.provider == "local-luna" else 0.3e-6,
                "output_cost_per_token": 0 if args.provider == "local-luna" else 1.2e-6,
                "cache_read_input_token_cost": 0 if args.provider == "local-luna" else 0.006e-6,
                "max_input_tokens": 1048576,
                "max_output_tokens": 393216,
                "litellm_provider": "openai",
                "mode": "responses",
            }
        }
    )
    native = LitellmResponseModel(
        model_name="openai/" + model_name,
        cost_tracking="ignore_errors" if args.provider == "local-luna" else "default",
        model_kwargs={
            "api_base": base_url,
            "max_output_tokens": POLICY["max_output_tokens"],
            "stream": False,
            "store": False,
            "num_retries": 0,
            "timeout": task.budget.model_timeout_seconds,
            **reasoning_parameters(args),
        },
    )
    env = None
    calls = 0
    started = time.monotonic()
    deadline = started + args.agent_seconds
    http = httpx.Client(
        trust_env=use_proxy,
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
            except (BudgetLimit, InterruptAgentFlow):
                raise
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
        # 在首个模型请求前，用同一容器用户实际读取共同输入中的源码。
        probe = (
            "import json\n"
            f"paths = {json.loads(task_input)['readable']!r}\n"
            "for path in paths:\n"
            "    with open('/src/' + path, 'rb') as stream:\n"
            "        stream.read(1)\n"
            "print(json.dumps({'readable_files': len(paths), 'ok': True}))\n"
        )
        preflight = env.execute({"command": "python3 -c " + shlex.quote(probe)}, timeout=30)
        save(args.output / "source-readability.json", preflight)
        if preflight.get("returncode") != 0 or preflight.get("exception_info"):
            raise BudgetLimit("MINI_SOURCE_NOT_READABLE")
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
        "native_status": result.get("exit_status"),
        "native_reason": result.get("exit_status"),
        "internal_verification_status": "not_performed",
        "internal_acceptance": None,
        **candidate_metadata(patch),
        "tool_calls_admitted": calls,
        "model_steps": agent.n_calls,
        "container_deleted": deleted,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=("repropatch", "mini"), required=True)
    parser.add_argument("--provider", choices=("deepseek", "local-luna"), default="deepseek")
    parser.add_argument(
        "--reasoning-effort",
        choices=("none", "low", "medium", "high", "xhigh", "max"),
        help="Luna 推理强度，默认 max；各次实验须显式冻结",
    )
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mini-source", type=Path)
    parser.add_argument("--mini-environment", type=Path)
    parser.add_argument("--common-input", type=Path)
    parser.add_argument("--agent-seconds", type=int, default=800)
    parser.add_argument("--check-only", action="store_true", help="只读预检，不创建 Run 或调用模型")
    parser.add_argument(
        "--candidate-only", action="store_true", help="ReproPatch 导出候选供统一 Oracle"
    )
    parser.add_argument(
        "--compiler-cache", action="store_true", help="ReproPatch 自检使用 Run 级 ccache"
    )
    parser.add_argument("--intermediate-checks", choices=("enabled", "disabled"), default="enabled")
    parser.add_argument("--tool-mode", choices=("legacy", "shell-only"), default="legacy")
    args = parser.parse_args()
    if args.agent != "repropatch" and (
        args.candidate_only
        or args.compiler_cache
        or args.intermediate_checks != "enabled"
        or args.tool_mode != "legacy"
    ):
        parser.error("候选模式、编译缓存和中途自检开关适用于 ReproPatch")
    if args.tool_mode == "shell-only" and args.intermediate_checks != "enabled":
        parser.error("Shell-only 通过 Bash 执行自检，四文件工具消融使用 legacy 模式")
    from repropatch.errors import ReproPatchError
    from repropatch.task import Task

    try:
        parameters = reasoning_parameters(args)
        task = Task.load(args.task)
        if args.provider == "local-luna":
            ledger = LocalUsageLedger(args.ledger)
        else:
            check_pricing_date()
            ledger = BudgetLedger(args.ledger)
        request_cap = (
            ledger.request_cap(args.attempt)
            if args.provider == "local-luna" and args.tool_mode == "shell-only"
            else 12
        )
        validate_task_budget(task, request_cap=request_cap)
        if args.agent == "mini":
            mini_inputs(args, task)
    except BudgetLimit as error:
        print(json.dumps({"ok": False, "error_code": str(error)}))
        return 2
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        sqlite3.Error,
        ReproPatchError,
        subprocess.SubprocessError,
    ) as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_code": "BENCHMARK_INPUT_INVALID",
                    "error_type": type(error).__name__,
                }
            )
        )
        return 2
    if args.check_only:
        print(
            json.dumps(
                {
                    "ok": True,
                    "check_only": True,
                    "agent": args.agent,
                    "requests_reserved": 0,
                    **parameters,
                }
            )
        )
        return 0
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    (args.output / "task.original.yaml").write_bytes(task.source_bytes)
    hook_options = {"local_luna": True} if args.provider == "local-luna" else {}
    hooks = BudgetHooks(ledger, args.attempt, args.output / "http-native", **hook_options)
    started = time.monotonic()
    result = {
        "schema": "repropatch.benchmark-attempt.v1",
        "intermediate_checks": args.intermediate_checks,
        "tool_mode": args.tool_mode,
        "agent": args.agent,
        "attempt": args.attempt,
        **attempt_identity(task, args.attempt),
        **candidate_metadata(b""),
        "native_status": "NOT_STARTED",
        "native_reason": None,
        "internal_verification_status": "not_started"
        if args.agent == "repropatch"
        else "not_performed",
        "oracle_resolved": None,
    }
    result["provider"] = {
        "profile": args.provider,
        "model": provider(args)[0],
        "base_url": provider(args)[1],
        **parameters,
    }
    result["adapter_source_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (Path(__file__), Path(__file__).with_name("benchmark_budget.py"))
    }
    code = 1
    try:
        result.update(
            repropatch_agent(args, hooks, task)
            if args.agent == "repropatch"
            else mini_agent(args, hooks, task)
        )
        code = 0
    except KeyboardInterrupt:
        result.update(native_status="CANCELLED", native_reason="USER_CANCELLED")
    except Exception as error:
        result["native_status"] = "ERROR"
        result["error_type"] = type(error).__name__
        if isinstance(error, BudgetLimit):
            result["error_code"] = str(error)
        elif isinstance(error, RuntimeError) and str(error).startswith("MODEL_REQUEST_FAILED:"):
            result["error_code"] = str(error)
    finally:
        if args.agent == "mini" and (args.output / "cleanup.json").is_file():
            cleanup = json.loads((args.output / "cleanup.json").read_text())
            result["container_deleted"] = cleanup["container_deleted"]
            candidate = args.output / "candidate.patch"
            if cleanup["container_deleted"] and candidate.is_file():
                patch = candidate.read_bytes()
                result.update(candidate_metadata(patch), candidate_source="native_frozen")
        result.update(
            duration_seconds=time.monotonic() - started, money=ledger.summary(args.attempt)
        )
        save(args.output / "result.json", result)
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
