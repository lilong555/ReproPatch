"""Offline ablation contracts for projections, receipts and source-bound state."""

import json
import socket
from copy import deepcopy
from dataclasses import replace

import pytest

from repropatch.context import (
    SUMMARY_KEYS,
    ContextPolicy,
    ContextState,
    complete_rounds,
    encoded,
    fold_tool_output,
)
from repropatch.context_optimization import ContextOptimizer, state_checkpoint
from repropatch.semantic_state import SemanticState
from repropatch.task import canonical_json
from repropatch.tools import Toolbox
from repropatch.workspace import Worktree

SOURCE = "a" * 64
LOG = "src/stats.cpp:5:3: error: expected value\n" * 300
ARMS = {
    "baseline": {},
    "diagnostics": {"diagnostic_extraction": True},
    "dedup": {"deduplicate_results": True},
    "state": {"state_aware_compaction": True},
    "combined": {
        "diagnostic_extraction": True,
        "deduplicate_results": True,
        "state_aware_compaction": True,
    },
}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("These tests use only offline receipts and ScriptedModel")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


def policy(**kwargs):
    return ContextPolicy(compact_trigger_tokens=48_000, compact_target_tokens=21_600, **kwargs)


def ref(identity):
    return {"path": f"agent/tool-results/{identity}.json", "sha256": "f" * 64, "size_bytes": 20_000}


def result(text=LOG, *, identity="first", source=SOURCE):
    return {
        "ok": True,
        "progress": {"model_steps_remaining": 8, "source_changed": False},
        "data": {
            "view_version": 2,
            "passed": False,
            "evaluation_id": identity,
            "evaluation_role": "agent_check",
            "source_tree_sha256": source,
            "issue_code": "TEST_FAILED",
            "diagnostic": "visible failure",
            "tests": [
                {
                    "name": "negative_values",
                    "observed_status": "failed",
                    "ctest_exit_code": 8,
                    "diagnostic": "expected -3",
                }
            ],
            "failed_commands": [
                {
                    "command_id": identity,
                    "status": "exited",
                    "exit_code": 8,
                    "stdout": text,
                    "stderr": "",
                    "duration_seconds": 1.0,
                    "stdout_log": {
                        "path": f"logs/{identity}/stdout.bin",
                        "sha256": "d" * 64,
                        "size_bytes": len(text.encode()),
                    },
                }
            ],
        },
    }


def project(optimizer, value, *, identity="first", source=SOURCE, name="run_command", args=None):
    native = fold_tool_output(
        canonical_json(value).decode(),
        optimizer.policy.tool_output_max_bytes,
        lambda raw: ref(identity)["path"],
    )
    text, events = optimizer.project(
        name,
        {"name": "reproduce"} if args is None else args,
        value,
        ref(identity),
        tool_id=identity,
        source=source,
        native=native,
    )
    return text, events, native


def test_policy_switches_are_independent_persistent_and_default_off():
    old = policy().to_dict()
    for name in ARMS["combined"]:
        assert getattr(policy(), name) is False
        assert old.get(name, False) is False
        assert name not in old
    assert ContextPolicy.from_dict(old) == policy()
    for switches in ARMS.values():
        configured = policy(**{name: switches.get(name, False) for name in ARMS["combined"]})
        serialized = configured.to_dict()
        assert {
            name: serialized[name] for name in ARMS["combined"] if name in serialized
        } == switches
        assert ContextPolicy.from_dict(json.loads(encoded(serialized))) == configured
    state = ContextState(policy())
    assert "optimization_state" not in state.to_dict()
    assert ContextState.restore(policy(), state.to_dict()).to_dict() == state.to_dict()


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {
            "transport_max_bytes": 256 * 1024,
            "response_max_bytes": 1024 * 1024,
            "context_policy_version": "legacy-256k",
            "request_cap": 12,
            "compaction_enabled": False,
        },
        {"compact_trigger_tokens": 48_000, "compact_target_tokens": 21_600, "request_cap": None},
    ],
    ids=["default", "legacy", "formal"],
)
def test_frozen_policy_exact_roundtrip_without_ablation_keys(overrides):
    frozen = {
        "context_window_tokens": 128_000,
        "compact_trigger_tokens": 80_000,
        "compact_target_tokens": 32_000,
        "max_output_tokens": 8192,
        "transport_max_bytes": 2 * 1024 * 1024,
        "response_max_bytes": 2 * 1024 * 1024,
        "request_cap": 24,
        "context_policy_version": "v1.0-unified-compaction",
        "tool_growth_tokens": 16_000,
        "estimation_margin_tokens": 8000,
        "retain_rounds": 2,
        "tool_output_max_bytes": 24 * 1024,
        "compaction_enabled": True,
        **overrides,
    }
    before = deepcopy(frozen)
    for supplied in (frozen, {**frozen, **dict.fromkeys(ARMS["combined"], False)}):
        restored = ContextPolicy.from_dict(supplied)
        assert restored.to_dict() == frozen
        assert encoded(restored.to_dict()) == encoded(frozen)
        assert canonical_json(restored.to_dict()) == canonical_json(frozen)
        assert all(getattr(restored, name) is False for name in ARMS["combined"])
    assert frozen == before
    if overrides.get("context_policy_version") == "legacy-256k":
        assert ContextPolicy.legacy().to_dict() == frozen


