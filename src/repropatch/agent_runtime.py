"""公开 SDK 的单次运行入口；仅接收宿主静态注册的异步 function tools。"""

import asyncio
import inspect
import time
from dataclasses import dataclass

from .context import (
    REQUEST_PURPOSE,
    SUMMARY_INSTRUCTIONS,
    ContextLimit,
    ContextState,
    admission_reason,
    encoded,
    fold_tool_output,
    request_purpose,
    stop_reason,
)
from .errors import ReproPatchError
from .models import positive_timeout, prepare_sdk


def model_file_scope(resolved, policy, *, shell_only=False):
    """初始提示压缩大型只读目录清单，工具逐路径使用完整冻结权限。"""
    readable = sorted(resolved.readable_files)
    if len(encoded(readable)) > policy.tool_output_max_bytes:
        readable = {
            "file_count": len(readable),
            "roots": sorted({path.split("/", 1)[0] for path in readable}),
            "discovery_tool": "bash" if shell_only else "list_directory",
            "source_root": "/src" if shell_only else ".",
        }
    return {"editable": sorted(resolved.editable_files), "readable": readable}


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
    except APIConnectionError as exc:
        # HTTP hooks 的拒绝可能被客户端包装为连接异常，保留领域原因。
        cause = exc.__cause__
        while cause is not None:
            if isinstance(cause, ContextLimit):
                raise cause from None
            cause = cause.__cause__
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


