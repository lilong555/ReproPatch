"""Source-bound duplicate read projections keep execution and evidence intact."""

import json
from copy import deepcopy
from dataclasses import replace

import pytest

from repropatch.context import SUMMARY_KEYS, ContextPolicy, ContextState, fold_tool_output
from repropatch.context_optimization import ContextOptimizer
from repropatch.task import canonical_json
from repropatch.workspace import git

SOURCE = "a" * 64
TEXT = "int repeated_symbol(int value) { return value + 1; }\n" * 100


def receipt(tool):
    if tool == "read_file":
        arguments = {"path": "src/stats.cpp", "start_line": 1, "max_lines": 100}
        data = {
            "path": arguments["path"],
            "text": TEXT,
            "start_line": 1,
            "end_line": 100,
            "total_lines": 150,
            "truncated": True,
            "editable": True,
        }
    elif tool == "search_code":
        arguments = {"query": "repeated_symbol", "path": "src"}
        data = {
            "matches": [
                {"path": "src/stats.cpp", "line": i + 1, "text": line}
                for i, line in enumerate(TEXT.splitlines())
            ],
            "truncated": True,
        }
    else:
        arguments = {"path": "src"}
        data = {
            "entries": [{"name": f"source_{i}.cpp", "type": "file"} for i in range(100)],
            "truncated": False,
        }
    return arguments, {"ok": True, "data": data, "progress": {"model_steps_remaining": 10}}


def project(optimizer, tool, arguments, value, identity, source=SOURCE):
    reference = {
        "path": f"agent/tool-results/{identity}.json",
        "sha256": "f" * 64,
        "size_bytes": len(canonical_json(value)) + 1,
    }
    native = fold_tool_output(
        canonical_json(value).decode(),
        optimizer.policy.tool_output_max_bytes,
        lambda raw: reference["path"],
    )
    output, events = optimizer.project(
        tool,
        arguments,
        value,
        reference,
        tool_id=identity,
        source=source,
        native=native,
    )
    return output, events, native


@pytest.mark.parametrize("tool", ["read_file", "search_code", "list_directory"])
def test_exact_read_duplicate_preserves_slice_metadata_and_latest_budget(tool):
    context = ContextState(ContextPolicy(deduplicate_results=True))
    optimizer = ContextOptimizer(context)
    arguments, value = receipt(tool)
    original = deepcopy(value)
    first, events, native = project(optimizer, tool, arguments, value, "first")
    assert first == native and events == []
    assert optimizer.last_decisions[0]["reason"] == "first_observation"
    value["progress"]["model_steps_remaining"] = 3
    output, events, native = project(optimizer, tool, arguments, value, "second")
    projected = json.loads(output)
    field = {"read_file": "text", "search_code": "matches", "list_directory": "entries"}[tool]
    assert field not in projected["data"] and field in value["data"]
    assert projected["data"]["truncated"] == original["data"]["truncated"]
    assert projected["data"]["returned_items"] == 100
    assert projected["progress"] == value["progress"]
    assert projected["context_projection"]["duplicate_of"]["tool_id"] == "first"
    assert projected["context_projection"]["tool_executed"] is True
    assert projected["context_projection"]["source_tree_sha256"] == SOURCE
    assert len(output.encode()) < len(native.encode())
    assert events[0]["strategy"] == "deduplicate_results"
    assert value["data"] == original["data"]
    metrics = context.optimization_state["metrics"]["deduplicate_results"]
    assert (metrics["attempts"], metrics["candidates"], metrics["triggers"]) == (2, 1, 1)


@pytest.mark.parametrize("change", ["source", "arguments", "content", "status"])
def test_changed_read_identity_is_fully_redisclosed(change):
    optimizer = ContextOptimizer(ContextState(ContextPolicy(deduplicate_results=True)))
    arguments, value = receipt("read_file")
    project(optimizer, "read_file", arguments, value, "first")
    source = SOURCE
    if change == "source":
        source = "b" * 64
    elif change == "arguments":
        arguments["max_lines"] = 101
    elif change == "content":
        value["data"]["text"] += "// newly visible line\n"
    else:
        value["ok"] = False
    output, events, native = project(optimizer, "read_file", arguments, value, "changed", source)
    assert output == native and events == []


def test_source_rollback_clears_read_identity():
    optimizer = ContextOptimizer(ContextState(ContextPolicy(deduplicate_results=True)))
    arguments, value = receipt("read_file")
    project(optimizer, "read_file", arguments, value, "first")
    project(optimizer, "read_file", arguments, value, "edited", "b" * 64)
    output, events, native = project(optimizer, "read_file", arguments, value, "rolled-back")
    assert output == native and not events
    assert optimizer.state["source_invalidations"] == 2


