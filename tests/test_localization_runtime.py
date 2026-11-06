"""Real SDK boundaries for frozen localization, delivered receipts and recovery."""

import hashlib
import json
import os
import time
from dataclasses import replace
from types import SimpleNamespace

import pytest

from repropatch.artifacts import EvidenceRef
from repropatch.context import ContextPolicy, ContextState, fold_tool_output
from repropatch.errors import ReproPatchError
from repropatch.events import read_events
from repropatch.harness import Harness, instructions_for
from repropatch.localization_runtime import LocalizationSession
from repropatch.task import Task, canonical_json, inspect_image
from repropatch.workspace import SourceFile, SourceManifest, Worktree


def test_localization_state_checkpoint_roundtrip():
    state = ContextState(ContextPolicy.legacy())
    state.localization_state = {"phase": "repair", "tools_used": 8}
    restored = ContextState.restore(state.policy, state.to_dict())
    assert restored.localization_state == state.localization_state


@pytest.mark.parametrize(
    "options",
    [
        {"localization_mode": "unknown"},
        {"localization_tool_budget": True},
        {"localization_tool_budget": -1},
        {"localization_step_budget": 0},
        {"localization_mode": "bounded", "tool_mode": "shell-only"},
        {"localization_mode": "feedback", "semantic_state_enabled": True},
    ],
)
def test_localization_contract_rejects_incompatible_inputs(task, options):
    with pytest.raises(ReproPatchError, match="LOCALIZATION"):
        Harness(task, object(), **options)


def test_bounded_and_feedback_instructions_match():
    assert instructions_for(
        "legacy", localization_mode="bounded", localization_tool_budget=8
    ) == instructions_for("legacy", localization_mode="feedback", localization_tool_budget=8)


def simple_session(tmp_path, file_count):
    events = []
    entries = tuple(
        SourceFile(f"{index}.cpp", "a" * 64, 4, "100644") for index in range(file_count)
    )
    workspace = SimpleNamespace(expected_manifest=SourceManifest(entries))
    harness = SimpleNamespace(
        directory=tmp_path,
        localization_mode="native",
        localization_tool_budget=8,
        localization_step_budget=4,
        report={"model_steps": 2, "tool_calls": 1, "usage": {}},
        resources=SimpleNamespace(budget=None),
        context=SimpleNamespace(clock=SimpleNamespace(started=time.monotonic())),
        log=SimpleNamespace(emit=lambda kind, payload: events.append((kind, payload))),
    )
    toolbox = SimpleNamespace(readable=frozenset(item.path for item in entries))
    session = LocalizationSession(harness, workspace, toolbox, ContextState(ContextPolicy.legacy()))
    return session, events


def test_large_source_manifest_is_not_repeated_in_receipts(tmp_path):
    session, events = simple_session(tmp_path, 50_000)
    text = json.dumps({"ok": True, "data": {"path": "0.cpp", "text": "one\n"}})
    session.prepare_receipt("read_file", {}, text, tool_id="s000001.t01", provider_call_id="read")
    payload = events[-1][1]
    assert payload["source_files"] == {"0.cpp": "a" * 64}
    assert len(canonical_json(payload)) < 2000


def test_folded_output_remains_a_confirmed_unparsed_receipt(tmp_path):
    session, events = simple_session(tmp_path, 1)
    text = fold_tool_output(json.dumps({"data": {"text": "x" * 8000}}), 512, lambda raw: "raw.json")
    with pytest.raises(ValueError):
        json.loads(text)
    session.prepare_receipt("read_file", {}, text, tool_id="s000001.t01", provider_call_id="read")
    session.submit(
        {"input": [{"type": "function_call_output", "call_id": "read", "output": text}]}, "repair"
    )
    session.confirm_response()
    kind, payload = events[-1]
    assert kind == "localization_exposure" and payload["delivery_status"] == "confirmed"
    assert payload["receipt_format"] == "folded_text"
    assert payload["source_files"] == {}
    assert session.state["pending_receipts"] == []


def frozen_feedback(task):
    with Worktree(
        task.repository, task.repository.parent / "feedback-source", task.revision
    ) as work:
        source = work.initial_manifest.sha256
    logs = []
    for name, text in (
        ("baseline-configure.log", "configured"),
        ("baseline-build.log", "built"),
        ("baseline-ctest.log", "/src/src/stats.cpp:5: Failure\nexpected -3, got 0"),
    ):
        logs.append(
            {"name": name, "text": text, "sha256": hashlib.sha256(text.encode()).hexdigest()}
        )
    value = {
        "schema": "repropatch.localization-feedback.v1",
        "instance_id": task.id,
        "prepared_commit": task.revision,
        "source_tree_sha256": source,
        "logs": logs,
    }
    value["feedback_sha256"] = hashlib.sha256(canonical_json(value)).hexdigest()
    return value


