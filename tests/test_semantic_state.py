"""结构检索、授权边界、可见证据恢复和无限请求的离线验证。"""

import json
from copy import deepcopy
from dataclasses import replace

import pytest

from repropatch.artifacts import EvidenceRef
from repropatch.context import SUMMARY_KEYS, ContextLimit, ContextPolicy, ContextState, encoded
from repropatch.errors import InfrastructureError, PolicyError
from repropatch.semantic_state import SemanticState
from repropatch.tools import Toolbox
from repropatch.workspace import Worktree


def policy(**kwargs):
    return ContextPolicy(
        **{
            "context_window_tokens": 40_000,
            "compact_trigger_tokens": 12_000,
            "compact_target_tokens": 5400,
            "tool_growth_tokens": 4000,
            "estimation_margin_tokens": 1000,
            "request_cap": None,
            **kwargs,
        }
    )


def checkpoint_summary():
    return json.dumps({name: "保留当前可见事实与下一步。" for name in SUMMARY_KEYS})


def test_cpp_structure_finds_definition_calls_and_include_with_authorized_scope(
    repository, tmp_path
):
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        toolbox = Toolbox(
            work,
            ("src/stats.cpp",),
            None,
            readable={"src/stats.cpp", "src/stats.hpp"},
        )
        state = SemanticState(toolbox)
        definitions = state.query("definitions", "maximum_sample")
        assert any(
            item["kind"] == "function_definition"
            and item["path"] == "src/stats.cpp"
            and item["line"] == 3
            for item in definitions["matches"]
        )
        assert definitions["relation_semantics"] == "syntactic"
        assert state.query("references", "samples.empty")["matches"][0]["kind"] == "call"
        include = state.query("includes", "stats.hpp")["matches"][0]
        assert include["target_path"] == "src/stats.hpp"
        assert state.query("definitions", "", "tests")["matches"] == []
        with pytest.raises(PolicyError, match="PATH_NOT_READABLE"):
            state.query("definitions", "", "../")
        assert all(path.startswith("src/") for path in state.state["files"])


def test_edit_invalidates_index_and_checkpoint_keeps_evidence(repository, tmp_path):
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        toolbox = Toolbox(work, ("src/stats.cpp",), None, readable={"src/stats.cpp"})
        state = SemanticState(toolbox)
        state.query("definitions", "maximum_sample")
        old = state.cache["src/stats.cpp"]["sha256"]
        result = toolbox.edit_file("src/stats.cpp", "maximum_sample", "best_sample")
        reference = {"path": "agent/tool-results/edit.json", "sha256": "f" * 64, "size_bytes": 10}
        state.observe(
            "edit_file",
            {"path": "src/stats.cpp"},
            {"ok": True, "data": result},
            reference,
            tool_id="edit",
        )
        assert "src/stats.cpp" not in state.cache
        assert "src/stats.cpp" not in state.state["files"]
        state = SemanticState(toolbox, json.loads(encoded(state.to_dict())))
        assert state.query("definitions", "maximum_sample")["matches"] == []
        assert state.query("definitions", "best_sample")["matches"]
        assert state.cache["src/stats.cpp"]["sha256"] != old
        changes = state.query("state", "src/stats.cpp")["groups"]["changes"]
        assert changes[0]["after_sha256"] == result["after_sha256"]
        assert changes[0]["evidence"] == reference


def test_evidence_reader_only_accepts_registered_visible_outputs_and_checks_sha(
    repository, tmp_path
):
    root = tmp_path / "evidence"
    ref = EvidenceRef.save(root, "agent/tool-results/a.json", b'{"diagnostic":"visible"}')
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        toolbox = Toolbox(work, (), None)
        state = SemanticState(
            toolbox,
            read_evidence=lambda item: EvidenceRef(**item).read(root, limit=item["size_bytes"]),
        )
        state.register_evidence(
            "a", {"path": ref.path, "sha256": ref.sha256, "size_bytes": ref.size_bytes}
        )
        assert state.query("evidence", "a")["text"] == '{"diagnostic":"visible"}'
        assert state.query("evidence", ref.path)["text"] == '{"diagnostic":"visible"}'
        with pytest.raises(PolicyError, match="EVIDENCE_NOT_VISIBLE"):
            state.query("evidence", "reference.patch")
        (root / ref.path).write_bytes(b'{"diagnostic":"changed"}')
        with pytest.raises(InfrastructureError, match="ARTIFACT_CORRUPT"):
            state.query("evidence", "a")