def test_diagnostics_preserve_unique_error_unknown_lines_exit_codes_and_raw_refs():
    state = ContextState(policy(diagnostic_extraction=True))
    optimizer = ContextOptimizer(state)
    value = result(LOG + "src/last.cpp:90: error: unique final error\nld: unknown linker failure\n")
    before = deepcopy(value)
    text, events, native = project(optimizer, value)
    projected = json.loads(text)
    command = projected["data"]["failed_commands"][0]
    diagnostics = command["stdout"]["diagnostics"]
    assert diagnostics[0] == {
        "file": "src/stats.cpp",
        "line": 5,
        "column": 3,
        "severity": "error",
        "message": "expected value",
        "occurrences": 300,
    }
    assert diagnostics[-1]["message"] == "unique final error"
    assert command["stdout"]["unparsed_output"] == "ld: unknown linker failure\n"
    assert command["exit_code"] == 8 and projected["data"]["tests"] == value["data"]["tests"]
    assert command["stdout_log"] == value["data"]["failed_commands"][0]["stdout_log"]
    assert projected["context_projection"]["raw_result_ref"] == ref("first")
    assert projected["progress"] == value["progress"] and value == before
    assert events[0]["saved_bytes"] == len(native.encode()) - len(text.encode())
    assert state.optimization_state["metrics"]["diagnostic_extraction"]["triggers"] == 1


@pytest.mark.parametrize(
    "text",
    [
        "unknown diagnostic format\n" * 1000,
        "x.cpp:1: error: tiny\n",
        "".join(f"x.cpp:{i}: error: unique-{i}\n" for i in range(100)),
        "x.cpp:1: error: " + "x" * 5000,
    ],
)
def test_unreliable_oversized_or_unprofitable_diagnostics_use_native(text):
    optimizer = ContextOptimizer(ContextState(policy(diagnostic_extraction=True)))
    output, events, native = project(optimizer, result(text))
    assert output == native and not events


@pytest.mark.parametrize("mutation", ["truncated", "output_truncated", "malformed"])
def test_incomplete_receipts_are_native_for_both_projections(mutation):
    optimizer = ContextOptimizer(
        ContextState(policy(diagnostic_extraction=True, deduplicate_results=True))
    )
    value = result()
    if mutation == "malformed":
        value["data"]["failed_commands"] = None
    else:
        value["data"]["failed_commands"][0][mutation] = True
    for _ in range(2):
        output, events, native = project(optimizer, value)
        assert output == native and not events


def test_msvc_and_failed_test_names_are_bounded_structured_receipts():
    optimizer = ContextOptimizer(ContextState(policy(diagnostic_extraction=True)))
    text = (
        "C:\\src\\stats.cpp(42,7): error C2001: expected value\n"
        "[  FAILED  ] Stats.Negative (1 ms)\n"
        "  1 - negative_values (Failed)\n"
    ) * 100
    value = {
        "ok": True,
        "data": {"status": "exited", "exit_code": 8, "stderr": text},
        "progress": {},
    }
    output, _, _ = project(optimizer, value, name="run_shell", args={"command": "ctest"})
    parsed = json.loads(output)["data"]["stderr"]
    assert parsed["diagnostics"][0]["column"] == 7
    assert {t["name"] for t in parsed["failed_tests"]} == {"Stats.Negative", "negative_values"}