@pytest.mark.parametrize("change", ["task", "commit", "hash", "log", "hidden", "source"])
def test_fixed_public_feedback_checks_identity_and_content(task, change):
    from repropatch.errors import InfrastructureError
    from repropatch.localization_runtime import validate_feedback

    value = frozen_feedback(task)
    source = value["source_tree_sha256"]
    if change == "task":
        value["instance_id"] = "other"
    elif change == "commit":
        value["prepared_commit"] = "a" * 40
    elif change == "hash":
        value["feedback_sha256"] = "b" * 64
    elif change == "log":
        value["logs"][2]["text"] += " changed"
    elif change == "hidden":
        value["logs"][2]["name"] = "native-oracle-ctest.log"
    else:
        source = "f" * 64
    with pytest.raises(InfrastructureError, match="LOCALIZATION_FEEDBACK"):
        validate_feedback(value, task, source_tree_sha256=source)


@pytest.mark.sdk
def test_fixed_feedback_is_exact_model_input_and_private_copy(task, tmp_path):
    from agents.testing import ScriptedModel, assistant_message, function_call
    from conftest import SimulatedSandbox

    feedback = frozen_feedback(task)
    expected = json.loads(canonical_json(feedback))
    model = ScriptedModel(
        [
            [function_call("search_files", {"query": "maximum_sample"}, call_id="find")],
            [assistant_message("Completed source review.")],
        ]
    )
    harness = Harness(
        task,
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        candidate_only=True,
        localization_mode="feedback",
        localization_tool_budget=1,
        localization_feedback=feedback,
    )
    feedback["logs"][2]["text"] = "caller mutation"
    report = harness.run()
    assert report["agent_stop_reason"] == "MODEL_FINISHED", report
    assert json.loads(model.calls[0].input[0]["content"])["baseline"] == expected
    result = next(
        v["output"] for v in model.calls[1].input if v.get("type") == "function_call_output"
    )
    assert json.loads(result)["data"]["fallback_reason"] is None
    frozen = json.loads((harness.directory / "execution-config.json").read_text())
    assert frozen["benchmark"]["localization_feedback"] == expected
    model.assert_complete()


@pytest.mark.sdk
@pytest.mark.parametrize("late_diagnostic", [False, True])
def test_source_revert_within_one_batch_invalidates_feedback(task, tmp_path, late_diagnostic):
    from agents.testing import ScriptedModel, assistant_message, function_call
    from conftest import SimulatedSandbox

    class DiagnosticSandbox(SimulatedSandbox):
        def execute_test(self, name):
            code, status, output = super().execute_test(name)
            return code, status, "/src/src/stats.cpp:5: Failure\n" + output if code else output

    search = {"query": "maximum_sample", "path": "src"}
    diagnostic = (
        [function_call("run_command", {"name": "reproduce"}, call_id="diagnostic")]
        if late_diagnostic
        else []
    )
    model = ScriptedModel(
        [
            [function_call("search_files", search, call_id="before")],
            [
                *diagnostic,
                function_call(
                    "edit_file",
                    {"path": "src/stats.cpp", "old": "int best = 0;", "new": "int best = 1;"},
                    call_id="edit",
                ),
                function_call(
                    "edit_file",
                    {"path": "src/stats.cpp", "old": "int best = 1;", "new": "int best = 0;"},
                    call_id="revert",
                ),
            ],
            [function_call("search_files", search, call_id="after")],
            [assistant_message("Reviewed the restored source.")],
        ]
    )
    harness = Harness(
        task,
        model,
        tmp_path / "runs",
        sandbox_factory=DiagnosticSandbox,
        candidate_only=True,
        localization_mode="feedback",
        localization_feedback=frozen_feedback(task),
    )
    report = harness.run()
    assert report["agent_stop_reason"] == "MODEL_FINISHED", report
    outputs = {
        item["call_id"]: json.loads(item["output"])
        for item in model.calls[-1].input
        if item.get("type") == "function_call_output"
    }
    assert outputs["before"]["data"]["fallback_reason"] is None
    assert outputs["after"]["data"]["fallback_reason"] == "stale_evidence"
    assert outputs["after"]["data"]["stale_evidence_count"] > 0
    if late_diagnostic:
        events = read_events(harness.directory, report["run_id"]).events
        (exposure,) = (
            event["payload"]
            for event in events
            if event["type"] == "localization_exposure"
            and event["payload"].get("provider_call_id") == "diagnostic"
        )
        engine = report["localization"]["engine"]
        receipt = next(
            item for item in engine["receipts"] if item["receipt_id"] == exposure["tool_call_id"]
        )
        assert exposure["source_epoch"] == receipt["source_epoch"] == 0
        assert engine["source_epoch"] == 2
        assert receipt["evidence"]
    model.assert_complete()


