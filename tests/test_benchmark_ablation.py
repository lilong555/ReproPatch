"""通过原生 SDK 验证自检消融、工具准入和最终独立验收。"""

import json
import runpy
import socket
from pathlib import Path

import pytest
from conftest import ROOT, SimulatedSandbox

import repropatch.tools as tools_module
from repropatch.harness import SYSTEM, Harness

pytestmark = pytest.mark.sdk


@pytest.fixture
def adapter(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("离线消融验证禁止真实网络")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    return runpy.run_path(str(ROOT / "scripts/run_benchmark_agent.py"))


@pytest.mark.parametrize("enabled", [True, False])
def test_both_profiles_preserve_baseline_and_final_acceptance(adapter, task, tmp_path, enabled):
    from agents.testing import ScriptedModel, assistant_message, function_call

    steps = [
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
        ]
    ]
    if enabled:
        steps.append([function_call("run_command", {"name": "reproduce"}, call_id="f2p")])
    steps.append([assistant_message("修复完成，交由独立验收。")])
    model = ScriptedModel(steps)
    harness = Harness(task, model, tmp_path / "runs", sandbox_factory=SimulatedSandbox)
    original_tools = tools_module.sdk_tools
    with adapter["intermediate_checks"](harness, enabled=enabled):
        registered = {tool.name for tool in tools_module.sdk_tools(None, None, None)}
        assert registered == (
            {"list_directory", "read_file", "search_code", "edit_file", "run_command", "run_shell"}
            if enabled
            else {"list_directory", "read_file", "search_code", "edit_file"}
        )
        if not enabled:
            assert 'run_command("' not in harness.instructions
            assert "run_shell" not in harness.instructions
        report = harness.run()
    assert report["outcome"] == "ACCEPTED"
    roles = [value["evaluation_role"] for value in report["evaluations"]]
    assert roles == (
        ["baseline", "agent_check", "independent"] if enabled else ["baseline", "independent"]
    )
    assert report["tool_calls"] == (2 if enabled else 1)
    assert report["cleanup_confirmed"]
    assert tools_module.sdk_tools is original_tools and harness.instructions == SYSTEM
    model.assert_complete()


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        ("run_command", {"name": "verify"}),
        ("run_shell", {"command": "ctest --test-dir /build", "cwd": "/build"}),
    ],
)
def test_disabled_execution_is_rejected_before_tool_admission(
    adapter, task, tmp_path, name, arguments
):
    from agents.testing import ScriptedModel, function_call

    model = ScriptedModel([[function_call(name, arguments, call_id="forbidden")]])
    harness = Harness(task, model, tmp_path / "runs", sandbox_factory=SimulatedSandbox)
    with adapter["intermediate_checks"](harness, enabled=False):
        report = harness.run()
    assert report["outcome"] == "ERROR" and report["reason_code"] == "PROTOCOL_ERROR"
    assert report["tool_calls"] == 0
    events = [
        json.loads(line)
        for line in (Path(report["artifact_directory"]) / "events.jsonl").read_text().splitlines()
    ]
    assert not any(event["type"] == "tool_started" for event in events)
    assert all(value["evaluation_role"] == "baseline" for value in report["evaluations"])
    model.assert_complete()


def test_ablation_restores_registration_after_failure(adapter, task, model, tmp_path):
    harness = Harness(task, model, tmp_path / "runs", sandbox_factory=SimulatedSandbox)
    original_tools = tools_module.sdk_tools
    with pytest.raises(RuntimeError, match="中断"):
        with adapter["intermediate_checks"](harness, enabled=False):
            raise RuntimeError("中断")
    assert tools_module.sdk_tools is original_tools
    assert harness.instructions == SYSTEM
