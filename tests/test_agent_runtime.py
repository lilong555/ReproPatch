"""生产 SDK 自动路径的预算、原生附件与六工具组合契约。"""

import asyncio
import json
import socket
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import SimulatedSandbox

from repropatch.harness import Harness

pytestmark = pytest.mark.sdk


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("SDK 生产契约禁止真实网络")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


def selected(task, tmp_path, steps, **budget):
    from agents.testing import ScriptedModel

    model = ScriptedModel(steps)
    harness = Harness(
        replace(task, budget=replace(task.budget, **budget)),
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
    )
    report = harness.run()
    return report, model


def edit(call_id="edit"):
    from agents.testing import function_call

    return function_call(
        "edit_file",
        {"path": "src/stats.cpp", "old": "int best = 0;", "new": "int best = samples.front();"},
        call_id=call_id,
    )


def events(report):
    return [
        json.loads(line)
        for line in (Path(report["artifact_directory"]) / "events.jsonl").read_text().splitlines()
    ]


def test_last_turn_tools_execute_and_patch_is_independently_verified(task, tmp_path):
    report, model = selected(task, tmp_path, [[edit()]], max_steps=1)
    assert report["outcome"] == "ACCEPTED" and report["agent"]["agent_stop_reason"] == "STEP_BUDGET"
    assert report["agent"]["steps_used"] == report["agent"]["tool_calls_used"] == 1
    assert report["independent"]["evaluation_role"] == "independent"
    output = json.loads(
        (Path(report["artifact_directory"]) / "agent/tool-results/s000001.t01.json").read_text()
    )
    assert output["progress"]["model_steps_remaining"] == 0
    assert output["progress"]["source_changed"] is True
    model.assert_complete()


def test_last_turn_two_edits_are_serial_and_independently_verified(task, tmp_path):
    from agents.testing import function_call

    second = function_call(
        "edit_file",
        {"path": "src/stats.cpp", "old": "value > best", "new": "best < value"},
        call_id="second-edit",
    )
    report, model = selected(task, tmp_path, [[edit(), second]], max_steps=1)
    assert report["outcome"] == "ACCEPTED"
    assert report["agent"]["tool_calls_used"] == 2
    assert report["independent"]["evaluation_role"] == "independent"
    finished = [row for row in events(report) if row["type"] == "tool_finished"]
    assert [row["tool_call_id"] for row in finished] == ["s000001.t01", "s000001.t02"]
    patch = (Path(report["artifact_directory"]) / "patch.diff").read_text()
    assert "+    int best = samples.front();" in patch and "+        if (best < value)" in patch
    model.assert_complete()


@pytest.mark.parametrize("candidate", [False, True])
def test_over_budget_batch_has_no_partial_side_effects(task, tmp_path, candidate):
    from agents.testing import function_call

    steps = [[edit()]] if candidate else []
    steps.append(
        [
            function_call("read_file", {"path": "src/stats.cpp"}, call_id="read"),
            function_call(
                "edit_file",
                {"path": "src/stats.cpp", "old": "int best = 0;", "new": "int best = -1;"},
                call_id="denied",
            ),
        ]
    )
    report, model = selected(task, tmp_path, steps, max_tool_calls=1)
    assert report["outcome"] == ("ACCEPTED" if candidate else "BUDGET_EXHAUSTED")
    assert report["agent"]["agent_stop_reason"] == "TOOL_BUDGET"
    assert report["agent"]["tool_calls_used"] == int(candidate)
    started = [e for e in events(report) if e["type"] == "tool_started"]
    assert len(started) == int(candidate)
    model.assert_complete()


def test_context_limit_keeps_existing_candidate_without_another_request(task, tmp_path):
    from agents.testing import assistant_message, function_call

    report, model = selected(
        task,
        tmp_path,
        [
            [edit()],
            [
                assistant_message("x" * 270000),
                function_call("read_file", {"path": "src/stats.cpp"}, call_id="read"),
            ],
        ],
    )
    assert (
        report["outcome"] == "ACCEPTED" and report["agent"]["agent_stop_reason"] == "CONTEXT_LIMIT"
    )
    assert len(model.calls) == 2 and report["agent"]["steps_used"] == 2
    model.assert_complete()


@pytest.mark.parametrize("fault", ["unknown", "incomplete", "too-large", "schema", "duplicate"])
def test_protocol_failures_never_start_a_tool(task, tmp_path, fault):
    from agents.testing import ModelStep, assistant_message, function_call

    if fault == "unknown":
        output = [function_call("host_shell", {}, call_id="x")]
    elif fault == "incomplete":
        item = assistant_message("未完成")
        item.status = "incomplete"
        output = [item]
    elif fault == "too-large":
        output = [assistant_message("x" * (1024 * 1024 + 1))]
    elif fault == "duplicate":
        output = [edit("same"), edit("same")]
    else:
        output = [function_call("edit_file", {"path": "src/stats.cpp"}, call_id="bad-schema")]
    report, model = selected(task, tmp_path, [ModelStep(output=output)])
    assert report["outcome"] == "ERROR" and report["agent"]["agent_stop_reason"] == "PROTOCOL_ERROR"
    assert not [e for e in events(report) if e["type"] == "tool_started"]
    assert report["agent"]["tool_calls_used"] == int(fault == "schema")
    assert report["agent"]["steps_used"] == 1 and report["independent"] is None