def test_folded_read_is_never_recorded_as_fully_disclosed():
    optimizer = ContextOptimizer(
        ContextState(ContextPolicy(deduplicate_results=True, tool_output_max_bytes=1024))
    )
    arguments, value = receipt("read_file")
    for identity in ("first", "second"):
        output, events, native = project(optimizer, "read_file", arguments, value, identity)
        assert output == native and not events
        assert optimizer.last_decisions[0]["reason"] == "first_result_not_fully_visible"
    assert optimizer.state["dedup_index"] == {}


def test_checkpoint_restore_reuses_reads_but_context_compaction_rediscloses():
    policy = ContextPolicy(
        deduplicate_results=True,
        compact_trigger_tokens=48_000,
        compact_target_tokens=21_600,
    )
    context = ContextState(policy)
    optimizer = ContextOptimizer(context)
    arguments, value = receipt("read_file")
    first, _, _ = project(optimizer, "read_file", arguments, value, "first")
    context = ContextState.restore(policy, json.loads(canonical_json(context.to_dict())))
    optimizer = ContextOptimizer(context)
    assert project(optimizer, "read_file", arguments, value, "restored")[1]
    body = {
        "input": [
            {"role": "user", "content": "Repair src/stats.cpp"},
            {"type": "function_call", "call_id": "first", "name": "read_file", "arguments": "{}"},
            {"type": "function_call_output", "call_id": "first", "output": first},
            {"role": "assistant", "content": "visible history " * 12_000},
        ]
    }
    plan = context.plan(body)
    assert plan is not None
    context.replace(
        body, plan, json.dumps(dict.fromkeys(SUMMARY_KEYS, [])), sequence=4, duration_seconds=0
    )
    output, events, native = project(optimizer, "read_file", arguments, value, "after-compaction")
    assert output == native and not events


def test_skip_reasons_cover_unprofitable_candidate_and_unsupported_tool():
    context = ContextState(ContextPolicy(deduplicate_results=True))
    optimizer = ContextOptimizer(context)
    arguments, value = receipt("read_file")
    value["data"]["text"] = "short"
    for identity in ("first", "second"):
        project(optimizer, "read_file", arguments, value, identity)
    project(optimizer, "run_shell", {}, value, "shell")
    metrics = context.optimization_state["metrics"]["deduplicate_results"]
    assert metrics["skip_reasons"] == {
        "first_observation": 1,
        "insufficient_savings": 1,
        "tool_not_supported": 1,
    }
    assert metrics["attempts"] == 3 and metrics["candidates"] == 1 and metrics["triggers"] == 0


@pytest.mark.sdk
def test_native_runtime_executes_both_reads_and_retains_both_raw_receipts(task, tmp_path):
    from agents.testing import ScriptedModel, assistant_message, function_call
    from conftest import SimulatedSandbox

    from repropatch.harness import Harness

    source = task.repository / "src/stats.cpp"
    source.write_text(source.read_text() + "\n// visible context for the read tool\n" * 100)
    git(task.repository, "add", "src/stats.cpp")
    git(
        task.repository,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@localhost",
        "commit",
        "-m",
        "read fixture",
    )
    configured = replace(task, revision=git(task.repository, "rev-parse", "HEAD").strip())
    model = ScriptedModel(
        [
            [function_call("read_file", {"path": "src/stats.cpp"}, call_id="one")],
            [function_call("read_file", {"path": "src/stats.cpp"}, call_id="two")],
            [assistant_message("Done")],
        ]
    )
    harness = Harness(
        configured,
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        context_policy=ContextPolicy(deduplicate_results=True),
        candidate_only=True,
    )
    report = harness.run()
    assert report["agent_stop_reason"] == "MODEL_FINISHED", report
    model.assert_complete()
    outputs = [v for v in model.calls[-1].input if v.get("type") == "function_call_output"]
    assert [v["call_id"] for v in outputs] == ["one", "two"]
    assert "text" in json.loads(outputs[0]["output"])["data"]
    assert json.loads(outputs[1]["output"])["context_projection"]["tool_executed"] is True
    for step in (1, 2):
        raw = json.loads(
            (harness.directory / f"agent/tool-results/s{step:06d}.t01.json").read_text()
        )
        assert "visible context for the read tool" in raw["data"]["text"]
    events = [
        json.loads(line) for line in (harness.directory / "events.jsonl").read_text().splitlines()
    ]
    finished = [event for event in events if event["type"] == "tool_finished"]
    assert len(finished) == 2
    assert (
        finished[0]["payload"]["context_optimization_decisions"][0]["reason"] == "first_observation"
    )
    assert finished[1]["payload"]["context_optimization_decisions"][0]["outcome"] == "projected"
