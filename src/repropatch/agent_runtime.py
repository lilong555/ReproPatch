"""公开 SDK 的单次运行入口；仅接收宿主静态注册的异步 function tools。"""

import asyncio
import inspect
from dataclasses import dataclass

from .errors import ReproPatchError
from .models import positive_timeout, prepare_sdk


async def run_sdk(
    *,
    model,
    input_items,
    tools,
    hooks,
    input_filter,
    instructions: str,
    context=None,
    max_turns: int,
    max_output_tokens: int,
    model_timeout: float,
    run_timeout: float,
):
    """保留原生 RunResult；取消向 SDK 传播，资源清理由调用方拥有。"""
    positive_timeout(model_timeout)
    positive_timeout(run_timeout)
    if any(type(v) is not int or v <= 0 for v in (max_turns, max_output_tokens)):
        raise ReproPatchError("SDK turn 与输出 token 限额必须为正整数")
    prepare_sdk()
    from agents import (
        Agent,
        FunctionTool,
        Model,
        ModelRetrySettings,
        ModelSettings,
        RunConfig,
        Runner,
        ToolExecutionConfig,
        retry_policies,
    )
    from agents.exceptions import UserError
    from openai import APIConnectionError, APIError, APITimeoutError

    if not isinstance(model, Model):
        raise ReproPatchError("必须显式传入已构造的 SDK 模型，不能使用隐式模型或凭据")
    registered = list(tools)
    if any(
        not isinstance(tool, FunctionTool)
        or not (
            inspect.iscoroutinefunction(tool.on_invoke_tool)
            or inspect.iscoroutinefunction(type(tool.on_invoke_tool).__call__)
        )
        for tool in registered
    ):
        raise ReproPatchError("SDK 入口仅接受静态注册的异步 function tools")
    agent = Agent(
        name="ReproPatch",
        instructions=instructions,
        model=model,
        tools=registered,
        model_settings=ModelSettings(
            store=False,
            preserve_raw_usage=True,
            response_include=["reasoning.encrypted_content"],
            parallel_tool_calls=False,
            max_tokens=max_output_tokens,
            timeout=model_timeout,
            retry=ModelRetrySettings(max_retries=0, policy=retry_policies.never()),
        ),
    )
    config = RunConfig(
        tracing_disabled=True,
        trace_include_sensitive_data=False,
        call_model_input_filter=input_filter,
        tool_execution=ToolExecutionConfig(max_function_tool_concurrency=1),
        tool_not_found_behavior="raise_error",
        tool_name_collision_policy="error",
    )
    try:
        async with asyncio.timeout(run_timeout):
            return await Runner.run(
                agent,
                input=input_items,
                context=context,
                max_turns=max_turns,
                hooks=hooks,
                run_config=config,
            )
    except UserError as exc:
        # SDK 使用公开异常链包装工具错误；领域错误必须继续终止运行。
        if isinstance(exc.__cause__, (ReproPatchError, OSError)):
            raise exc.__cause__ from None
        raise
    except APITimeoutError:
        raise ReproPatchError("MODEL_REQUEST_TIMEOUT") from None
    except APIConnectionError:
        raise ReproPatchError("MODEL_CONNECTION_ERROR") from None
    except APIError as exc:
        status = getattr(exc, "status_code", None)
        code = (
            "MODEL_AUTH_ERROR"
            if status in (401, 403)
            else "MODEL_RATE_LIMIT"
            if status == 429
            else "MODEL_SERVER_ERROR"
            if type(status) is int and status >= 500
            else "MODEL_CONTEXT_ERROR"
            if getattr(exc, "code", None) == "context_length_exceeded"
            else "MODEL_REQUEST_FAILED"
        )
        raise ReproPatchError(code) from None


class AgentStop(ReproPatchError):
    """预算停止仍允许保存并独立验证已完成候选。"""

    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class AgentResult:
    """与 SDK 状态分离的领域结果，不能用 final_text 代替验证结局。"""

    stop_reason: str
    final_text: str | None
    steps_used: int
    tool_calls_admitted: int
    http_attempts: int | None
    usage: dict
    native_trace: tuple