@pytest.mark.sdk
def test_read_only_phase_blocks_edits_then_repairs_with_exact_delivered_source(task, tmp_path):
    from agents.testing import ScriptedModel, assistant_message, function_call
    from conftest import SimulatedSandbox

    edit = {"path": "src/stats.cpp", "old": "int best = 0;", "new": "int best = samples.front();"}
    model = ScriptedModel(
        [
            [
                function_call("edit_file", edit, call_id="premature"),
                function_call("read_file", {"path": "src/stats.cpp"}, call_id="read"),
            ],
            [function_call("edit_file", edit, call_id="repair")],
            [assistant_message("Repair is complete.")],
        ]
    )
    harness = Harness(
        task,
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        candidate_only=True,
        localization_tool_budget=2,
    )
    report = harness.run()
    assert report["agent_stop_reason"] == "MODEL_FINISHED", report
    assert report["model_steps"] == 3 and report["tool_calls"] == 3
    assert report["localization"]["phase"] == "repair"
    assert report["localization"]["transition_reason"] == "tool_budget"
    events = read_events(harness.directory, report["run_id"]).events
    exposures = [e["payload"] for e in events if e["type"] == "localization_exposure"]
    assert [e["phase"] for e in exposures] == ["localization"] * 3 + ["repair"]
    denied = json.loads(
        EvidenceRef(**exposures[1]["delivered_ref"]).read(harness.directory, limit=100_000)
    )
    assert denied["error"]["code"] == "LOCALIZATION_READ_ONLY"
    receipt = (
        EvidenceRef(**exposures[2]["delivered_ref"]).read(harness.directory, limit=100_000).decode()
    )
    assert "int best = 0;" in json.loads(receipt)["data"]["text"]
    assert any(item.get("output") == receipt for item in model.calls[1].input)
    assert exposures[2]["source_tree_sha256"] != exposures[3]["source_tree_sha256"]
    model.assert_complete()


@pytest.mark.sdk
@pytest.mark.parametrize("finish", [False, True])
def test_localization_transitions_on_model_budget_or_final_text(task, tmp_path, finish):
    from agents.testing import ScriptedModel, assistant_message, function_call
    from conftest import SimulatedSandbox

    first = (
        assistant_message("Localized the defect.")
        if finish
        else function_call("read_file", {"path": "src/stats.cpp"}, call_id="read")
    )
    model = ScriptedModel([[first], [assistant_message("Finished repair review.")]])
    harness = Harness(
        task,
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        candidate_only=True,
        localization_tool_budget=8,
        localization_step_budget=1,
    )
    report = harness.run()
    assert report["agent_stop_reason"] == "MODEL_FINISHED", report
    assert report["model_steps"] == 2
    assert report["localization"]["transition_reason"] == (
        "model_finished_localization" if finish else "model_step_budget"
    )
    assert "Editing and command execution are now available" in json.dumps(model.calls[1].input)
    model.assert_complete()


@pytest.mark.sdk
def test_over_budget_batch_remains_read_only(task, tmp_path):
    from agents.testing import ScriptedModel, assistant_message, function_call
    from conftest import SimulatedSandbox

    model = ScriptedModel(
        [
            [
                function_call("read_file", {"path": "src/stats.cpp"}, call_id=f"read-{i}")
                for i in range(3)
            ],
            [assistant_message("Reviewed the source.")],
        ]
    )
    harness = Harness(
        task,
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        candidate_only=True,
        localization_tool_budget=2,
    )
    report = harness.run()
    assert report["tool_calls"] == 3
    receipts = [v for v in model.calls[1].input if v.get("type") == "function_call_output"]
    assert json.loads(receipts[-1]["output"])["error"]["code"] == "LOCALIZATION_BUDGET"
    model.assert_complete()