def test_cumulative_metrics_survive_observation_window_and_checkpoint(repository, tmp_path):
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        toolbox = Toolbox(work, ("src/stats.cpp",), None, readable={"src/stats.cpp"})
        state = SemanticState(toolbox)
        state.query("definitions", "maximum_sample")
        state.query("references", "samples")
        raw_bytes = len((work.path / "src/stats.cpp").read_bytes())
        for index in range(130):
            state.query("state")
            state.observe(
                "query_code",
                {"kind": "state"},
                {"ok": True, "data": {}},
                {"path": f"agent/tool-results/{index}.json", "sha256": "f" * 64, "size_bytes": 1},
                tool_id=str(index),
            )
        assert len(state.state["observations"]) == 128
        context = ContextState(policy(), semantic_state=state.to_dict())
        restored = ContextState.restore(policy(), json.loads(encoded(context.to_dict())))
        state = SemanticState(toolbox, restored.semantic_state)
        assert state.state["queries_total"] == 132
        assert state.state["query_kinds"] == {"definitions": 1, "references": 1, "state": 130}
        assert state.state["parse_count"] == 1 and state.state["cache_hits"] == 1
        state.query("includes")
        assert state.state["queries_total"] == 133
        assert state.state["parse_count"] == 2
        assert state.state["indexed_bytes_total"] == raw_bytes * 2
        assert state.state["files"]["src/stats.cpp"]["source_bytes"] == raw_bytes
        assert state.state["index_seconds_total"] >= state.state["parse_seconds_total"] > 0
        with pytest.raises(PolicyError, match="INVALID_ARGUMENT"):
            state.query("unknown")
        assert state.state["queries_total"] == sum(state.state["query_kinds"].values()) == 134


def test_failed_summary_replacement_preserves_usage_anchor():
    state = ContextState(policy())
    fixed = [{"role": "user", "content": "仅修改 src/stats.cpp"}]
    state.plan({"input": fixed})
    body = {
        "input": fixed
        + [
            {"type": "function_call", "call_id": "a", "name": "read_file", "arguments": "{}"},
            {"type": "function_call_output", "call_id": "a", "output": "旧日志" * 20_000},
        ]
    }
    plan = state.plan(body)
    state.estimator.observe(
        {"input": fixed},
        {"output": [], "usage": {"input_tokens": 321, "output_tokens": 4}},
    )
    before = deepcopy(state.to_dict())
    oversized = json.dumps({key: "摘要过大 " * 10_000 for key in SUMMARY_KEYS})
    with pytest.raises(ContextLimit, match="COMPACTION_FAILED"):
        state.replace(body, plan, oversized, sequence=2, duration_seconds=0.1)
    assert state.to_dict() == before


@pytest.mark.parametrize("invalid", [0, -1, True, 1.5, "24"])
def test_request_cap_is_optional_and_type_checked(invalid):
    assert policy().request_cap is None
    with pytest.raises(ValueError, match="CONTEXT_POLICY_REQUEST_CAP"):
        policy(request_cap=invalid)