def test_dedup_restores_index_keeps_first_receipt_current_metadata_and_progress():
    context = ContextState(policy(deduplicate_results=True))
    optimizer = ContextOptimizer(context)
    first = result()
    output, events, native = project(
        optimizer, first, args={"name": "reproduce", "extra": {"b": 2, "a": 1}}
    )
    assert output == native and not events
    restored = ContextState.restore(context.policy, json.loads(encoded(context.to_dict())))
    optimizer = ContextOptimizer(restored)
    second = result(identity="second")
    second["progress"] = {"model_steps_remaining": 2, "pending_tool_calls": 1}
    second["data"]["failed_commands"][0]["duration_seconds"] = 5.0
    output, events, _ = project(
        optimizer, second, identity="second", args={"extra": {"a": 1, "b": 2}, "name": "reproduce"}
    )
    projected = json.loads(output)
    assert projected["progress"] == second["progress"]
    assert projected["data"]["evaluation_id"] == "second"
    assert projected["data"]["failed_commands"][0]["duration_seconds"] == 5.0
    projection = projected["context_projection"]
    assert projection["duplicate_of"]["tool_id"] == "first"
    assert projection["duplicate_of"]["reference"] == ref("first")
    assert projection["raw_result_ref"] == ref("second") and projection["tool_executed"]
    assert len(events) == 1 and events[0]["strategy"] == "deduplicate_results"
    assert first["data"]["failed_commands"][0]["stdout"] == LOG


def test_dedup_content_phase_source_change_and_rollback_invalidate():
    optimizer = ContextOptimizer(ContextState(policy(deduplicate_results=True)))
    project(optimizer, result())
    for value, kwargs in [
        (result(LOG + "new failure"), {}),
        (result(), {"args": {"name": "verify"}}),
        (result(source="b" * 64), {"source": "b" * 64}),
        (result(), {}),
    ]:
        output, events, native = project(optimizer, value, **kwargs)
        assert output == native and not events
    assert optimizer.state["source_invalidations"] == 2
    assert project(optimizer, result(), identity="again")[1][0]["strategy"] == "deduplicate_results"


@pytest.mark.parametrize("restore", [False, True])
def test_successful_compaction_invalidates_dedup_and_rediscloses_same_receipt(restore):
    context = ContextState(policy(deduplicate_results=True))
    optimizer = ContextOptimizer(context)
    first, _, _ = project(optimizer, result())
    body = {
        "input": [
            {"role": "user", "content": "Repair src/stats.cpp"},
            {"type": "function_call", "call_id": "first", "name": "run_command", "arguments": "{}"},
            {"type": "function_call_output", "call_id": "first", "output": first},
            {"role": "assistant", "content": "visible history " * 12_000},
        ]
    }
    plan = context.plan(body)
    assert plan is not None and plan["retained"] == []
    replacement = context.replace(
        body,
        plan,
        json.dumps({key: [] for key in SUMMARY_KEYS}),
        sequence=2,
        duration_seconds=0,
    )
    assert "expected value" not in encoded(replacement).decode()
    if restore:
        context = ContextState.restore(context.policy, json.loads(encoded(context.to_dict())))
        optimizer = ContextOptimizer(context)
    output, events, native = project(optimizer, result(identity="fresh"), identity="fresh")
    assert output == native and not events
    assert json.loads(output)["data"]["failed_commands"][0]["stdout"] == LOG
    assert context.optimization_state["compaction_invalidations"] == 1
    assert context.compactions[-1]["dedup_invalidation"] == {
        "reason": "context_compaction",
        "invalidated_entries": 1,
    }
    assert context.optimization_state.get("source_invalidations", 0) == 0
    duplicate = json.loads(project(optimizer, result(identity="later"), identity="later")[0])
    assert duplicate["context_projection"]["duplicate_of"]["tool_id"] == "fresh"


@pytest.mark.parametrize(
    "invalid",
    ["invalid JSON", json.dumps({key: ["x" * 100_000] for key in SUMMARY_KEYS})],
    ids=["invalid_json", "over_budget"],
)
def test_failed_compaction_preserves_dedup_index(invalid):
    from repropatch.context import ContextLimit

    context = ContextState(policy(deduplicate_results=True))
    optimizer = ContextOptimizer(context)
    first, _, _ = project(optimizer, result())
    body = {
        "input": [
            {"role": "user", "content": "Repair src/stats.cpp"},
            {"type": "function_call", "call_id": "first", "name": "run_command", "arguments": "{}"},
            {"type": "function_call_output", "call_id": "first", "output": first},
            {"role": "assistant", "content": "visible history " * 12_000},
        ]
    }
    plan = context.plan(body)
    before = deepcopy(context.to_dict())
    with pytest.raises(ContextLimit):
        context.replace(body, plan, invalid, sequence=2, duration_seconds=0)
    assert context.to_dict() == before
    duplicate = json.loads(project(optimizer, result(identity="later"), identity="later")[0])
    assert duplicate["context_projection"]["duplicate_of"]["tool_id"] == "first"


