import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import SimulatedSandbox, TrustedLocalSandbox, scripted

from repropatch.harness import Harness
from repropatch.workspace import git

pytestmark = pytest.mark.sdk


def test_complete_flow_unit(task, model, tmp_path):
    report = Harness(task, model, tmp_path / "runs", sandbox_factory=SimulatedSandbox).run()
    assert report["status"] == "passed" and report["reproduced"] and report["verified"]
    assert report["isolated"] is False
    directory = Path(report["artifact_directory"])
    assert "samples.front()" in (directory / "patch.diff").read_text()
    events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
    with sqlite3.connect(directory / "events.sqlite3") as db:
        rows = db.execute("SELECT envelope_json FROM events ORDER BY seq").fetchall()
    assert len(events) == len(rows)
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    assert [json.loads(row[0]) for row in rows] == events
    assert events[-1]["type"] == "state_changed"
    assert events[-1]["payload"]["to"] == "FINISHED"
    tools = {event["tool_call_id"]: event for event in events if event["type"] == "tool_started"}
    assert tools and None not in tools
    for event in events:
        if (
            event["type"] == "command_started"
            and event["payload"].get("evaluation_role") == "agent_check"
        ):
            assert event["tool_call_id"] in tools
            assert event["step_id"] == tools[event["tool_call_id"]]["step_id"]
    assert not (directory / "worktrees/repair").exists()
    assert not (directory / "worktrees/validation").exists()
    assert git(task.repository, "status", "--porcelain") == ""
    baseline, _, independent = report["evaluations"]
    assert baseline["source_sha256"] != independent["source_sha256"]
    assert baseline["tests"][0]["ctest_exit_code"] == 8
    assert all(c["returncode"] == 0 for c in independent["commands"])
    feedback = [
        json.loads((directory / event["payload"]["result_ref"]["path"]).read_text())["data"]
        for event in events
        if event["type"] == "tool_finished" and event["payload"]["name"] == "run_command"
    ]
    assert feedback and feedback[0]["passed"]
    assert feedback[0]["failed_commands"] == [] and "commands" not in feedback[0]
    reference = feedback[0]["evidence"]
    raw = json.loads((directory / reference["path"]).read_text())
    assert raw["commands"] and len(raw["tests"]) == len(feedback[0]["tests"])


@pytest.mark.parametrize(
    "actions,status",
    [
        ([{"finish": "done"}], "no_patch"),
        ([{"tool": "read_file", "arguments": {"path": "src/stats.cpp"}}] * 12, "budget_exhausted"),
        (
            [
                {
                    "tool": "edit_file",
                    "arguments": {
                        "path": "src/stats.cpp",
                        "old": "int best = 0;",
                        "new": "int best = -1;",
                    },
                },
                {"finish": "done"},
            ],
            "failed",
        ),
    ],
)
def test_incomplete_repairs_cannot_pass(task, tmp_path, actions, status):
    # Use a stricter fake for the wrong-but-nonzero patch.
    class Strict(SimulatedSandbox):
        def execute_test(self, name):
            source = (self.source / "src/stats.cpp").read_text()
            if name == "negative_values" and "samples.front()" not in source:
                return 8, "failed", "expected -3, got 0"
            return 0, "passed", "pass"

    report = Harness(task, scripted(actions), tmp_path / "runs", sandbox_factory=Strict).run()
    assert report["status"] == status and not report["verified"]


@pytest.mark.parametrize(
    "mode,status",
    [
        ("pass", "not_reproduced"),
        ("timeout", "inconclusive"),
        ("wrong-marker", "not_reproduced"),
        ("build", "error"),
    ],
)
def test_baseline_failure_is_checked(task, tmp_path, mode, status):
    class BadBaseline(SimulatedSandbox):
        def execute_test(self, name):
            if name != "negative_values":
                return 0, "passed", "pass"
            if mode == "pass":
                return 0, "passed", "pass"
            return (
                8,
                "timed_out" if mode == "timeout" else "failed",
                "unrelated" if mode == "wrong-marker" else "expected -3, got 0",
            )

        def run(self, argv):
            if mode == "build" and argv[0] == "cmake":
                return self.result(argv, 1, "build failed")
            return super().run(argv)

    report = Harness(task, scripted([]), tmp_path / "runs", sandbox_factory=BadBaseline).run()
    assert report["status"] == status and report["model_steps"] == 0


def test_denied_tool_is_visible_to_model(task, tmp_path, model):
    script = [{"tool": "read_file", "arguments": {"path": "/etc/passwd"}}, {"finish": "stop"}]
    report = Harness(
        task, scripted(script), tmp_path / "runs", sandbox_factory=SimulatedSandbox
    ).run()
    events = (Path(report["artifact_directory"]) / "events.jsonl").read_text()
    assert '"ok": false' in events and report["status"] == "no_patch"


