"""通过原生 ScriptedModel 验证 Shell 工具、预算和候选完整性。"""

import json
import runpy
import socket
import uuid
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import ROOT, SimulatedSandbox

from repropatch.harness import Harness

pytestmark = pytest.mark.sdk


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("离线 Shell 契约仅使用确定性模型")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


class ScriptedRepairSandbox(SimulatedSandbox):
    """仅解释测试定义的动作名，测试后端始终声明为非隔离。"""

    name = "scripted-repair"
    cleanup_confirmed = False
    active = False

    def __enter__(self):
        self.active = self.paused = True
        self.calls = []
        return self

    def assert_idle(self):
        assert self.active and self.paused

    def execute(self, command, *, cwd="/src"):
        self.assert_idle()
        self.calls.append((command, cwd))
        if command == "edit":
            path = self.source / "src/stats.cpp"
            path.write_bytes(
                path.read_bytes().replace(b"int best = 0;", b"int best = samples.front();")
            )
        elif command == "invalid":
            (self.source / "src/stats.cpp").write_bytes(b"\xff")
        elif command == "timeout":
            self.close()
            return self.result(("bash", command), 137, status="timed_out")
        return self.result(("bash", command), 127 if command == "missing" else 0)

    def close(self):
        self.active = self.paused = False
        self.cleanup_confirmed = True

    def __exit__(self, *_):
        self.close()


def shell_call(command, call_id=None, **arguments):
    from agents.testing import function_call

    return function_call(
        "bash", {"command": command, **arguments}, call_id=call_id or uuid.uuid4().hex
    )


def run_shell(task, tmp_path, steps, **options):
    from agents.testing import ScriptedModel

    model = ScriptedModel(steps)
    harness = Harness(
        task,
        model,
        tmp_path / "runs",
        tool_mode="shell-only",
        sandbox_factory=SimulatedSandbox,
        repair_sandbox_factory=ScriptedRepairSandbox,
        **options,
    )
    return harness, model, harness.run()


def test_single_shell_schema_supports_compound_last_turn_and_independent_oracle(task, tmp_path):
    task = replace(task, budget=replace(task.budget, max_steps=1))
    harness, model, report = run_shell(
        task, tmp_path, [[shell_call("edit", "edit"), shell_call("inspect", "inspect")]]
    )
    assert report["outcome"] == "ACCEPTED", report
    assert report["agent"]["agent_stop_reason"] == "STEP_BUDGET"
    assert report["tool_calls"] == 2
    assert report["benchmark"]["tool_mode"] == "shell-only"
    assert [tool.name for tool in model.calls[0].tools] == ["bash"]
    initial = json.loads(model.calls[0].input[0]["content"])
    assert initial["commands"] == task.commands.to_dict()
    assert initial["shell"]["persistent"] is True
    assert len(harness.repair_sandbox.calls) == 2 and not harness.repair_sandbox.active
    assert report["independent"] is not None and report["artifacts_complete"]
    outputs = [
        json.loads(p.read_text())
        for p in sorted((harness.directory / "agent/tool-results").glob("*.json"))
    ]
    assert outputs[0]["data"]["changed_files"] == ["src/stats.cpp"]
    assert outputs[0]["data"]["source_after_sha256"] == outputs[1]["data"]["source_before_sha256"]
    assert outputs[1]["data"]["changed_files"] == []
    assert outputs[1]["progress"]["model_steps_remaining"] == 0
    model.assert_complete()


def test_shell_nonzero_exit_and_invalid_arguments_allow_further_repair(task, tmp_path):
    from agents.testing import assistant_message

    harness, model, report = run_shell(
        task,
        tmp_path,
        [
            [shell_call("missing")],
            [shell_call(" ")],
            [shell_call("edit")],
            [assistant_message("完成")],
        ],
    )
    assert report["outcome"] == "ACCEPTED", report
    results = [
        json.loads(p.read_text())
        for p in sorted((harness.directory / "agent/tool-results").glob("*.json"))
    ]
    assert results[0]["data"]["exit_code"] == 127 and results[0]["ok"]
    assert results[1]["error"]["code"] == "INVALID_ARGUMENT"
    assert len(harness.repair_sandbox.calls) == 2
    model.assert_complete()


def test_shell_schema_rejects_legacy_tools_before_dispatch(task, tmp_path):
    from agents.testing import function_call

    harness, model, report = run_shell(
        task,
        tmp_path,
        [
            [
                function_call(
                    "edit_file", {"path": "src/stats.cpp", "old": "a", "new": "b"}, call_id="legacy"
                )
            ]
        ],
    )
    assert report["reason_code"] == "PROTOCOL_ERROR" and report["tool_calls"] == 0
    assert harness.repair_sandbox.calls == [] and harness.repair_sandbox.cleanup_confirmed
    model.assert_complete()


def test_shell_poisoned_snapshot_is_rejected_before_candidate_export(task, tmp_path, monkeypatch):
    from agents.testing import assistant_message

    harness, model, report = run_shell(
        task,
        tmp_path,
        [
            [shell_call("edit")],
            [shell_call("invalid")],
            [assistant_message("剩余请求")],
        ],
    )
    assert report["outcome"] == "REJECTED" and report["reason_code"] == "FORBIDDEN_PATCH", report
    assert report["candidate"] is None and report["independent"] is None
    assert len(model.calls) == 2 and harness.repair_sandbox.cleanup_confirmed
    assert b"samples.front()" in (harness.directory / "diagnostics/unverified.patch").read_bytes()
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    adapter = runpy.run_path(str(ROOT / "scripts/run_benchmark_agent.py"))
    exported = adapter["export_repropatch_candidate"](report, harness.directory, tmp_path)
    assert exported["candidate_bytes"] == 0 and not (tmp_path / "candidate.patch").exists()
    assert exported["candidate_rejected"] == "FORBIDDEN_PATCH"


def test_shell_timeout_closes_session_and_saves_legal_candidate(task, tmp_path):
    harness, model, report = run_shell(
        task, tmp_path, [[shell_call("edit")], [shell_call("timeout")]]
    )
    assert report["outcome"] == "ACCEPTED", report
    assert report["agent"]["agent_stop_reason"] == "SHELL_TIMED_OUT"
    assert report["model_steps"] == 2 and harness.repair_sandbox.cleanup_confirmed
    model.assert_complete()


def test_shell_candidate_only_retains_external_acceptance_contract(task, tmp_path):
    task = replace(task, budget=replace(task.budget, max_steps=1))
    _, model, report = run_shell(task, tmp_path, [[shell_call("edit")]], candidate_only=True)
    assert report["reason_code"] == "EXTERNAL_ORACLE_REQUIRED", report
    assert report["candidate_roundtrip_verified"] and report["independent"] is None
    oracle = Harness(
        task,
        output_root=tmp_path / "oracle",
        sandbox_factory=SimulatedSandbox,
        patch_file=Path(report["artifact_directory"]) / "patch.diff",
    ).run()
    assert oracle["outcome"] == "ACCEPTED"
    model.assert_complete()
