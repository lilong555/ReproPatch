"""开放次数预算下的真实 SDK 循环和事件账本契约。"""

import json
import socket
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import SimulatedSandbox

from repropatch.harness import Harness

pytestmark = pytest.mark.sdk


def test_open_budget_crosses_old_request_and_tool_caps_and_finishes(task, tmp_path, monkeypatch):
    from agents.testing import ScriptedModel, assistant_message, function_call

    def denied(*args, **kwargs):
        raise AssertionError("该测试仅使用固定模型响应")

    monkeypatch.setattr(socket.socket, "connect", denied)
    steps = [
        [
            function_call("read_file", {"path": "src/stats.cpp"}, call_id=f"read-{turn}-{item}")
            for item in range(2)
        ]
        for turn in range(25)
    ]
    steps.extend(
        [
            [
                function_call(
                    "edit_file",
                    {
                        "path": "src/stats.cpp",
                        "old": "int best = 0;",
                        "new": "int best = samples.front();",
                    },
                    call_id="fix",
                )
            ],
            [assistant_message("修复完成。")],
        ]
    )
    model = ScriptedModel(steps)
    harness = Harness(
        replace(task, budget=replace(task.budget, max_steps=None, max_tool_calls=None)),
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
    )
    report = harness.run()
    model.assert_complete()
    assert report["outcome"] == "ACCEPTED"
    assert report["agent"]["steps_used"] == 27
    assert report["agent"]["tool_calls_used"] == 51
    assert report["agent"]["agent_stop_reason"] == "MODEL_FINISHED"
    directory = Path(report["artifact_directory"])
    config = json.loads((directory / "execution-config.json").read_text())
    assert config["budget"]["max_steps"] is None
    assert config["budget"]["max_tool_calls"] is None
