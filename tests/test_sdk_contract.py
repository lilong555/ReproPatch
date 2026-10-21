"""锁定 SDK 的公开组合契约；模型与 HTTP 均为离线受控替身。"""

import asyncio
import importlib
import json
import logging
import socket
import traceback

import pytest

from repropatch.agent_runtime import run_sdk
from repropatch.errors import InfrastructureError, ReproPatchError
from repropatch.models import load_sdk_script, raw_token_usage, responses_model

pytestmark = pytest.mark.sdk


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("SDK 契约测试禁止真实网络")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)


@pytest.fixture
def sdk():
    return importlib.import_module("agents")


@pytest.fixture
def testing():
    return importlib.import_module("agents.testing")


async def invoke(model, **overrides):
    options = dict(
        model=model,
        input_items=[{"role": "user", "content": "执行离线契约"}],
        tools=[],
        hooks=None,
        input_filter=None,
        instructions="仅执行契约工具。",
        max_turns=4,
        max_output_tokens=256,
        model_timeout=2,
        run_timeout=5,
    )
    options.update(overrides)
    return await run_sdk(**options)


@pytest.mark.parametrize("enabled", [False, True])
def test_transport_environment_requires_explicit_choice(enabled, monkeypatch):
    import httpx2

    constructor = httpx2.AsyncClient
    configurations = []
    clients = []

    class CapturedClient(constructor):
        def __init__(self, **options):
            configurations.append(options)
            super().__init__(**options)
            clients.append(self)

    monkeypatch.setattr(httpx2, "AsyncClient", CapturedClient)
    monkeypatch.setenv("CONTRACT_PROXY_KEY", "synthetic-proxy-contract")

    async def scenario():
        options = {"use_env_proxy": True} if enabled else {}
        async with responses_model(
            "contract-model",
            model_timeout=1,
            allow_paid=True,
            key_env="CONTRACT_PROXY_KEY",
            **options,
        ):
            pass

    asyncio.run(scenario())
    assert configurations == [{"trust_env": enabled, "follow_redirects": False}]
    assert clients[0].is_closed


def test_native_items_roundtrip_and_public_hook_order(sdk, testing):
    from openai.types.responses import ResponseReasoningItem

    events = []

    @sdk.function_tool(failure_error_function=None)
    async def contract_echo(value: str) -> str:
        """原样返回契约文本，无文件或进程副作用。"""
        events.append("工具")
        return value

    class Hooks(sdk.RunHooks):
        async def on_llm_start(self, *args):
            events.append("请求前")

        async def on_llm_end(self, context, agent, response):
            events.append("准入")
            assert all(hasattr(item, "model_dump") for item in response.output)

        async def on_tool_start(self, *args):
            events.append("工具前")

    async def boundary(data):
        events.append("输入过滤")
        return data.model_data

    reasoning = ResponseReasoningItem(
        id="reasoning-1", type="reasoning", summary=[], encrypted_content="opaque-synthetic"
    )
    model = testing.ScriptedModel(
        [
            testing.ModelStep(
                output=[
                    reasoning,
                    testing.function_call("contract_echo", {"value": "往返"}, call_id="call-1"),
                ],
                raw_usage={"input_tokens": 0},
            ),
            testing.ModelStep(output=[testing.assistant_message("结束")]),
        ]
    )
    result = asyncio.run(invoke(model, tools=[contract_echo], hooks=Hooks(), input_filter=boundary))
    model.assert_complete()
    assert result.final_output == "结束"
    assert events == ["输入过滤", "请求前", "准入", "工具前", "工具", "输入过滤", "请求前", "准入"]
    second_input = model.calls[1].input
    assert any(
        item.get("type") == "reasoning" and item["encrypted_content"] == "opaque-synthetic"
        for item in second_input
    )
    assert any(
        item.get("type") == "function_call_output"
        and item["call_id"] == "call-1"
        and item["output"] == "往返"
        for item in second_input
    )
    continuation = result.to_input_list()
    assert continuation[: len(second_input)] == second_input
    assert raw_token_usage(result.raw_responses[0]) == {
        "input_tokens": 0,
        "output_tokens": None,
        "total_tokens": None,
    }
    assert raw_token_usage(result.raw_responses[1]) == dict.fromkeys(
        ("input_tokens", "output_tokens", "total_tokens")
    )
    following = testing.ScriptedModel([[testing.assistant_message("继续")]])
    asyncio.run(invoke(following, input_items=continuation))
    assert following.first_call.input == continuation
    following.assert_complete()
    for call in model.calls:
        settings = call.model_settings
        assert settings.store is False and settings.parallel_tool_calls is False
        assert settings.preserve_raw_usage is True
        assert settings.response_include == ["reasoning.encrypted_content"]
        assert settings.retry.max_retries == 0
        assert settings.timeout == 2 and settings.max_tokens == 256
        assert call.tracing.is_disabled()
        assert call.previous_response_id is None and call.conversation_id is None
        assert call.handoffs == []