def test_dedup_unknown_status_and_changed_full_log_hash_keep_native():
    optimizer = ContextOptimizer(ContextState(policy(deduplicate_results=True)))
    project(optimizer, result())
    for field, changed in [
        ("status", "timed_out"),
        (
            "stdout_log",
            {
                "path": "logs/new.bin",
                "sha256": "e" * 64,
                "size_bytes": len(LOG.encode()),
            },
        ),
    ]:
        value = result()
        value["data"]["failed_commands"][0][field] = changed
        output, events, native = project(optimizer, value)
        assert output == native and not events


@pytest.mark.parametrize("tool", ["read_file", "edit_file", "run_shell", "bash", "unknown"])
def test_dedup_excludes_reads_writes_shell_and_unknown_tools(tool):
    optimizer = ContextOptimizer(ContextState(policy(deduplicate_results=True)))
    for _ in range(2):
        output, events, native = project(optimizer, result(), name=tool)
        assert output == native and not events


def test_state_tracks_real_edits_discards_reverted_changes_and_marks_old_checks(
    repository, tmp_path
):
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        toolbox = Toolbox(work, ("src/stats.cpp",), None)
        semantic = SemanticState(toolbox)
        source = semantic.track_source()
        semantic.observe(
            "run_command",
            {"name": "reproduce"},
            result(source=source),
            ref("check"),
            tool_id="check",
            track_source=True,
        )
        assert (
            state_checkpoint(semantic.state, maximum=12_000)["checks"][0]["currency"] == "current"
        )
        edit = toolbox.edit_file("src/stats.cpp", "int best = 0;", "int best = -1;")
        semantic.observe(
            "edit_file",
            {"path": "src/stats.cpp"},
            {"ok": True, "data": edit},
            ref("edit"),
            tool_id="edit",
            track_source=True,
        )
        checkpoint = state_checkpoint(semantic.state, maximum=12_000)
        assert not checkpoint["checks"]
        assert checkpoint["changes"][0]["evidence"] == ref("edit")
        assert checkpoint["pending_checks"] == ["reproduce", "verify"]
        assert checkpoint["historical_check_refs"][0]["currency"] == "historical"
        assert "expected value" not in json.dumps(checkpoint)
        toolbox.edit_file("src/stats.cpp", "int best = -1;", "int best = 0;")
        semantic.track_source()
        checkpoint = state_checkpoint(semantic.state, maximum=12_000)
        assert checkpoint["source_tree_sha256"] == source
        assert checkpoint["changes"] == [] and checkpoint["checks"] == []
        assert state_checkpoint(semantic.state, maximum=10) is None
        semantic.observe(
            "run_shell",
            {"command": "cmake --build /build"},
            {"ok": True, "data": {"status": "exited", "exit_code": 2}},
            ref("shell"),
            tool_id="shell",
            track_source=True,
        )
        checkpoint = state_checkpoint(semantic.state, maximum=12_000)
        assert checkpoint["checks"][0]["exit_code"] == 2
        assert checkpoint["checks"][0]["passed"] is False
        assert checkpoint["checks"][0]["evidence"] == ref("shell")


def test_state_checkpoint_uses_native_loop_thresholds_pairs_and_transactional_replacement():
    state = ContextState(
        policy(state_aware_compaction=True),
        semantic_state={
            "source_tree_sha256": SOURCE,
            "source_epoch": 1,
            "checks": [],
            "current_changes": [],
        },
    )
    body = {
        "input": [{"role": "user", "content": "Repair src/stats.cpp"}]
        + [
            {"type": "function_call", "call_id": "c1", "name": "run_command", "arguments": "{}"},
            {"type": "function_call_output", "call_id": "c1", "output": "x" * 150_000},
        ]
    }
    baseline_plan = ContextState(policy()).plan(body)
    plan = state.plan(body)
    for key in ("fixed", "retained", "folded_items", "pre_compact_tokens", "pre_transport_bytes"):
        assert plan[key] == baseline_plan[key]
    assert "Current source-bound tool receipts" in plan["summarize"][-1]["content"]
    before = deepcopy(state.to_dict())
    from repropatch.context import ContextLimit

    with pytest.raises(ContextLimit):
        state.replace(body, plan, "invalid summary", sequence=1, duration_seconds=0)
    assert state.to_dict() == before
    summary = json.dumps({key: [] for key in SUMMARY_KEYS})
    replacement = state.replace(body, plan, summary, sequence=2, duration_seconds=0)
    complete_rounds(replacement)
    assert replacement[-1] == plan["state_checkpoint"]
    metrics = state.optimization_state["metrics"]["state_aware_compaction"]
    assert metrics["triggers"] == 1 and metrics["saved_bytes"] == 0 and metrics["added_bytes"] > 0
    assert "query_code" not in json.dumps(replacement)


