"""Zero-network SDK smoke for optional early selection and observation recall."""

import json
import socket
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from repropatch.artifacts import EvidenceRef
from repropatch.context import (
    REQUEST_PURPOSE,
    ContextPolicy,
    ContextState,
    complete_rounds,
    encoded,
)
from repropatch.context_early import SELECTION_INSTRUCTIONS
from repropatch.harness import Harness
from repropatch.workspace import git

pytestmark = pytest.mark.sdk


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("early-context smoke uses no real network")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


@pytest.fixture
def long_task(task):
    path = task.repository / "src/stats.cpp"
    with path.open("a") as stream:
        stream.write(
            "\n"
            + "".join(
                f"// fixture context row {i}: source range selection evidence.\n"
                for i in range(100)
            )
        )
    git(task.repository, "add", "src/stats.cpp")
    git(
        task.repository,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@localhost",
        "commit",
        "-m",
        "context fixture",
    )
    return replace(
        task,
        revision=git(task.repository, "rev-parse", "HEAD").strip(),
        budget=replace(task.budget, max_steps=12, max_tool_calls=30),
    )


def usage(incoming=100, outgoing=10):
    return {
        "input_tokens": incoming,
        "output_tokens": outgoing,
        "total_tokens": incoming + outgoing,
        "input_tokens_details": {"cached_tokens": incoming // 2},
    }


def read():
    from agents.testing import function_call

    return function_call("read_file", {"path": "src/stats.cpp"}, call_id="read")


def search(call_id="search"):
    from agents.testing import function_call

    return function_call(
        "search_code", {"query": "int best", "path": "src/stats.cpp"}, call_id=call_id
    )


def listing(call_id="list"):
    from agents.testing import function_call

    return function_call("list_directory", {"path": "src"}, call_id=call_id)


def edit():
    from agents.testing import function_call

    return function_call(
        "edit_file",
        {"path": "src/stats.cpp", "old": "int best = 0;", "new": "int best = samples.front();"},
        call_id="edit",
    )


def harness_for(task, tmp_path, model, **options):
    from conftest import SimulatedSandbox

    return Harness(
        task,
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        context_policy=options.pop(
            "context_policy",
            ContextPolicy(early_observation_reduction=True, observation_recall=True),
        ),
        **options,
    )


def test_sdk_delayed_selection_shared_budget_and_readonly_recall(long_task, tmp_path):
    from agents.testing import ModelStep, ScriptedModel, assistant_message, function_call

    def select(call):
        assert call.system_instructions == SELECTION_INSTRUCTIONS
        assert not call.tools
        target = json.loads(call.input[0]["content"])["target"]
        assert target["tool_id"] == "s000001.t01"
        answer = {
            "decision": "SELECT",
            "tool_id": target["tool_id"],
            "source_tree_sha256": target["source_tree_sha256"],
            "ranges": [[target["start_line"], target["start_line"] + 11]],
        }
        return ModelStep(output=[assistant_message(json.dumps(answer))], raw_usage=usage(200, 20))

    def after_selection(call):
        assert call.system_instructions != SELECTION_INSTRUCTIONS
        assert "read_observation" in {t.name for t in call.tools}
        complete_rounds(call.input)
        output = next(
            i
            for i in call.input
            if i.get("call_id") == "read" and i.get("type") == "function_call_output"
        )
        value = json.loads(output["output"])
        assert value["data"]["context_view"] == "selected_source_lines"
        assert value["data"]["snippets"][0]["start_line"] == 1
        return ModelStep(
            output=[
                function_call(
                    "read_observation",
                    {"tool_id": "s000001.t01", "offset": 0, "max_chars": 80},
                    call_id="recall",
                )
            ],
            raw_usage=usage(),
        )

    model = ScriptedModel(
        [
            ModelStep(output=[read(), listing("same-response")], raw_usage=usage()),
            ModelStep(output=[search()], raw_usage=usage()),
            ModelStep(output=[listing()], raw_usage=usage()),
            ModelStep(responder=select),
            ModelStep(responder=after_selection),
            ModelStep(output=[edit()], raw_usage=usage()),
            ModelStep(output=[assistant_message("完成")], raw_usage=usage()),
        ]
    )
    harness = harness_for(long_task, tmp_path, model)
    report = harness.run()
    assert report["outcome"] == "ACCEPTED", report
    assert report["model_steps"] == 7 and len(model.calls) == 7
    state = report["context"]["early_observation_state"]
    assert state["repair_responses"] == 6
    assert state["metrics"]["auxiliary_requests"] == state["metrics"]["trigger_count"] == 1
    assert state["metrics"]["auxiliary_input_tokens"] == 200
    assert state["metrics"]["auxiliary_output_tokens"] == 20
    assert state["metrics"]["auxiliary_cached_input_tokens"] == 100
    assert state["metrics"]["auxiliary_unknown_usage"] == 0
    assert report["usage"]["input_tokens"] == 800 and report["usage"]["output_tokens"] == 80
    assert state["metrics"]["recall_success"] == 1
    assert "s000005.t01" not in state["observations"]
    assert state["observations"]["s000001.t01"]["repair_response"] == 1
    assert state["observations"]["s000001.t02"]["repair_response"] == 1
    assert all(call.tools for call in model.calls[:3])
    raw = json.loads((harness.directory / "agent/tool-results/s000001.t01.json").read_text())
    assert "fixture context row 99" in raw["data"]["text"]
    assert "context_view" not in raw["data"]
    model.assert_complete()


@pytest.mark.parametrize(
    "answer", ['{"decision":"KEEP"}', '{"decision":"SELECT","ranges":[[0,999999]]}', "invalid JSON"]
)
def test_invalid_or_keep_selection_retains_raw_and_resets_repair_body(long_task, tmp_path, answer):
    from agents.testing import ModelStep, ScriptedModel, assistant_message

    def check_repair(call):
        assert call.system_instructions != SELECTION_INSTRUCTIONS and call.tools
        old = next(
            i
            for i in call.input
            if i.get("type") == "function_call_output" and i.get("call_id") == "read"
        )
        assert "fixture context row 99" in json.loads(old["output"])["data"]["text"]
        return ModelStep(output=[edit()], raw_usage=usage())

    model = ScriptedModel(
        [
            [read()],
            [search()],
            [listing()],
            [assistant_message(answer)],
            ModelStep(responder=check_repair),
            [assistant_message("完成")],
        ]
    )
    report = harness_for(long_task, tmp_path, model).run()
    assert report["outcome"] == "ACCEPTED", report
    metric = report["context"]["early_observation_state"]["metrics"]
    assert metric["attempts"] == 1 and metric["trigger_count"] == 0
    assert metric["auxiliary_requests"] == 1
    model.assert_complete()


def test_last_remaining_request_is_repair_and_not_selection(long_task, tmp_path):
    from agents.testing import ScriptedModel, assistant_message

    model = ScriptedModel([[read()], [search()], [edit()], [assistant_message("完成")]])
    task = replace(long_task, budget=replace(long_task.budget, max_steps=4))
    report = harness_for(task, tmp_path, model).run()
    assert report["outcome"] == "ACCEPTED", report
    metric = report["context"]["early_observation_state"]["metrics"]
    assert metric["auxiliary_requests"] == 0
    assert metric["skip_counts"]["insufficient_request_budget"] == 1
    assert all(call.tools for call in model.calls)
    model.assert_complete()


def test_common_recall_splits_baseline_equivalently_and_keeps_contract(task, tmp_path):
    from agents.testing import ScriptedModel, assistant_message, function_call

    from repropatch.tools import model_evaluation

    model = ScriptedModel(
        [
            [
                function_call(
                    "read_observation", {"tool_id": "baseline", "max_chars": 4000}, call_id="base"
                )
            ],
            [edit()],
            [assistant_message("完成")],
        ]
    )
    harness = harness_for(
        task, tmp_path, model, context_policy=ContextPolicy(observation_recall=True)
    )
    report = harness.run()
    assert report["outcome"] == "ACCEPTED", report
    initial = model.calls[0].input
    assert len(initial) == 2
    contract = json.loads(initial[0]["content"])
    observed = json.loads(initial[1]["content"])["baseline_observation"]
    assert observed == json.loads(encoded(model_evaluation(harness.baseline.to_dict())))
    assert contract["task"] == task.prompt and "baseline" not in contract
    assert "repair_state" not in contract
    assert report["context"]["fixed_items"] == initial[:1]
    state = report["context"]["early_observation_state"]
    assert state["observations"]["baseline"]["first_seen_repair"] == 1
    recall = json.loads((harness.directory / "agent/tool-results/s000001.t01.json").read_text())[
        "data"
    ]
    assert recall["tool_id"] == "baseline" and recall["view"] == "historical_observation_json"
    original = (
        EvidenceRef(**recall["original_result_ref"])
        .read(harness.directory, limit=2 * 1024 * 1024)
        .decode()
    )
    assert json.loads(original) == observed
    assert original[:4000] == recall["text"]
    assert state["metrics"]["auxiliary_requests"] == 0
    model.assert_complete()


@pytest.mark.parametrize("pause_step", [3, 4])
def test_actual_pause_resume_preserves_candidates_and_auxiliary_usage(
    long_task, tmp_path, pause_step
):
    from agents.testing import assistant_message
    from conftest import SimulatedSandbox

    from repropatch.models import load_sdk_script
    from repropatch.recovery import read_checkpoint, resume_run

    outputs = [
        [read()],
        [search()],
        [listing()],
        [assistant_message('{"decision":"KEEP"}')],
        [edit()],
        [assistant_message("完成")],
    ]
    script = {
        "version": 1,
        "steps": [
            {
                "output": [x.model_dump(mode="json", exclude_none=True) for x in output],
                "usage": {
                    key: value for key, value in usage().items() if key != "input_tokens_details"
                },
            }
            for output in outputs
        ],
    }
    path = tmp_path / "script.json"
    path.write_bytes(encoded(script))
    harness = harness_for(
        long_task,
        tmp_path,
        load_sdk_script(path),
        pause_after_step=pause_step,
        script_source=path.read_bytes(),
    )
    paused = harness.run()
    assert paused["paused"], paused
    manifest, _ = read_checkpoint(harness.directory)
    state = json.loads(
        EvidenceRef(**manifest["context_state"]).read(harness.directory, limit=2 * 1024 * 1024)
    )
    early = state["early_observation_state"]
    assert early["repair_responses"] == 3
    assert early["attempts_used"] == int(pause_step == 4)
    assert early["observations"]["s000001.t01"]["status"] == (
        "kept" if pause_step == 4 else "pending"
    )
    result = resume_run(harness.directory, sandbox_factory=SimulatedSandbox)
    assert result["outcome"] == "ACCEPTED", result
    final = result["context"]["early_observation_state"]
    assert final["repair_responses"] == 5 and final["metrics"]["auxiliary_requests"] == 1
    assert result["model_steps"] == 6 and result["usage"]["input_tokens"] == 600
    assert final["observations"]["baseline"]["first_seen_repair"] == 1


def test_failed_auxiliary_preserves_unknown_usage_while_repair_continues(long_task, tmp_path):
    from agents.testing import ModelStep, ScriptedModel, assistant_message

    from repropatch.errors import ReproPatchError

    def fail(_):
        raise ReproPatchError("MODEL_REQUEST_TIMEOUT")

    model = ScriptedModel(
        [
            ModelStep(output=[read()], raw_usage=usage()),
            ModelStep(output=[search()], raw_usage=usage()),
            ModelStep(output=[listing()], raw_usage=usage()),
            ModelStep(responder=fail),
            ModelStep(output=[edit()], raw_usage=usage()),
            ModelStep(output=[assistant_message("完成")], raw_usage=usage()),
        ]
    )
    report = harness_for(long_task, tmp_path, model).run()
    assert report["outcome"] == "ACCEPTED", report
    state = report["context"]["early_observation_state"]
    assert state["metrics"]["auxiliary_unknown_usage"] == 1
    assert state["metrics"]["auxiliary_requests"] == 1
    assert state["metrics"]["skip_counts"]["auxiliary_failed"] == 1
    assert state["observations"]["s000001.t01"]["status"] == "kept"
    assert report["usage"]["unknown_turns"] == 1
    assert report["usage"]["input_tokens"] is None
    assert report["usage"]["output_tokens"] is None
    assert report["usage"]["total_tokens"] is None
    assert report["usage"]["known_tokens"] == {
        "input_tokens": 500,
        "output_tokens": 50,
        "total_tokens": 550,
    }
    model.assert_complete()


@pytest.mark.parametrize("auxiliary_outcome", ["select", "timeout", "local_rejection"])
def test_http_sdk_meter_counts_auxiliary_and_restores_repair_contract(
    long_task, tmp_path, monkeypatch, auxiliary_outcome
):
    import httpx2
    from agents.testing import assistant_message
    from benchmark_budget import BudgetHooks, BudgetLimit, LocalUsageLedger
    from run_benchmark_agent import responses_client

    from repropatch import models
    from repropatch.models import ResponsesConfig

    monkeypatch.setenv("REPROPATCH_EARLY_TEST_KEY", "offline-fixture-key")
    policy = ContextPolicy(early_observation_reduction=True, observation_recall=True)
    attempt = "early-mock-sdk"
    ledger = LocalUsageLedger.create_scoped(
        tmp_path / "usage.sqlite3", {attempt: 24}, context_policy=policy
    )

    class ControlledHooks(BudgetHooks):
        def _request(self, request, identity):
            if REQUEST_PURPOSE.get() == "compact" and auxiliary_outcome == "local_rejection":
                raise BudgetLimit("LOCAL_TRANSPORT_LIMIT")
            return super()._request(request, identity)

    meter = ControlledHooks(ledger, attempt, tmp_path / "http", local_luna=True)
    requests, repairs, plans = (
        [],
        iter([[read()], [search()], [listing()], [edit()], [assistant_message("完成")]]),
        [],
    )

    def handle(request):
        payload = json.loads(request.content)
        purpose = REQUEST_PURPOSE.get()
        requests.append((purpose, payload))
        assert payload["reasoning"] == {"effort": "max"}
        if purpose == "compact":
            assert payload["instructions"] == SELECTION_INSTRUCTIONS
            assert payload["tools"] == [] and payload["max_output_tokens"] == 2048
            if auxiliary_outcome == "timeout":
                raise httpx2.ReadTimeout("offline injected timeout", request=request)
            target = json.loads(payload["input"][0]["content"])["target"]
            output = [
                assistant_message(
                    json.dumps(
                        {
                            "decision": "SELECT",
                            "tool_id": target["tool_id"],
                            "source_tree_sha256": target["source_tree_sha256"],
                            "ranges": [[1, 12]],
                        }
                    )
                )
            ]
            raw_usage = usage(200, 20)
        else:
            assert payload["max_output_tokens"] == 8192
            assert "read_observation" in {tool["name"] for tool in payload["tools"]}
            assert payload["instructions"] != SELECTION_INSTRUCTIONS
            output, raw_usage = next(repairs), usage()
        return httpx2.Response(
            200,
            json={
                "id": f"fixture-response-{len(requests)}",
                "object": "response",
                "created_at": 1,
                "model": "gpt-6-luna",
                "status": "completed",
                "parallel_tool_calls": False,
                "tools": [],
                "tool_choice": "auto",
                "temperature": 1,
                "top_p": 1,
                "output": [item.model_dump(mode="json", exclude_none=True) for item in output],
                "usage": raw_usage,
            },
        )

    real_responses_model = models.responses_model

    @asynccontextmanager
    async def offline_model(*args, **kwargs):
        client = responses_client(
            SimpleNamespace(provider="local-luna", reasoning_effort="max", cpa_route="public"),
            meter,
            transport=httpx2.MockTransport(handle),
        )
        async with real_responses_model(*args, http_client=client, **kwargs) as model:
            yield model
        assert client.is_closed

    original_plan = ContextState.plan

    def capture_plan(state, body):
        plans.append(deepcopy(body))
        return original_plan(state, body)

    monkeypatch.setattr(models, "responses_model", offline_model)
    monkeypatch.setattr(ContextState, "plan", capture_plan)
    model = ResponsesConfig(
        "gpt-6-luna", "https://cpa.liyinlong.me/v1", "REPROPATCH_EARLY_TEST_KEY", True
    )
    task = replace(long_task, budget=replace(long_task.budget, max_output_tokens=8192))
    harness = harness_for(task, tmp_path, model, context_policy=policy, context_meter=meter)
    report = harness.run()
    accounting = ledger.summary(attempt)
    metric = report["context"]["early_observation_state"]["metrics"]
    if auxiliary_outcome == "local_rejection":
        assert report["agent_stop_reason"] == "LOCAL_TRANSPORT_LIMIT", report
        assert accounting["requests"] == 3 and accounting["local_rejections"] == 1
        assert len(requests) == 3 and report["model_steps"] == 4
        assert metric["attempts"] == 1 and metric["auxiliary_requests"] == 0
        assert metric["auxiliary_unknown_usage"] == metric["auxiliary_input_tokens"] == 0
        return
    if auxiliary_outcome == "timeout":
        assert report["agent_stop_reason"] == "FORMAL_USAGE_UNSETTLED", report
        assert [purpose for purpose, _ in requests] == ["repair"] * 3 + ["compact"]
        assert accounting["requests"] == 4 and accounting["local_rejections"] == 1
        assert accounting["unknown_usage_requests"] == metric["auxiliary_unknown_usage"] == 1
        assert report["usage"]["input_tokens"] is None
        assert accounting["known_input_tokens"] == 300
        assert metric["auxiliary_requests"] == 1 and metric["auxiliary_input_tokens"] == 0
        assert metric["skip_counts"]["auxiliary_failed"] == 1
        return
    assert report["outcome"] == "ACCEPTED", report
    assert [purpose for purpose, _ in requests] == ["repair"] * 3 + ["compact"] + ["repair"] * 2
    assert accounting["requests"] == report["model_steps"] == 6
    assert accounting["compact_requests"] == 1 and accounting["repair_requests"] == 5
    assert accounting["input_tokens"] == report["usage"]["input_tokens"] == 700
    assert accounting["output_tokens"] == report["usage"]["output_tokens"] == 70
    assert accounting["cached_input_tokens"] == 350
    assert accounting["unknown_usage_requests"] == accounting["local_rejections"] == 0
    assert metric["auxiliary_input_tokens"] == 200
    assert metric["auxiliary_output_tokens"] == 20
    assert metric["auxiliary_cached_input_tokens"] == 100
    assert metric["trigger_count"] == 1
    assert all(body["tools"] and body["max_output_tokens"] == 8192 for body in plans)


@pytest.mark.parametrize("cap_source", ["task", "context_policy"])
def test_early_then_history_reserves_final_repair_request(long_task, tmp_path, cap_source):
    from agents.testing import ModelStep, ScriptedModel, assistant_message

    policy = ContextPolicy(
        early_observation_reduction=True,
        observation_recall=True,
        state_aware_compaction=True,
        compact_trigger_tokens=16000,
        compact_target_tokens=7200,
        request_cap=5 if cap_source == "context_policy" else 24,
    )
    task = replace(
        long_task, budget=replace(long_task.budget, max_steps=5 if cap_source == "task" else 12)
    )

    def last_repair(call):
        assert call.system_instructions != SELECTION_INSTRUCTIONS
        assert call.tools
        body = {
            "model": "offline",
            "instructions": call.system_instructions,
            "max_output_tokens": task.budget.max_output_tokens,
            "tools": [
                {
                    "type": "function",
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.params_json_schema,
                    "strict": tool.strict_json_schema,
                }
                for tool in call.tools
            ],
            "input": call.input,
        }
        assert harness.context_state.estimator.estimate(body)["estimated_input_tokens"] >= 16000
        return ModelStep(output=[assistant_message("完成")], raw_usage=usage())

    model = ScriptedModel(
        [
            ModelStep(output=[read()], raw_usage=usage()),
            ModelStep(output=[search()], raw_usage=usage()),
            ModelStep(output=[edit()], raw_usage=usage(17000)),
            ModelStep(output=[assistant_message('{"decision":"KEEP"}')], raw_usage=usage()),
            ModelStep(responder=last_repair),
        ]
    )
    harness = harness_for(task, tmp_path, model, context_policy=policy)
    report = harness.run()
    assert report["outcome"] == "ACCEPTED", report
    assert report["model_steps"] == 5
    assert report["context"]["compactions"] == []
    assert report["context"]["early_observation_state"]["metrics"]["auxiliary_requests"] == 1
    model.assert_complete()


def test_runtime_limits_selection_to_four_auxiliary_requests(long_task, tmp_path):
    from agents.testing import ModelStep, ScriptedModel, assistant_message, function_call

    steps = [
        ModelStep(
            output=[
                function_call("read_file", {"path": "src/stats.cpp"}, call_id=f"read-{i}")
                for i in range(6)
            ],
            raw_usage=usage(),
        ),
        ModelStep(output=[search()], raw_usage=usage()),
        ModelStep(output=[listing()], raw_usage=usage()),
    ]
    for i in range(4):
        steps.extend(
            [
                ModelStep(output=[assistant_message('{"decision":"KEEP"}')], raw_usage=usage()),
                ModelStep(output=[edit() if i == 3 else listing(f"list-{i}")], raw_usage=usage()),
            ]
        )
    steps.append(ModelStep(output=[assistant_message("完成")], raw_usage=usage()))
    model = ScriptedModel(steps)
    task = replace(long_task, budget=replace(long_task.budget, max_steps=20))
    report = harness_for(task, tmp_path, model).run()
    assert report["outcome"] == "ACCEPTED", report
    state = report["context"]["early_observation_state"]
    assert report["model_steps"] == 12 and state["repair_responses"] == 8
    assert state["metrics"]["auxiliary_requests"] == state["attempts_used"] == 4
    assert state["metrics"]["skip_counts"]["run_attempt_limit"] == 2
    model.assert_complete()