@pytest.mark.sdk
def test_localization_resume_restores_phase_and_cumulative_budget(task, tmp_path):
    from agents.testing import assistant_message, function_call
    from conftest import SimulatedSandbox

    from repropatch.models import load_sdk_script
    from repropatch.recovery import resume_run

    outputs = [
        [function_call("read_file", {"path": "src/stats.cpp"}, call_id="read")],
        [function_call("read_file", {"path": "src/stats.hpp"}, call_id="header")],
        [assistant_message("Reviewed the repair.")],
    ]
    script = tmp_path / "script.json"
    script.write_text(
        json.dumps(
            {
                "version": 1,
                "steps": [
                    {"output": [o.model_dump(exclude_none=True) for o in v]} for v in outputs
                ],
            }
        )
    )
    model, source = load_sdk_script(script, with_source=True)
    harness = Harness(
        replace(task, budget=replace(task.budget, max_steps=6)),
        model,
        tmp_path / "runs",
        script_source=source,
        sandbox_factory=SimulatedSandbox,
        candidate_only=True,
        pause_after_step=1,
        localization_tool_budget=2,
    )
    paused = harness.run()
    assert paused["paused"], paused
    resumed = resume_run(harness.directory, sandbox_factory=SimulatedSandbox)
    assert resumed["model_steps"] == 3 and resumed["tool_calls"] == 2, resumed
    assert resumed["context"]["localization_state"]["transition_reason"] == "tool_budget"


@pytest.mark.sdk
@pytest.mark.parametrize("mode", ["native", "bounded", "feedback"])
def test_abc_search_read_repair_uses_same_public_feedback(task, tmp_path, mode):
    from agents.testing import ScriptedModel, assistant_message, function_call
    from conftest import SimulatedSandbox

    class DiagnosticSandbox(SimulatedSandbox):
        def execute_test(self, name):
            code, status, output = super().execute_test(name)
            return code, status, "/src/src/stats.cpp:5: Failure\n" + output if code else output

    search = "search_code" if mode == "native" else "search_files"
    model = ScriptedModel(
        [
            [function_call(search, {"query": "maximum_sample", "path": "src"}, call_id="find")],
            [function_call("read_file", {"path": "src/stats.cpp"}, call_id="read")],
            [
                function_call(
                    "edit_file",
                    {
                        "path": "src/stats.cpp",
                        "old": "int best = 0;",
                        "new": "int best = samples.front();",
                    },
                    call_id="edit",
                )
            ],
            [assistant_message("Fixed the initial value.")],
        ]
    )
    harness = Harness(
        task,
        model,
        tmp_path / "runs",
        sandbox_factory=DiagnosticSandbox,
        candidate_only=True,
        localization_mode=mode,
        localization_tool_budget=2,
    )
    report = harness.run()
    assert report["agent_stop_reason"] == "MODEL_FINISHED", report
    assert report["tool_calls"] == 3 and report["model_steps"] == 4
    assert report["localization"]["receipt_count"] == 4
    if mode != "native":
        result = next(
            v["output"] for v in model.calls[1].input if v.get("type") == "function_call_output"
        )
        data = json.loads(result)["data"]
        assert any(c["path"] == "src/stats.cpp" for c in data["candidates"])
        if mode == "feedback":
            assert data["fallback_reason"] is None
    model.assert_complete()


@pytest.mark.sdk
@pytest.mark.docker
@pytest.mark.skipif(os.environ.get("REPROPATCH_DOCKER_TESTS") != "1", reason="Real Docker opt-in")
@pytest.mark.parametrize("mode", ["native", "bounded", "feedback"])
def test_localization_real_docker_independent_acceptance(task, tmp_path, mode):
    from agents.testing import ScriptedModel, assistant_message, function_call

    raw = task.to_dict()
    raw["environment"]["image"] = inspect_image(
        os.environ.get("REPROPATCH_TEST_IMAGE", "repropatch-cpp:0.1")
    ).image_id
    task = Task.from_dict(raw, task.repository.parent)
    model = ScriptedModel(
        [
            [
                function_call(
                    "search_code" if mode == "native" else "search_files",
                    {"query": "maximum_sample", "path": "src"},
                    call_id="find",
                ),
                function_call("read_file", {"path": "src/stats.cpp"}, call_id="read"),
            ],
            [
                function_call(
                    "edit_file",
                    {
                        "path": "src/stats.cpp",
                        "old": "int best = 0;",
                        "new": "int best = samples.front();",
                    },
                    call_id="edit",
                )
            ],
            [assistant_message("Fixed the initial maximum.")],
        ]
    )
    harness = Harness(
        task, model, tmp_path / "runs", localization_mode=mode, localization_tool_budget=2
    )
    report = harness.run()
    assert report["outcome"] == "ACCEPTED", report
    assert report["model_steps"] == 3 and report["tool_calls"] == 3
    assert report["usage"]["synthetic"] is True
    assert report["agent"]["http_attempts"] == 0
    model.assert_complete()