@pytest.mark.sdk
@pytest.mark.parametrize("arm", ARMS)
def test_five_arms_keep_six_tools_prompt_execution_pairs_and_raw_evidence(task, tmp_path, arm):
    from agents.testing import ScriptedModel, assistant_message, function_call
    from conftest import SimulatedSandbox

    from repropatch.harness import SYSTEM, Harness

    class NoisySandbox(SimulatedSandbox):
        def execute_test(self, name):
            code, status, text = super().execute_test(name)
            return code, status, LOG + text if code else text

    model = ScriptedModel(
        [
            [function_call("run_command", {"name": "reproduce"}, call_id="one")],
            [function_call("run_command", {"name": "reproduce"}, call_id="two")],
            [assistant_message("Done")],
        ]
    )
    harness = Harness(
        replace(task, budget=replace(task.budget, max_steps=4)),
        model,
        tmp_path / "runs",
        sandbox_factory=NoisySandbox,
        context_policy=policy(**ARMS[arm]),
        candidate_only=True,
    )
    report = harness.run()
    assert report["agent_stop_reason"] == "MODEL_FINISHED", report
    model.assert_complete()
    assert len([e for e in report["evaluations"] if e["evaluation_role"] == "agent_check"]) == 2
    for call in model.calls:
        assert call.system_instructions == SYSTEM
        assert [tool.name for tool in call.tools] == [
            "list_directory",
            "read_file",
            "search_code",
            "edit_file",
            "run_command",
            "run_shell",
        ]
    assert "baseline" in json.loads(model.calls[0].input[0]["content"])
    assert "repair_state" not in json.loads(model.calls[0].input[0]["content"])
    complete_rounds(model.calls[-1].input)
    outputs = [item for item in model.calls[-1].input if item.get("type") == "function_call_output"]
    assert [item["call_id"] for item in outputs] == ["one", "two"]
    for index, item in enumerate(outputs, 1):
        raw = json.loads(
            (harness.directory / f"agent/tool-results/s{index:06d}.t01.json").read_text()
        )
        visible = json.loads(item["output"])
        assert raw["data"]["failed_commands"][0]["stdout"] == LOG + "expected -3, got 0"
        assert raw["progress"] == visible["progress"]
        assert "evidence_id" not in raw
        if arm in {"baseline", "state"}:
            assert visible == raw
    if arm != "baseline":
        metrics = report["context"]["optimization_state"]["metrics"]
        for key, enabled in ARMS[arm].items():
            if enabled and key != "state_aware_compaction":
                assert metrics[key]["triggers"] > 0, metrics
    else:
        assert "optimization_state" not in report["context"]