def test_six_tools_and_policy_feedback_use_native_items(task, tmp_path):
    from agents.testing import ModelStep, assistant_message, function_call

    names = ["list_directory", "read_file", "search_code", "edit_file", "run_command", "run_shell"]

    def inspect(call):
        assert [tool.name for tool in call.tools] == names
        outputs = [i for i in call.input if i.get("type") == "function_call_output"]
        assert len(outputs) == 3
        data = [json.loads(item["output"]) for item in outputs]
        assert data[0]["data"]["entries"] == [
            {"name": "stats.cpp", "type": "file"},
            {"name": "stats.hpp", "type": "file"},
        ]
        assert data[1]["error"]["code"] == "PATH_NOT_READABLE"
        assert data[2]["data"]["matches"]
        for index, result in enumerate(data):
            progress = result["progress"]
            assert progress["model_steps_remaining"] == task.budget.max_steps - 1
            assert progress["tool_calls_remaining"] == task.budget.max_tool_calls - 3
            assert progress["pending_tool_calls"] == 2 - index
            assert progress["source_changed"] is False
            assert 0 <= progress["agent_seconds_remaining"] <= task.budget.wall_seconds
        return [assistant_message("结束")]

    steps = [
        ModelStep(
            output=[
                function_call(name, args, call_id=name)
                for name, args in [
                    ("list_directory", {"path": "src"}),
                    ("read_file", {"path": "/etc/passwd"}),
                    ("search_code", {"query": "maximum_sample", "path": "src"}),
                ]
            ]
        ),
        ModelStep(responder=inspect),
    ]
    report, model = selected(task, tmp_path, steps)
    assert report["outcome"] == "REJECTED" and report["reason_code"] == "NO_PATCH"
    assert len(model.calls) == 2
    model.assert_complete()


def test_raw_usage_unknown_and_native_reasoning_are_preserved(task, tmp_path):
    from agents.testing import ModelStep, assistant_message
    from openai.types.responses import ResponseReasoningItem

    reasoning = ResponseReasoningItem(
        id="reasoning", type="reasoning", summary=[], encrypted_content="opaque-synthetic"
    )
    report, model = selected(
        task,
        tmp_path,
        [
            ModelStep(output=[reasoning, edit()], raw_usage={"input_tokens": 0}),
            ModelStep(
                output=[assistant_message("完成")],
                raw_usage={"input_tokens": 3, "output_tokens": 2, "total_tokens": 5},
            ),
        ],
    )
    assert report["outcome"] == "ACCEPTED"
    assert report["usage"]["input_tokens"] == 3 and report["usage"]["output_tokens"] is None
    assert report["usage"]["known_tokens"] == {
        "input_tokens": 3,
        "output_tokens": 2,
        "total_tokens": 5,
    }
    assert report["usage"]["synthetic"] and report["cost"] is None
    native = [
        json.loads((Path(report["artifact_directory"]) / ref["path"]).read_text())
        for ref in report["native_trace"]
    ]
    assert any("opaque-synthetic" in json.dumps(value) for value in native)
    assert "opaque-synthetic" not in json.dumps(events(report))
    assert any(item.get("encrypted_content") == "opaque-synthetic" for item in model.calls[1].input)
    model.assert_complete()


@pytest.mark.parametrize("fault", ["timeout", "cancel", "error"])
def test_model_stop_preserves_unverified_candidate_and_cleans(task, tmp_path, fault):
    from agents.testing import ModelStep

    async def responder(call):
        if fault == "cancel":
            raise asyncio.CancelledError()
        if fault == "error":
            raise RuntimeError("不得泄露的供应商细节")
        await asyncio.Event().wait()

    report, model = selected(
        task, tmp_path, [[edit()], ModelStep(responder=responder)], model_timeout_seconds=1
    )
    assert report["outcome"] == ("CANCELLED" if fault == "cancel" else "ERROR")
    assert report["independent"] is None and report["candidate"] is None
    root = Path(report["artifact_directory"])
    assert b"samples.front()" in (root / "diagnostics/unverified.patch").read_bytes()
    assert report["cleanup"]["active_code_stopped"]
    assert "不得泄露" not in json.dumps(report, ensure_ascii=False)
    assert report["agent"]["steps_used"] == 2
    model.assert_complete()