class ContextRebuilt(ReproPatchError):
    """安全边界退出当前 Runner，由公开入口装入替换后的有效历史。"""

    def __init__(self, items):
        self.items = items
        super().__init__("CONTEXT_REBUILT")


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
        PatchRejected,
        PolicyError,
    )
    from .models import raw_token_usage
    from .recovery import save_checkpoint
    from .task import canonical_json
    from .tools import Toolbox, model_evaluation, sdk_tools, sdk_tools_sha256, shell_only_tools
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
    current_body = None
    context_state = harness.context_state or ContextState(harness.context_policy)
    harness.context_state = context_state
    closed = False
    (harness.directory / "agent").mkdir(mode=0o700, exist_ok=True)
    (harness.directory / "agent/native").mkdir(mode=0o700, exist_ok=True)

    def deadline():
        if harness.shell_stop_reason is not None:
            raise AgentStop(harness.shell_stop_reason)
        if context.clock.remaining("agent_check") <= 0:
            raise AgentStop("AGENT_DEADLINE")
        if not harness.agent_resources_ready():
            raise CleanupUnconfirmed("CLEANUP_UNCONFIRMED: 工具之后的执行资源未确认静止")

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
        nonlocal next_input, current_body
        deadline()
        if closed:
            raise AgentStop("AGENT_DEADLINE")
        if report["model_steps"] >= budget.max_steps:
            raise AgentStop(
                "REQUEST_BUDGET_EXHAUSTED"
                if harness.context_policy.compaction_enabled
                else "STEP_BUDGET"
            )
        native = {"instructions": data.model_data.instructions, "input": data.model_data.input}
        if not harness.context_policy.compaction_enabled and (
            len(canonical_json(native)) > harness.context_policy.transport_max_bytes
        ):
            raise AgentStop("CONTEXT_LIMIT")
        if pending:
            raise ReproPatchError("CHECKPOINT_UNSAFE: 尚有未执行的准入工具")
        current_body = {
            **model_parameters,
            **native,
        }
        meter = harness.context_meter
        if meter is not None and meter.last_request_body is not None:
            current_body = {**meter.last_request_body, **native}
            context_state.estimator = meter.ledger.estimator(meter.attempt)
        plan = context_state.plan(current_body)
        if meter is None and plan is None and harness.context_policy.compaction_enabled:
            measurement = {
                **context_state.estimator.estimate(current_body),
                "transport_bytes": len(encoded(current_body)),
            }
            reason = admission_reason(harness.context_policy, measurement)
            if reason:
                save(
                    f"{report['model_steps'] + 1:04d}-local-rejection",
                    {
                        "body": current_body,
                        "measurement": measurement,
                        "stop_reason": reason,
                        "rejection_layer": "AgentRuntime.unmetered_input",
                    },
                )
                raise ContextLimit(reason)
        manifest, checkpoint_ref, pause = save_checkpoint(harness, workspace, native, tools_sha256)
        report["checkpoint"] = {
            "checkpoint_id": manifest["checkpoint_id"],
            "manifest": checkpoint_ref,
        }
        if pause:
            raise HarnessPause("已提交完整输入边界")
        if plan is not None:
            before = time.monotonic()
            summary_input = [{"role": "user", "content": encoded(plan["summarize"]).decode()}]

            async def summary_filter(summary_data):
                nonlocal next_input, current_body
                current_body = {
                    **model_parameters,
                    "tools": [],
                    "instructions": SUMMARY_INSTRUCTIONS,
                    "input": summary_data.model_data.input,
                }
                next_input = save(
                    f"{report['model_steps'] + 1:04d}-input",
                    {
                        "instructions": SUMMARY_INSTRUCTIONS,
                        "input": summary_data.model_data.input,
                        "request_purpose": "compact",
                    },
                )
                return summary_data.model_data

            try:
                repair_body = dict(current_body)
                with request_purpose("compact"):
                    summary = await run_sdk(
                        model=harness.model,
                        input_items=summary_input,
                        tools=[],
                        hooks=Hooks(),
                        input_filter=summary_filter,
                        instructions=SUMMARY_INSTRUCTIONS,
                        max_turns=1,
                        max_output_tokens=budget.max_output_tokens,
                        model_timeout=budget.model_timeout_seconds,
                        run_timeout=context.clock.remaining("agent_check"),
                    )
                replacement = context_state.replace(
                    repair_body,
                    plan,
                    summary.final_output,
                    sequence=report["model_steps"],
                    duration_seconds=time.monotonic() - before,
                )
                report["context"] = context_state.to_dict()
                log.emit("context_compacted", context_state.compactions[-1])
            except (HarnessPause, InfrastructureError):
                raise
            except Exception as exc:
                reason = stop_reason(exc)
                if reason in {"REQUEST_BUDGET_EXHAUSTED", "LOCAL_TRANSPORT_LIMIT"}:
                    raise AgentStop(reason) from exc
                log.emit("context_compaction_failed", {"cause": reason})
                raise AgentStop("COMPACTION_FAILED") from exc
            raise ContextRebuilt(replacement)
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
                    "request_purpose": REQUEST_PURPOSE.get(),
                },
                step_id=step,
            )
            report["model_steps"] = step
            report["usage"] = usage

        async def on_llm_end(self, wrapper, agent, response):
            output = [item.model_dump(mode="json", exclude_none=True) for item in response.output]
            if len(canonical_json(output)) > harness.context_policy.response_max_bytes:
                raise ReproPatchError("PROTOCOL_ERROR: 原生输出超过传输上限")
            ref = save(
                f"{report['model_steps']:04d}-output",
                {
                    "output": output,
                    "raw_usage": response.raw_usage,
                    "request_purpose": REQUEST_PURPOSE.get(),
                },
            )
            usage = raw_token_usage(response)
            context_state.estimator.observe(
                current_body, {"output": output, "usage": response.raw_usage}
            )
            if REQUEST_PURPOSE.get() == "repair" and context_state.compactions:
                compact = context_state.compactions[-1]
                compact.setdefault(
                    "post_compact_actual_input_tokens",
                    (response.raw_usage or {}).get("input_tokens"),
                )
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
                    "request_purpose": REQUEST_PURPOSE.get(),
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
            if REQUEST_PURPOSE.get() == "compact" and calls:
                raise ContextLimit("COMPACTION_FAILED", detail="摘要返回工具调用")
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
            if isinstance(exc, PatchRejected) and harness.tool_mode == "shell-only":
                raise
            message = str(exc)
            code = message.split(":", 1)[0] if ":" in message else "INVALID_ARGUMENT"
            code = {"EDIT_FILE_TOO_LARGE": "FILE_TOO_LARGE", "EDIT_NOT_TEXT": "NOT_UTF8"}.get(
                code, code
            )
            value = {"ok": False, "error": {"code": code, "message": message[:1000]}}
        # 整批工具已在事务中扣减；提示额度包含尚待执行的本批工具。
        value["progress"] = {
            "model_steps_remaining": budget.max_steps - report["model_steps"],
            "tool_calls_remaining": budget.max_tool_calls - report["tool_calls"],
            "pending_tool_calls": len(pending),
            "agent_seconds_remaining": max(0, int(context.clock.remaining("agent_check"))),
            "source_changed": workspace.expected_manifest != workspace.initial_manifest,
        }
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
        if context_state.compactions:
            context_state.compactions[-1]["continued_with_tools"] = True
        deadline()
        text = canonical_json(value).decode("utf-8")
        if harness.context_policy.compaction_enabled:
            return fold_tool_output(
                text,
                harness.context_policy.tool_output_max_bytes,
                lambda raw: reference.path,
            )
        return text

    toolbox = Toolbox(
        workspace,
        tuple(harness.resolved.editable_files),
        lambda name: harness._agent_check(workspace, name),
        readable=harness.resolved.readable_files,
    )
    tools = (
        shell_only_tools(
            boundary,
            lambda command, cwd, timeout: harness._agent_bash(workspace, command, cwd, timeout),
        )
        if harness.tool_mode == "shell-only"
        else sdk_tools(
            toolbox,
            boundary,
            lambda command, cwd, timeout: harness._agent_shell(workspace, command, cwd, timeout),
        )
    )
    if not harness.intermediate_checks_enabled:
        tools = [tool for tool in tools if tool.name not in {"run_command", "run_shell"}]
    names = {tool.name for tool in tools}
    tools_sha256 = sdk_tools_sha256(tools)
    model_parameters = {
        "model": getattr(harness.model, "model", "offline"),
        "max_output_tokens": budget.max_output_tokens,
        "tools": [
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.params_json_schema,
                "strict": tool.strict_json_schema,
            }
            for tool in tools
        ],
    }
    baseline = model_evaluation(harness.baseline.to_dict())
    initial = [
        {
            "role": "user",
            "content": canonical_json(
                {
                    "task": harness.task.prompt,
                    **model_file_scope(
                        harness.resolved,
                        harness.context_policy,
                        shell_only=harness.tool_mode == "shell-only",
                    ),
                    "base_commit": harness.resolved.base_commit,
                    "image_id": harness.resolved.image_id,
                    "budget": asdict(budget),
                    "baseline": baseline,
                    **(
                        {
                            "commands": harness.task.commands.to_dict(),
                            "shell": {
                                "source_visibility": "complete_prepared_snapshot",
                                "source_root": "/src",
                                "build_root": "/build",
                                "persistent": True,
                                "edit_mode": "in_place",
                                "git_metadata": "host_only",
                                "compiler_cache": "ccache" if harness.compiler_cache else "off",
                            },
                        }
                        if harness.tool_mode == "shell-only"
                        else {}
                    ),
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
        while True:
            try:
                result = await run_sdk(
                    model=harness.model,
                    input_items=initial,
                    tools=tools,
                    hooks=Hooks(),
                    input_filter=input_filter,
                    instructions=harness.instructions,
                    context=None,
                    max_turns=max(1, budget.max_steps - report["model_steps"]),
                    max_output_tokens=budget.max_output_tokens,
                    model_timeout=budget.model_timeout_seconds,
                    run_timeout=context.clock.remaining("agent_check"),
                )
                break
            except ContextRebuilt as rebuild:
                initial = rebuild.items
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
        harness.agent_stop_reason = (
            "REQUEST_BUDGET_EXHAUSTED"
            if harness.context_policy.compaction_enabled
            else "STEP_BUDGET"
        )
    except ContextLimit as exc:
        harness.agent_stop_reason = exc.reason
    except (AgentStop, StageDeadline) as exc:
        harness.agent_stop_reason = exc.reason if isinstance(exc, AgentStop) else "AGENT_DEADLINE"
    except asyncio.CancelledError:
        harness.agent_stop_reason = "USER_CANCELLED"
        raise KeyboardInterrupt() from None
    except TimeoutError:
        harness.agent_stop_reason = "AGENT_DEADLINE"
    except ModelTimeoutError:
        harness.agent_stop_reason = "MODEL_TIMEOUT"
        raise ReproPatchError("MODEL_REQUEST_TIMEOUT: 单次模型请求超时") from None
    except (InfrastructureError, OSError):
        raise
    except ReproPatchError as exc:
        harness.agent_stop_reason = (
            stop_reason(exc)
            if harness.context_policy.compaction_enabled
            else ("PROTOCOL_ERROR" if str(exc).startswith("PROTOCOL_ERROR") else "MODEL_ERROR")
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
        report["context"] = context_state.to_dict()
        if harness.context_meter is not None:
            metered = harness.context_meter.ledger.summary(harness.context_meter.attempt)
            # 本地拒绝没有上游用量；最终账本校正 SDK 启动钩子的临时未知标记。
            known = {
                "input_tokens": metered["known_input_tokens"],
                "output_tokens": metered["known_output_tokens"],
                "total_tokens": metered["known_input_tokens"] + metered["known_output_tokens"],
            }
            report["usage"].update(
                known_tokens=known, unknown_turns=metered["unknown_usage_requests"]
            )
            report["usage"].update(
                {k: None if metered["unknown_usage_requests"] else v for k, v in known.items()}
            )
            report["request_accounting"] = metered
    return AgentResult(
        harness.agent_stop_reason,
        report.get("model_summary"),
        report["model_steps"],
        report["tool_calls"],
        report["agent"]["http_attempts"],
        dict(report["usage"]),
        tuple(EvidenceRef(**ref) for ref in report["native_trace"]),
    )
