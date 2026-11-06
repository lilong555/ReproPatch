"""Offline SDK regressions for source delivery and localization request budgets."""

import hashlib
import json
from dataclasses import replace

import pytest

from repropatch.artifacts import EvidenceRef
from repropatch.context import SUMMARY_KEYS, ContextPolicy
from repropatch.events import read_events
from repropatch.harness import Harness
from repropatch.recovery import read_checkpoint

pytestmark = pytest.mark.sdk


@pytest.fixture(params=("native", "bounded", "feedback"))
def mode(request):
    return request.param


def read_receipt(harness, events):
    (prepared,) = (
        event["payload"]
        for event in events
        if event["type"] == "localization_receipt_prepared"
        and event["payload"]["tool_name"] == "read_file"
    )
    assert prepared["delivery_status"] == "prepared"
    assert prepared["provider_call_id"] == "read"
    assert set(prepared["source_files"]) == {"src/stats.cpp"}
    reference = EvidenceRef(**prepared["delivered_ref"])
    raw = reference.read(harness.directory, limit=reference.size_bytes)
    assert hashlib.sha256(raw).hexdigest() == reference.sha256
    assert "int best = 0;" in json.loads(raw)["data"]["text"]
    assert not any(
        event["type"] == "localization_exposure"
        and event["payload"]["tool_call_id"] == prepared["tool_call_id"]
        for event in events
    )
    return prepared, raw.decode("utf-8")


def test_last_request_read_is_prepared_without_source_exposure(task, tmp_path, mode):
    from agents.testing import ScriptedModel, function_call
    from conftest import SimulatedSandbox

    model = ScriptedModel([[function_call("read_file", {"path": "src/stats.cpp"}, call_id="read")]])
    harness = Harness(
        replace(task, budget=replace(task.budget, max_steps=1)),
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        candidate_only=True,
        localization_mode=mode,
        localization_tool_budget=8,
    )
    report = harness.run()
    assert report["agent_stop_reason"] == "STEP_BUDGET", report
    assert report["model_steps"] == report["tool_calls"] == len(model.calls) == 1
    events = read_events(harness.directory, report["run_id"]).events
    prepared, _ = read_receipt(harness, events)
    assert not any(
        item.get("type") == "function_call_output" and item.get("call_id") == "read"
        for call in model.calls
        for item in call.input
    )
    state = report["context"]["localization_state"]
    assert [entry["payload"] for entry in state["pending_receipts"]] == [prepared]
    assert state["receipt_count"] == 2
    assert state["exposure_count"] == 1
    assert [
        event["payload"]["tool_name"]
        for event in events
        if event["type"] == "localization_exposure"
    ] == ["baseline"]
    model.assert_complete()


def test_pause_persists_receipt_without_submitting_its_carrier(task, tmp_path, mode):
    from agents.testing import function_call
    from conftest import SimulatedSandbox

    from repropatch.models import sdk_script_bytes

    output = function_call("read_file", {"path": "src/stats.cpp"}, call_id="read")
    source = json.dumps(
        {"version": 1, "steps": [{"output": [output.model_dump(exclude_none=True)]}]}
    ).encode()
    model = sdk_script_bytes(source)
    harness = Harness(
        replace(task, budget=replace(task.budget, max_steps=6)),
        model,
        tmp_path / "runs",
        script_source=source,
        sandbox_factory=SimulatedSandbox,
        candidate_only=True,
        pause_after_step=1,
        localization_mode=mode,
        localization_tool_budget=8,
    )
    report = harness.run()
    assert report["paused"], report
    snapshot = read_events(harness.directory, report["run_id"])
    assert (
        snapshot.run["steps_used"] == snapshot.run["tool_calls_admitted"] == len(model.calls) == 1
    )
    prepared, text = read_receipt(harness, snapshot.events)
    assert [event["step_id"] for event in snapshot.events if event["type"] == "model_started"] == [
        1
    ]
    assert not any(item.get("call_id") == "read" for item in model.calls[0].input)

    checkpoint, _ = read_checkpoint(harness.directory, snapshot)
    assert checkpoint["schema_version"] == 2
    assert checkpoint["counters"] == {"steps_used": 1, "tool_calls_admitted": 1}
    reference = EvidenceRef(**checkpoint["context_state"])
    context = json.loads(reference.read(harness.directory, limit=reference.size_bytes))
    state = context["localization_state"]
    assert state["phase"] == "localization"
    assert state["model_steps"] == state["tools_used"] == state["exposure_count"] == 1
    assert [entry["payload"] for entry in state["pending_receipts"]] == [prepared]
    reference = EvidenceRef(**checkpoint["native_next_input"])
    native = json.loads(reference.read(harness.directory, limit=reference.size_bytes))
    assert any(
        item.get("type") == "function_call_output"
        and item.get("call_id") == "read"
        and item.get("output") == text
        for item in native["input"]
    )
    model.assert_complete()