@pytest.mark.sdk
@pytest.mark.parametrize("arm", ["state", "combined"])
def test_runtime_compaction_retains_current_edit_and_historical_failure_receipts(
    task, tmp_path, arm
):
    from agents.testing import ModelStep, ScriptedModel, assistant_message, function_call
    from conftest import SimulatedSandbox

    from repropatch.harness import SYSTEM, Harness

    model = ScriptedModel(
        [
            [function_call("run_command", {"name": "reproduce"}, call_id="check")],
            ModelStep(
                output=[
                    assistant_message("visible history " * 12_000),
                    function_call(
                        "edit_file",
                        {
                            "path": "src/stats.cpp",
                            "old": "int best = 0;",
                            "new": "int best = samples.front();",
                        },
                        call_id="edit",
                    ),
                ],
                raw_usage={"input_tokens": 45_000, "output_tokens": 10_000, "total_tokens": 55_000},
            ),
            [assistant_message(json.dumps({key: [] for key in SUMMARY_KEYS}))],
            [assistant_message("Done")],
        ]
    )
    harness = Harness(
        replace(task, budget=replace(task.budget, max_steps=6)),
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        context_policy=policy(**ARMS[arm]),
        candidate_only=True,
    )
    report = harness.run()
    assert report["agent_stop_reason"] == "MODEL_FINISHED", report
    model.assert_complete()
    assert len(report["context"]["compactions"]) == 1
    semantic = report["context"]["semantic_state"]
    assert semantic["parse_count"] == 0 and semantic["queries_total"] == 0
    assert semantic["current_changes"][0]["tool_id"] == "s000002.t01"
    final = model.calls[-1]
    assert final.system_instructions == SYSTEM and len(final.tools) == 6
    checkpoint_message = next(
        item["content"]
        for item in final.input
        if "Current source-bound tool receipts" in item.get("content", "")
    )
    assert '"currency":"historical"' in checkpoint_message
    assert '"checks":[]' in checkpoint_message
    assert '"pending_checks":["reproduce","verify"]' in checkpoint_message
    assert '"tool_id":"s000002.t01"' in checkpoint_message
    metrics = report["context"]["optimization_state"]["metrics"]["state_aware_compaction"]
    assert metrics["triggers"] == 1
    events = [
        json.loads(line) for line in (harness.directory / "events.jsonl").read_text().splitlines()
    ]
    compact = next(event for event in events if event["type"] == "context_compacted")
    assert compact["payload"]["context_optimization"][0]["strategy"] == "state_aware_compaction"


@pytest.mark.sdk
@pytest.mark.parametrize("arm", ["dedup", "combined"])
def test_runtime_same_check_after_compaction_rediscloses_diagnostics(task, tmp_path, arm):
    from agents.testing import ModelStep, ScriptedModel, assistant_message, function_call
    from conftest import SimulatedSandbox

    from repropatch.harness import SYSTEM, Harness

    class NoisySandbox(SimulatedSandbox):
        def execute_test(self, name):
            code, status, text = super().execute_test(name)
            return code, status, LOG + text if code else text

    model = ScriptedModel(
        [
            [function_call("run_command", {"name": "reproduce"}, call_id="first")],
            ModelStep(
                output=[
                    assistant_message("visible history " * 12_000),
                    function_call("run_command", {"name": "reproduce"}, call_id="duplicate"),
                ],
                raw_usage={"input_tokens": 45_000, "output_tokens": 10_000, "total_tokens": 55_000},
            ),
            [assistant_message(json.dumps({key: [] for key in SUMMARY_KEYS}))],
            [function_call("run_command", {"name": "reproduce"}, call_id="fresh")],
            [assistant_message("Done")],
        ]
    )
    harness = Harness(
        replace(task, budget=replace(task.budget, max_steps=6)),
        model,
        tmp_path / "runs",
        sandbox_factory=NoisySandbox,
        context_policy=policy(**ARMS[arm]),
        candidate_only=True,
    )
    report = harness.run()
    assert report["agent_stop_reason"] == "MODEL_FINISHED", report
    model.assert_complete()
    assert len([e for e in report["evaluations"] if e["evaluation_role"] == "agent_check"]) == 3
    for index in (0, 1, 3, 4):
        assert model.calls[index].system_instructions == SYSTEM
        assert len(model.calls[index].tools) == 6
    final = model.calls[-1].input
    complete_rounds(final)
    outputs = [item for item in final if item.get("type") == "function_call_output"]
    assert [item["call_id"] for item in outputs] == ["fresh"]
    visible = json.loads(outputs[0]["output"])
    raw = json.loads((harness.directory / "agent/tool-results/s000004.t01.json").read_text())
    assert visible["progress"] == raw["progress"]
    if arm == "dedup":
        assert visible == raw
        assert visible["data"]["failed_commands"][0]["stdout"] == LOG + "expected -3, got 0"
    else:
        assert visible["context_projection"]["kind"] == "structured_diagnostics"
        assert (
            visible["data"]["failed_commands"][0]["stdout"]["diagnostics"][0]["message"]
            == "expected value"
        )
    state = report["context"]["optimization_state"]
    assert state["compaction_invalidations"] == 1
    assert state["metrics"]["deduplicate_results"]["triggers"] == 1
    assert next(iter(state["dedup_index"].values()))["tool_id"] == "s000004.t01"
    events = [
        json.loads(line) for line in (harness.directory / "events.jsonl").read_text().splitlines()
    ]
    compact = next(event for event in events if event["type"] == "context_compacted")
    assert compact["payload"]["dedup_invalidation"]["invalidated_entries"] == 1