def test_source_tools_never_dispatch_to_thread(task, tmp_path, monkeypatch):
    from agents.testing import assistant_message

    def forbidden(*args, **kwargs):
        raise AssertionError("领域工具不能使用后台线程")

    monkeypatch.setattr(asyncio, "to_thread", forbidden)
    report, model = selected(task, tmp_path, [[edit()], [assistant_message("完成")]])
    assert report["outcome"] == "ACCEPTED"
    model.assert_complete()


def test_initial_context_limit_does_not_start_model(task, tmp_path):
    from agents.testing import ScriptedModel, assistant_message

    model = ScriptedModel([[assistant_message("不应消费")]])
    harness = Harness(task, model, tmp_path / "runs", sandbox_factory=SimulatedSandbox)
    harness.instructions = "x" * 270000
    report = harness.run()
    assert (
        report["outcome"] == "BUDGET_EXHAUSTED"
        and report["agent"]["agent_stop_reason"] == "CONTEXT_LIMIT"
    )
    assert report["agent"]["steps_used"] == 0 and not model.calls


def test_agent_deadline_preserves_verification_reserve(task, tmp_path, monkeypatch):
    from agents.testing import ModelStep

    from repropatch.verification import RunClock

    original = RunClock.remaining
    started = False

    async def wait(call):
        nonlocal started
        started = True
        await asyncio.Event().wait()

    def remaining(self, role):
        value = original(self, role)
        if role == "agent_check":
            return min(value, 1.0)
        return value

    monkeypatch.setattr(RunClock, "remaining", remaining)
    report, model = selected(task, tmp_path, [[edit()], ModelStep(responder=wait)])
    assert started and report["outcome"] == "ACCEPTED"
    assert report["agent"]["agent_stop_reason"] == "AGENT_DEADLINE"
    assert report["independent"] is not None
    model.assert_complete()


@pytest.mark.parametrize("fail_after_edit", [False, True])
def test_responses_configuration_uses_same_harness_and_closes_client(
    task, tmp_path, monkeypatch, fail_after_edit, caplog
):
    import httpx2
    from agents.testing import assistant_message

    import repropatch.models
    from repropatch.models import ResponsesConfig, responses_model

    sentinel = "synthetic-harness-key-do-not-export"
    monkeypatch.setenv("REPROPATCH_CONTRACT_KEY", sentinel)
    requests = []

    def handle(request):
        assert request.headers["authorization"] == "Bearer " + sentinel
        requests.append(request)
        if len(requests) == 2 and fail_after_edit:
            return httpx2.Response(500, json={"error": {"message": sentinel}})
        output = [edit()] if len(requests) == 1 else [assistant_message("完成")]
        return httpx2.Response(
            200,
            json={
                "id": f"response-{len(requests)}",
                "object": "response",
                "created_at": 1,
                "status": "completed",
                "model": "contract-model",
                "parallel_tool_calls": False,
                "tools": [],
                "tool_choice": "auto",
                "temperature": 1,
                "top_p": 1,
                "output": [item.model_dump(mode="json") for item in output],
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            },
        )

    client = httpx2.AsyncClient(transport=httpx2.MockTransport(handle), trust_env=False)

    def factory(*args, **kwargs):
        return responses_model(*args, http_client=client, **kwargs)

    monkeypatch.setattr(repropatch.models, "responses_model", factory)
    config = ResponsesConfig(
        "contract-model", "https://contract.invalid/v1", "REPROPATCH_CONTRACT_KEY", True
    )
    report = Harness(task, config, tmp_path / "runs", sandbox_factory=SimulatedSandbox).run()
    assert report["outcome"] == ("ERROR" if fail_after_edit else "ACCEPTED"), report
    if fail_after_edit:
        assert report["reason_code"] == "MODEL_SERVER_ERROR" and report["independent"] is None
        assert report["usage"]["input_tokens"] is None and report["usage"]["unknown_turns"] == 1
    else:
        assert report["usage"]["input_tokens"] == 0 and report["usage"]["unknown_turns"] == 0
    assert client.is_closed and len(requests) == 2
    assert (
        report["engine"]["kind"] == "agents-sdk"
        and report["engine"]["model_name"] == "contract-model"
    )
    assert report["agent"]["http_attempts"] is None and not report["usage"]["synthetic"]
    assert sentinel not in json.dumps(report) + caplog.text
    for ref in report["native_trace"]:
        assert sentinel not in (Path(report["artifact_directory"]) / ref["path"]).read_text()
    import runpy

    gate = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/check_live_gate.py"))
    observed = gate["live_observations"](report["artifact_directory"])
    assert observed["status"] == ("failed" if fail_after_edit else "passed")
    assert bool(observed["tool_round_trips"]) is (not fail_after_edit)