async def run_agent(harness, workspace) -> AgentResult:
    """将领域预算和工具连接到公开 Runner，不保存或改写 SDK 私有状态。"""
    from dataclasses import asdict
    from importlib.metadata import version

    from agents import RunHooks
    from agents.exceptions import AgentsException, MaxTurnsExceeded, ModelTimeoutError
    from agents.testing import ScriptedModel

    from .artifacts import EvidenceRef
    from .errors import (
        CleanupUnconfirmed,
        HarnessPause,
        InfrastructureError,
        OperationDeadline,
        PolicyError,
    )
    from .models import raw_token_usage
    from .recovery import save_checkpoint
    from .task import canonical_json
    from .tools import Toolbox, model_baseline, sdk_tools, sdk_tools_sha256
    from .verification import StageDeadline
    from .workspace import git_deadline

    budget = harness.task.budget
    context = harness.context
    report = harness.report
    log = harness.log
    fake = isinstance(harness.model, ScriptedModel)
    report["engine"].update(
        kind="fake" if fake else "agents-sdk",
        versions={p: version(p) for p in ("openai-agents", "openai")},
    )
    report["agent"]["http_attempts"] = 0 if fake else None
    report["usage"]["synthetic"] = fake
    report["usage"].setdefault("unknown_turns", 0)
    report.setdefault("native_trace", [])
    totals = dict(report["usage"].get("known_tokens", {})) or {
        key: 0 for key in ("input_tokens", "output_tokens", "total_tokens")
    }
    unknown = {key: report["model_steps"] > 0 and report["usage"][key] is None for key in totals}
    pending = []
    next_input = None
    closed = False
    (harness.directory / "agent").mkdir(mode=0o700, exist_ok=True)
    (harness.directory / "agent/native").mkdir(mode=0o700, exist_ok=True)

    def deadline():
        if context.clock.remaining("agent_check") <= 0:
            raise AgentStop("AGENT_DEADLINE")
        if not harness.resources.containers_clean:
            raise CleanupUnconfirmed("CLEANUP_UNCONFIRMED: 工具之后的容器未确认删除")

    def save(name, value):
        ref = EvidenceRef.save(
            harness.directory,
            f"agent/native/{name}.json",
            canonical_json(value) + b"\n",
            budget=harness.resources.budget,
        )
        report["native_trace"].append(asdict(ref))
        return asdict(ref)

    async def input_filter(data):
        nonlocal next_input
        deadline()
        if closed:
            raise AgentStop("AGENT_DEADLINE")
        if report["model_steps"] >= budget.max_steps:
            raise AgentStop("STEP_BUDGET")
        native = {"instructions": data.model_data.instructions, "input": data.model_data.input}
        if len(canonical_json(native)) > 256 * 1024:
            raise AgentStop("CONTEXT_LIMIT")
        if pending:
            raise ReproPatchError("CHECKPOINT_UNSAFE: 尚有未执行的准入工具")
        manifest, checkpoint_ref, pause = save_checkpoint(harness, workspace, native, tools_sha256)
        report["checkpoint"] = {
            "checkpoint_id": manifest["checkpoint_id"],
            "manifest": checkpoint_ref,
        }
        if pause:
            raise HarnessPause("已提交完整输入边界")
        ref = save(f"{report['model_steps'] + 1:04d}-input", native)
        next_input = ref
        return data.model_data

    class Hooks(RunHooks):
        async def on_llm_start(self, *args):
            deadline()
            step = report["model_steps"] + 1
            # 已开始但尚无响应的请求，其用量也属于未知，不能沿用前轮已知总数。
            usage = {
                **report["usage"],
                "unknown_turns": report["usage"]["unknown_turns"] + 1,
                "known_tokens": dict(totals),
            }
            for key in totals:
                usage[key] = None
            log.emit(
                "model_started",
                {
                    "native_input": next_input,
                    "steps_used": step,
                    "usage": usage,
                    "engine": report["engine"],
                },
                step_id=step,
            )
            report["model_steps"] = step
            report["usage"] = usage

        async def on_llm_end(self, wrapper, agent, response):
            output = [item.model_dump(mode="json", exclude_none=True) for item in response.output]
            if len(canonical_json(output)) > 1024 * 1024:
                raise ReproPatchError("PROTOCOL_ERROR: 原生输出超过 1 MiB")
            ref = save(
                f"{report['model_steps']:04d}-output",
                {"output": output, "raw_usage": response.raw_usage},
            )
            usage = raw_token_usage(response)
            for key, value in usage.items():
                unknown[key] |= value is None
                totals[key] += value or 0
                report["usage"][key] = None if unknown[key] else totals[key]
            report["usage"]["known_tokens"] = dict(totals)
            report["usage"]["unknown_turns"] -= int(
                all(value is not None for value in usage.values())
            )
            log.emit(
                "model_finished",
                {
                    "step": report["model_steps"],
                    "native": ref,
                    "usage": usage,
                    "synthetic": fake,
                    "cumulative_usage": report["usage"],
                },
                step_id=report["model_steps"],
            )
            calls = []
            for item in response.output:
                if (
                    item.type not in {"message", "reasoning", "function_call"}
                    or getattr(item, "status", None) == "incomplete"
                ):
                    raise ReproPatchError("PROTOCOL_ERROR: 未授权执行项或未完成输出")
                if item.type == "function_call":
                    calls.append(item)
            ids = [call.call_id for call in calls]
            if (
                len(calls) > 8
                or any(not isinstance(cid, str) or not cid for cid in ids)
                or len(set(ids)) != len(ids)
            ):
                raise ReproPatchError("PROTOCOL_ERROR: 非法工具调用身份或数量")
            if any(
                call.name not in names
                or getattr(call, "async_", False)
                or getattr(call, "namespace", None) is not None
                for call in calls
            ):
                raise ReproPatchError("PROTOCOL_ERROR: 未注册工具")
            deadline()
            if report["tool_calls"] + len(calls) > budget.max_tool_calls:
                raise AgentStop("TOOL_BUDGET")
            admitted = report["tool_calls"] + len(calls)
            log.emit(
                "tool_batch_admitted",
                {
                    "step": report["model_steps"],
                    "call_ids": ids,
                    "tool_calls_used": admitted,
                    "calls": [
                        {
                            "tool_call_id": f"s{report['model_steps']:06d}.t{index:02d}",
                            "provider_call_id": call.call_id,
                            "name": call.name,
                        }
                        for index, call in enumerate(calls, 1)
                    ],
                },
                step_id=report["model_steps"],
            )
            report["tool_calls"] = admitted
            pending.extend(
                (call, f"s{report['model_steps']:06d}.t{index:02d}")
                for index, call in enumerate(calls, 1)
            )

    async def boundary(name, callback):
        if closed:
            raise AgentStop("AGENT_DEADLINE")
        deadline()
        if not pending or pending[0][0].name != name:
            raise ReproPatchError("PROTOCOL_ERROR: 工具执行与准入不一致")
        call, tool_id = pending.pop(0)
        identity = {"step_id": report["model_steps"], "tool_call_id": tool_id}
        log.emit("tool_started", {"provider_call_id": call.call_id, "name": name}, **identity)
        try:
            with log.bind(**identity), git_deadline(context.clock.deadline("agent_check")):
                value = {"ok": True, "data": callback()}
        except OperationDeadline:
            raise AgentStop("AGENT_DEADLINE") from None
        except PolicyError as exc:
            message = str(exc)
            code = message.split(":", 1)[0] if ":" in message else "INVALID_ARGUMENT"
            code = {"EDIT_FILE_TOO_LARGE": "FILE_TOO_LARGE", "EDIT_NOT_TEXT": "NOT_UTF8"}.get(
                code, code
            )
            value = {"ok": False, "error": {"code": code, "message": message[:1000]}}
        reference = EvidenceRef.save(
            harness.directory,
            f"agent/tool-results/{tool_id}.json",
            canonical_json(value) + b"\n",
            budget=harness.resources.budget,
        )
        log.emit(
            "tool_finished",
            {
                "provider_call_id": call.call_id,
                "name": name,
                "ok": value["ok"],
                "result_ref": asdict(reference),
            },
            **identity,
        )
        deadline()
        return canonical_json(value).decode("utf-8")

    toolbox = Toolbox(
        workspace,
        tuple(harness.resolved.editable_files),
        lambda name: harness._agent_check(workspace, name),
        readable=harness.resolved.readable_files,
    )
    tools = sdk_tools(
        toolbox,
        boundary,
        lambda command, cwd, timeout: harness._agent_shell(workspace, command, cwd, timeout),
    )
    names = {tool.name for tool in tools}
    tools_sha256 = sdk_tools_sha256(tools)
    baseline = model_baseline(harness.baseline.to_dict())
    initial = [
        {
            "role": "user",
            "content": canonical_json(
                {
                    "task": harness.task.prompt,
                    "editable": sorted(harness.resolved.editable_files),
                    "readable": sorted(harness.resolved.readable_files),
                    "base_commit": harness.resolved.base_commit,
                    "image_id": harness.resolved.image_id,
                    "budget": asdict(budget),
                    "baseline": baseline,
                }
            ).decode(),
        }
    ]
    if getattr(harness, "resume_native", None) is not None:
        initial = harness.resume_native["input"]
    try:
        deadline()
        if report["model_steps"] >= budget.max_steps:
            raise AgentStop("STEP_BUDGET")
        result = await run_sdk(
            model=harness.model,
            input_items=initial,
            tools=tools,
            hooks=Hooks(),
            input_filter=input_filter,
            instructions=harness.instructions,
            context=None,
            max_turns=budget.max_steps - report["model_steps"],
            max_output_tokens=budget.max_output_tokens,
            model_timeout=budget.model_timeout_seconds,
            run_timeout=context.clock.remaining("agent_check"),
        )
        if not isinstance(result.final_output, str) or not result.final_output.strip():
            raise ReproPatchError("PROTOCOL_ERROR: 缺少正常结束文本")
        reference = EvidenceRef.save(
            harness.directory,
            "agent/final-text.txt",
            result.final_output[:16000].encode(),
            budget=harness.resources.budget,
        )
        report["agent_final_text"] = asdict(reference)
        harness.agent_stop_reason = "MODEL_FINISHED"
    except HarnessPause:
        raise
    except MaxTurnsExceeded:
        harness.agent_stop_reason = "STEP_BUDGET"
    except (AgentStop, StageDeadline) as exc:
        harness.agent_stop_reason = exc.reason if isinstance(exc, AgentStop) else "AGENT_DEADLINE"
    except asyncio.CancelledError:
        harness.agent_stop_reason = "USER_CANCELLED"
        raise KeyboardInterrupt() from None
    except TimeoutError:
        harness.agent_stop_reason = "AGENT_DEADLINE"
    except ModelTimeoutError:
        harness.agent_stop_reason = "MODEL_ERROR"
        raise ReproPatchError("MODEL_REQUEST_TIMEOUT: 单次模型请求超时") from None
    except (InfrastructureError, OSError):
        raise
    except ReproPatchError as exc:
        harness.agent_stop_reason = (
            "PROTOCOL_ERROR" if str(exc).startswith("PROTOCOL_ERROR") else "MODEL_ERROR"
        )
        if str(exc).startswith("MODEL_") and ":" not in str(exc):
            raise ReproPatchError(str(exc) + ": 模型请求失败") from None
        raise
    except AgentsException:
        harness.agent_stop_reason = "PROTOCOL_ERROR"
        raise ReproPatchError("PROTOCOL_ERROR: SDK 拒绝模型或工具协议") from None
    except Exception:
        harness.agent_stop_reason = "MODEL_ERROR"
        raise ReproPatchError("MODEL_ERROR: 模型执行失败") from None
    finally:
        # SDK 可能仍有收尾任务，闭锁会阻止所有后续领域工具进入。
        closed = True
        pending.clear()
    return AgentResult(
        harness.agent_stop_reason,
        report.get("model_summary"),
        report["model_steps"],
        report["tool_calls"],
        report["agent"]["http_attempts"],
        dict(report["usage"]),
        tuple(EvidenceRef(**ref) for ref in report["native_trace"]),
    )