def test_independent_verification_catches_regression(task, model, tmp_path):
    class Regression(SimulatedSandbox):
        def execute_test(self, name):
            if "independent" in self.source.name and name == "empty_values":
                return 8, "failed", "empty_values failed"
            return super().execute_test(name)

    report = Harness(task, model, tmp_path / "runs", sandbox_factory=Regression).run()
    assert report["status"] == "failed" and not report["verified"]


def test_error_still_writes_report_and_cleans_worktree(task, tmp_path):
    from agents.testing import ModelStep, ScriptedModel

    from repropatch.errors import ReproPatchError

    selected = ScriptedModel([ModelStep(error=ReproPatchError("model offline"))])
    report = Harness(task, selected, tmp_path / "runs", sandbox_factory=SimulatedSandbox).run()
    assert report["status"] == "error" and report["error"] == "model offline"
    assert not (Path(report["artifact_directory"]) / "worktrees/repair").exists()


@pytest.mark.integration
def test_real_cpp_reproduce_repair_verify(task, model, tmp_path):
    report = Harness(task, model, tmp_path / "runs", sandbox_factory=TrustedLocalSandbox).run()
    assert report["status"] == "passed", report
    assert report["isolated"] is False
    baseline = report["evaluations"][0]
    assert baseline["tests"][0]["marker_seen"] is True
    final = report["evaluations"][-1]
    assert {item["name"] for item in final["tests"]} == {
        "negative_values",
        "positive_values",
        "empty_values",
        "mixed_values",
    }
    assert all(item["observed_status"] == "passed" for item in final["tests"])


@pytest.mark.integration
def test_real_cpp_wrong_patch_rejected(task, tmp_path):
    actions = [
        {
            "tool": "edit_file",
            "arguments": {"path": "src/stats.cpp", "old": "int best = 0;", "new": "int best = -1;"},
        },
        {"finish": "done"},
    ]
    report = Harness(
        replace(task, budget=replace(task.budget, max_steps=3)),
        scripted(actions),
        tmp_path / "runs",
        sandbox_factory=TrustedLocalSandbox,
    ).run()
    assert report["status"] == "failed" and report["reproduced"] and not report["verified"]


def test_budget_exhaustion_retains_tentative_patch(task, tmp_path):
    actions = [
        {
            "tool": "edit_file",
            "arguments": {
                "path": "src/stats.cpp",
                "old": "int best = 0;",
                "new": "int best = samples.front();",
            },
        }
    ]
    report = Harness(
        replace(task, budget=replace(task.budget, max_steps=1)),
        scripted(actions),
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
    ).run()
    assert report["outcome"] == "ACCEPTED" and report["agent"]["agent_stop_reason"] == "STEP_BUDGET"
    assert "samples.front()" in (Path(report["artifact_directory"]) / "patch.diff").read_text()


def test_model_exception_does_not_lose_candidate_patch(task, tmp_path):
    from agents.testing import ModelStep, ScriptedModel, function_call

    selected = ScriptedModel(
        [
            ModelStep(
                output=[
                    function_call(
                        "edit_file",
                        {"path": "src/stats.cpp", "old": "int best = 0;", "new": "int best = -1;"},
                        call_id="candidate",
                    )
                ]
            ),
            ModelStep(error=RuntimeError("sensitive plugin detail")),
        ]
    )
    report = Harness(task, selected, tmp_path / "runs", sandbox_factory=SimulatedSandbox).run()
    assert report["status"] == "error"
    assert "sensitive" not in report["error"]
    assert "int best = -1;" in (Path(report["artifact_directory"]) / "patch.diff").read_text()


def test_changing_execution_image_is_rejected(task, model, tmp_path):
    class DriftingImage(SimulatedSandbox):
        @property
        def image_id(self):
            return "sha256:" + ("a" if "baseline" in self.source.name else "b") * 64

    report = Harness(task, model, tmp_path / "runs", sandbox_factory=DriftingImage).run()
    assert report["status"] == "error" and "image changed" in report["error"]


def test_invalid_output_root_does_not_modify_source_repository(task, model):
    from repropatch.errors import ReproPatchError

    target = task.repository / "outputs"
    with pytest.raises(ReproPatchError, match="ROOT_OVERLAP"):
        Harness(task, model, target, sandbox_factory=SimulatedSandbox)
    assert not target.exists()


def test_frozen_task_matches_report_and_original_yaml(task, model, tmp_path):
    import hashlib

    from repropatch.task import canonical_json

    report = Harness(task, model, tmp_path / "runs", sandbox_factory=SimulatedSandbox).run()
    directory = Path(report["artifact_directory"])
    frozen = json.loads((directory / "task.resolved.json").read_text())
    assert frozen["task_sha256"] == report["task_sha256"]
    assert (
        hashlib.sha256(canonical_json(frozen["execution_contract"])).hexdigest()
        == report["task_sha256"]
    )
    assert (directory / "task.original.yaml").read_bytes() == task.source_bytes