def test_compactor_counts_toward_four_request_localization_cap(task, tmp_path, mode):
    from agents.testing import ScriptedModel, assistant_message, function_call
    from conftest import SimulatedSandbox

    edit = {"path": "src/stats.cpp", "old": "int best = 0;", "new": "int best = samples.front();"}
    model = ScriptedModel(
        [
            [
                assistant_message("source-review " * 4000),
                function_call("read_file", {"path": "src/stats.cpp"}, call_id="read-1"),
            ],
            [
                assistant_message(
                    json.dumps({key: "Keep examining source." for key in SUMMARY_KEYS})
                )
            ],
            [function_call("read_file", {"path": "src/stats.cpp"}, call_id="read-2")],
            [function_call("read_file", {"path": "src/stats.cpp"}, call_id="read-3")],
            [function_call("edit_file", edit, call_id="edit")],
            [assistant_message("Repair is complete.")],
        ]
    )
    harness = Harness(
        replace(task, budget=replace(task.budget, max_steps=6)),
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        candidate_only=True,
        localization_mode=mode,
        localization_tool_budget=8,
        localization_step_budget=4,
        context_policy=ContextPolicy(compact_trigger_tokens=12_000, compact_target_tokens=5000),
    )
    report = harness.run()
    assert report["agent_stop_reason"] == "MODEL_FINISHED", report
    assert report["model_steps"] == len(model.calls) == 6
    assert report["tool_calls"] == 4
    events = read_events(harness.directory, report["run_id"]).events
    starts = [event for event in events if event["type"] == "model_started"]
    assert [event["step_id"] for event in starts] == list(range(1, 7))
    assert [event["payload"]["request_purpose"] for event in starts] == [
        "repair",
        "compact",
        "repair",
        "repair",
        "repair",
        "repair",
    ]
    assert [event["payload"]["localization_phase"] for event in starts] == ["localization"] * 4 + [
        "repair"
    ] * 2
    assert sum(event["type"] == "context_compacted" for event in events) == 1
    (transition,) = [event for event in events if event["type"] == "localization_phase_finished"]
    assert transition["payload"]["reason"] == "model_step_budget"
    assert transition["payload"]["model_step"] == 4
    assert transition["payload"]["localization_model_steps"] == 4
    assert transition["payload"]["localization_tools_used"] == 3
    assert starts[3]["seq"] < transition["seq"] < starts[4]["seq"]
    assert "Editing and command execution are now available" in json.dumps(model.calls[4].input)
    (edited,) = [
        event
        for event in events
        if event["type"] == "tool_finished" and event["payload"]["name"] == "edit_file"
    ]
    assert edited["step_id"] == 5 and edited["payload"]["ok"] is True
    state = report["context"]["localization_state"]
    assert state["phase"] == "repair" and state["model_steps"] == 4
    model.assert_complete()