def test_public_hook_denies_entire_batch_before_any_tool(sdk, testing):
    executed = []

    @sdk.function_tool(failure_error_function=None)
    async def contract_echo(value: str) -> str:
        """仅供准入次序测试。"""
        executed.append(value)
        return value

    class Deny(sdk.RunHooks):
        async def on_llm_end(self, context, agent, response):
            assert len(response.output) == 2
            raise InfrastructureError("整批拒绝")

    model = testing.ScriptedModel(
        [
            testing.ModelStep(
                output=[
                    testing.function_call("contract_echo", {"value": "甲"}, call_id="a"),
                    testing.function_call("contract_echo", {"value": "乙"}, call_id="b"),
                ]
            )
        ]
    )
    with pytest.raises(InfrastructureError, match="整批拒绝"):
        asyncio.run(invoke(model, tools=[contract_echo], hooks=Deny()))
    assert executed == []
    model.assert_complete()


def test_function_tools_are_serial_even_for_multi_call_response(sdk, testing):
    active = 0
    maximum = 0

    @sdk.function_tool(failure_error_function=None)
    async def contract_echo(value: str) -> str:
        """异步串行契约。"""
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0)
        active -= 1
        return value

    model = testing.ScriptedModel(
        [
            [testing.function_call("contract_echo", {"value": v}, call_id=v) for v in ("a", "b")],
            [testing.assistant_message("结束")],
        ]
    )
    asyncio.run(invoke(model, tools=[contract_echo]))
    assert active == 0 and maximum == 1
    model.assert_complete()


@pytest.mark.parametrize("timeout_at", ["model", "tool", "run", "cancel"])
def test_timeout_cancels_body_and_caller_owns_cleanup(sdk, testing, timeout_at):
    events = []

    async def delay():
        try:
            events.append("开始")
            await asyncio.Event().wait()
        finally:
            events.append("主体停止")

    @sdk.function_tool(failure_error_function=None)
    async def contract_wait() -> str:
        """无副作用的可取消工具。"""
        await delay()
        return "不可到达"

    async def responder(call):
        await delay()
        return [testing.assistant_message("不可到达")]

    async def scenario():
        model = testing.ScriptedModel(
            [
                testing.ModelStep(responder=responder)
                if timeout_at == "model"
                else [testing.function_call("contract_wait", {}, call_id="wait")]
            ]
        )
        options = dict(tools=[contract_wait], model_timeout=0.03, run_timeout=1)
        if timeout_at in {"tool", "run"}:
            options["run_timeout"] = 0.03
        try:
            if timeout_at == "cancel":
                task = asyncio.create_task(invoke(model, **options))
                async with asyncio.timeout(1):
                    while not events:
                        if task.done():
                            await task
                        await asyncio.sleep(0)
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            else:
                from agents.exceptions import ModelTimeoutError

                expected = ModelTimeoutError if timeout_at == "model" else TimeoutError
                with pytest.raises(expected):
                    await invoke(model, **options)
        finally:
            # 执行资源的异步清理位于 SDK 取消域之外，由宿主拥有。
            await asyncio.sleep(0)
            events.append("外层清理")
        model.assert_complete()
        assert events == ["开始", "主体停止", "外层清理"]

    asyncio.run(scenario())


@pytest.mark.parametrize("origin", ["model", "tool", "input_filter"])
@pytest.mark.parametrize("error_type", [InfrastructureError, OSError])
def test_infrastructure_errors_propagate_without_becoming_tool_success(
    sdk, testing, origin, error_type
):
    error = error_type("注入基础设施错误")

    @sdk.function_tool(failure_error_function=None)
    async def contract_error() -> str:
        """显式传播基础设施异常。"""
        raise error

    def boundary(data):
        raise error

    model = testing.ScriptedModel(
        [
            testing.ModelStep(error=error)
            if origin == "model"
            else [testing.function_call("contract_error", {}, call_id="error")]
        ]
    )
    with pytest.raises(error_type) as captured:
        asyncio.run(
            invoke(
                model,
                tools=[contract_error],
                input_filter=boundary if origin == "input_filter" else None,
            )
        )
    assert captured.value is error
    if origin != "input_filter":
        model.assert_complete()