@pytest.mark.sdk
def test_full_large_baseline_compacts_then_queries_edits_and_recovers_state(
    task, tmp_path, monkeypatch
):
    from agents.testing import ModelStep, ScriptedModel, assistant_message, function_call
    from conftest import SimulatedSandbox

    from repropatch.harness import Harness
    from repropatch.tools import model_evaluation

    original_view = model_evaluation

    def large_view(record):
        return {**original_view(record), "diagnostic": "可见重复基线诊断 " * 3500}

    monkeypatch.setattr("repropatch.tools.model_evaluation", large_view)
    model = ScriptedModel(
        [
            [assistant_message(checkpoint_summary())],
            [
                function_call(
                    "query_code", {"kind": "definitions", "query": "maximum_sample"}, call_id="q"
                )
            ],
            ModelStep(
                output=[
                    assistant_message("定位过程中已读取的旧日志 " * 3000),
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
                raw_usage={"input_tokens": 10_000, "output_tokens": 5000, "total_tokens": 15_000},
            ),
            [assistant_message(checkpoint_summary())],
            [
                function_call(
                    "query_code", {"kind": "state", "query": "src/stats.cpp"}, call_id="state"
                )
            ],
            [assistant_message("完成")],
        ]
    )
    task = replace(task, budget=replace(task.budget, max_steps=None, max_tool_calls=None))
    harness = Harness(
        task,
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        context_policy=policy(),
        semantic_state_enabled=True,
        candidate_only=True,
    )
    report = harness.run()
    assert report["reason_code"] == "EXTERNAL_ORACLE_REQUIRED", report
    assert report["agent_stop_reason"] == "MODEL_FINISHED", report
    assert len(report["context"]["compactions"]) == 2
    assert report["model_steps"] == 6 and report["tool_calls"] == 3
    state = report["context"]["semantic_state"]
    assert state["changes"]["src/stats.cpp"]["after_sha256"]
    assert state["evidence"]["baseline"]
    assert "src/stats.cpp" not in state["files"]
    assert "可见重复基线诊断" not in encoded(model.calls[1].input).decode()
    assert "Persistent C++ repair evidence" in encoded(model.calls[4].input).decode()
    final_context = encoded(model.calls[-1].input).decode()
    assert "before_sha256" in final_context and "after_sha256" in final_context
    assert (harness.directory / "patch.diff").read_bytes()
    model.assert_complete()


@pytest.mark.sdk
def test_full_unlimited_requests_continues_past_legacy_cap(task, tmp_path):
    from agents.testing import ScriptedModel, assistant_message, function_call
    from conftest import SimulatedSandbox

    from repropatch.harness import Harness

    model = ScriptedModel(
        [
            [function_call("read_file", {"path": "src/stats.cpp"}, call_id=f"r{index}")]
            for index in range(25)
        ]
        + [[assistant_message("已完成检查")]]
    )
    harness = Harness(
        replace(task, budget=replace(task.budget, max_steps=None, max_tool_calls=None)),
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        candidate_only=True,
    )
    report = harness.run()
    assert report["agent_stop_reason"] == "MODEL_FINISHED", report
    assert report["model_steps"] == 26
    assert report["tool_calls"] == 25
    model.assert_complete()


@pytest.mark.sdk
def test_semantic_checkpoint_resume_keeps_tool_schema_state_and_open_budget(task, tmp_path):
    from agents.testing import assistant_message, function_call
    from conftest import SimulatedSandbox

    from repropatch.harness import Harness
    from repropatch.models import load_sdk_script
    from repropatch.recovery import read_checkpoint, resume_run

    outputs = [
        [
            assistant_message("已经读取的可见诊断 " * 5000),
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
        [assistant_message(checkpoint_summary())],
        [
            function_call(
                "query_code",
                {"kind": "state", "query": "src/stats.cpp"},
                call_id="state",
            )
        ],
        [assistant_message("完成")],
    ]
    script = {
        "version": 1,
        "steps": [
            {
                "output": [item.model_dump(mode="json", exclude_none=True) for item in items],
                "usage": {
                    "input_tokens": 10_000 if index == 0 else 1000,
                    "output_tokens": 5000 if index == 0 else 100,
                    "total_tokens": 15_000 if index == 0 else 1100,
                },
            }
            for index, items in enumerate(outputs)
        ],
    }
    path = tmp_path / "script.json"
    path.write_bytes(encoded(script))
    harness = Harness(
        replace(task, budget=replace(task.budget, max_steps=None, max_tool_calls=None)),
        load_sdk_script(path),
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        context_policy=policy(),
        semantic_state_enabled=True,
        pause_after_step=2,
        script_source=path.read_bytes(),
    )
    paused = harness.run()
    assert paused["paused"], paused
    manifest, _ = read_checkpoint(harness.directory)
    state = json.loads(
        EvidenceRef(**manifest["context_state"]).read(harness.directory, limit=100_000)
    )
    assert state["compacted_up_to_seq"] == 2
    assert state["semantic_state"]["changes"]["src/stats.cpp"]["after_sha256"]
    result = resume_run(harness.directory, sandbox_factory=SimulatedSandbox)
    assert result["outcome"] == "ACCEPTED", result
    assert result["model_steps"] == 4 and result["tool_calls"] == 2
    assert result["context"]["semantic_state"]["observations"][-1]["tool"] == "query_code"