def test_script_exhaustion_and_unconsumed_steps_are_errors(testing):
    model = testing.ScriptedModel([])
    with pytest.raises(testing.UnexpectedModelCall):
        asyncio.run(invoke(model))
    model = testing.ScriptedModel(
        [[testing.assistant_message("已结束")], [testing.assistant_message("多余")]]
    )
    asyncio.run(invoke(model))
    with pytest.raises(testing.UnconsumedModelSteps):
        model.assert_complete()


def test_model_error_is_not_retried(testing):
    error = InfrastructureError("不重试")
    model = testing.ScriptedModel(
        [testing.ModelStep(error=error), [testing.assistant_message("多余")]]
    )
    with pytest.raises(InfrastructureError):
        asyncio.run(invoke(model))
    assert len(model.calls) == 1 and model.remaining_steps == 1


@pytest.mark.parametrize("model", [None, "contract-model"])
def test_implicit_model_selection_is_rejected(sdk, model):
    with pytest.raises(ReproPatchError, match="显式传入"):
        asyncio.run(invoke(model))


def test_unknown_tool_is_an_error(testing):
    from agents.exceptions import ModelBehaviorError

    model = testing.ScriptedModel([[testing.function_call("unregistered", {}, call_id="unknown")]])
    with pytest.raises(ModelBehaviorError):
        asyncio.run(invoke(model))
    model.assert_complete()


@pytest.mark.parametrize(
    "usage",
    [
        None,
        {},
        {"input_tokens": 0},
        {"output_tokens": 5},
        {"input_tokens": True, "output_tokens": -1, "total_tokens": "3"},
    ],
)
def test_missing_usage_remains_unknown(sdk, usage):
    response = sdk.ModelResponse(output=[], usage=sdk.Usage(), response_id=None, raw_usage=usage)
    actual = raw_token_usage(response)
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        value = usage.get(key) if usage else None
        assert actual[key] == (value if type(value) is int and value >= 0 else None)


def test_native_json_loader_and_synthetic_partial_usage(tmp_path, sdk, testing):
    path = tmp_path / "script.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "steps": [
                    {
                        "output": [
                            testing.function_call(
                                "contract_echo", {"value": "合成"}, call_id="echo"
                            ).model_dump(mode="json", exclude_none=True)
                        ]
                    },
                    {
                        "output": [
                            testing.assistant_message("完成").model_dump(
                                mode="json", exclude_none=True
                            )
                        ],
                        "usage": {"input_tokens": 0},
                    },
                ],
            }
        )
    )

    @sdk.function_tool(failure_error_function=None)
    async def contract_echo(value: str) -> str:
        """无副作用回传。"""
        return value

    model = load_sdk_script(path)
    result = asyncio.run(invoke(model, tools=[contract_echo]))
    model.assert_complete()
    assert result.final_output == "完成"
    assert raw_token_usage(result.raw_responses[0])["input_tokens"] is None
    assert raw_token_usage(result.raw_responses[1])["input_tokens"] == 0


@pytest.mark.parametrize(
    "step",
    [
        {"output": [], "error": "隐藏代码"},
        {"output": [], "responder": "module.callback"},
        {"output": [{"type": "unknown", "id": "x"}]},
        {"output": [{"type": "message", "role": "user"}]},
        {"output": [{"type": "function_call", "name": "x", "arguments": {}, "call_id": "a"}]},
        {"output": [], "usage": {"input_tokens": True}},
        {"output": [], "usage": {"output_tokens": -1}},
        {"output": [], "usage": {"total_tokens": 1.0}},
        {"output": [], "usage": {"requests": 1}},
        {"output": [], "usage": None},
    ],
)
def test_loader_rejects_non_native_or_executable_step(tmp_path, step):
    path = tmp_path / "script.json"
    path.write_text(json.dumps({"version": 1, "steps": [step]}))
    with pytest.raises(ReproPatchError, match="INVALID_SDK_SCRIPT"):
        load_sdk_script(path)


@pytest.mark.parametrize(
    "status,expected",
    [
        (401, "MODEL_AUTH_ERROR"),
        (403, "MODEL_AUTH_ERROR"),
        (429, "MODEL_RATE_LIMIT"),
        (500, "MODEL_SERVER_ERROR"),
        (400, "MODEL_CONTEXT_ERROR"),
        (307, "MODEL_REQUEST_FAILED"),
    ],
)
def test_http_errors_are_redacted_and_never_retried_or_redirected(
    status, expected, monkeypatch, caplog, capsys, sdk
):
    import httpx2

    sentinel = "synthetic-contract-key-do-not-export"
    monkeypatch.setenv("REPROPATCH_CONTRACT_KEY", sentinel)
    caplog.set_level(logging.DEBUG)
    attempts = []

    @sdk.function_tool(failure_error_function=None)
    async def contract_echo(value: str) -> str:
        """用于验证非并行工具请求参数。"""
        return value

    def handle(request):
        attempts.append(request)
        assert request.headers["authorization"] == "Bearer " + sentinel
        payload = json.loads(request.content)
        assert payload["model"] == "contract-model"
        assert payload["store"] is False
        assert payload["parallel_tool_calls"] is False
        assert payload["include"] == ["reasoning.encrypted_content"]
        assert payload["max_output_tokens"] == 256
        assert "previous_response_id" not in payload and "conversation" not in payload
        assert sentinel not in request.content.decode()
        return httpx2.Response(
            status,
            json={
                "error": {
                    "message": sentinel,
                    "code": "context_length_exceeded" if status == 400 else None,
                }
            },
            headers={"location": "https://untrusted.invalid/", "x-request-id": sentinel},
        )

    async def scenario():
        client = httpx2.AsyncClient(transport=httpx2.MockTransport(handle), trust_env=False)
        async with responses_model(
            "contract-model",
            model_timeout=1,
            allow_paid=True,
            base_url="https://contract.invalid/v1",
            key_env="REPROPATCH_CONTRACT_KEY",
            http_client=client,
        ) as model:
            with pytest.raises(ReproPatchError, match=expected) as captured:
                await invoke(model, tools=[contract_echo])
            rendered = "".join(traceback.format_exception(captured.value))
            assert sentinel not in rendered
        assert client.is_closed

    asyncio.run(scenario())
    assert len(attempts) == 1
    output = capsys.readouterr()
    assert sentinel not in caplog.text + output.out + output.err
    assert all(sentinel not in repr(record.__dict__) for record in caplog.records)


@pytest.mark.parametrize("kind", ["timeout", "connection"])
def test_transport_errors_have_one_attempt_and_safe_failure(kind, monkeypatch, sdk):
    import httpx2

    attempts = []
    monkeypatch.setenv("REPROPATCH_CONTRACT_KEY", "synthetic-contract-key")

    def handle(request):
        attempts.append(request)
        error = httpx2.ReadTimeout if kind == "timeout" else httpx2.ConnectError
        raise error("synthetic-contract-key", request=request)

    async def scenario():
        async with responses_model(
            "contract-model",
            model_timeout=1,
            allow_paid=True,
            key_env="REPROPATCH_CONTRACT_KEY",
            base_url="https://contract.invalid/v1",
            http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handle)),
        ) as model:
            expected = "MODEL_REQUEST_TIMEOUT" if kind == "timeout" else "MODEL_CONNECTION_ERROR"
            with pytest.raises(ReproPatchError, match=expected):
                await invoke(model)

    asyncio.run(scenario())
    assert len(attempts) == 1


def test_http_success_uses_native_response_and_keeps_partial_raw_usage(monkeypatch, testing):
    import httpx2

    monkeypatch.setenv("REPROPATCH_CONTRACT_KEY", "synthetic-contract-key")
    attempts = []

    def handle(request):
        attempts.append(request)
        return httpx2.Response(
            200,
            json={
                "id": "response-contract",
                "object": "response",
                "created_at": 1,
                "model": "contract-model",
                "status": "completed",
                "parallel_tool_calls": False,
                "tools": [],
                "tool_choice": "auto",
                "temperature": 1,
                "top_p": 1,
                "output": [testing.assistant_message("完成").model_dump(mode="json")],
                "usage": {"input_tokens": 0},
            },
        )

    async def scenario():
        async with responses_model(
            "contract-model",
            model_timeout=1,
            allow_paid=True,
            base_url="https://contract.invalid/v1",
            key_env="REPROPATCH_CONTRACT_KEY",
            http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handle)),
        ) as model:
            result = await invoke(model)
        assert result.final_output == "完成"
        assert raw_token_usage(result.raw_responses[0]) == {
            "input_tokens": 0,
            "output_tokens": None,
            "total_tokens": None,
        }

    asyncio.run(scenario())
    assert len(attempts) == 1
