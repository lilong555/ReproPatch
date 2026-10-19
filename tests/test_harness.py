import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import SimulatedSandbox, TrustedLocalSandbox

from repropatch.harness import Harness
from repropatch.models import MockModel
from repropatch.process import CommandResult
from repropatch.workspace import git


def test_complete_flow_unit(task, model, tmp_path):
    report = Harness(task, model, tmp_path / "runs", sandbox_factory=SimulatedSandbox).run()
    assert report["status"] == "passed" and report["reproduced"] and report["verified"]
    assert report["isolated"] is False
    directory = Path(report["artifact_directory"])
    assert "samples.front()" in (directory / "patch.diff").read_text()
    events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
    with sqlite3.connect(directory / "events.sqlite3") as db:
        rows = db.execute("SELECT seq,kind,payload FROM events ORDER BY seq").fetchall()
    assert len(events) == len(rows)
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    assert all(
        json.loads(row[2]) == event["payload"] for row, event in zip(rows, events, strict=True)
    )
    assert events[-1]["kind"] == "run_finished"
    assert not (directory / "worktrees/repair").exists()
    assert not (directory / "worktrees/validation").exists()
    assert git(task.repository, "status", "--porcelain") == ""
    baseline, _, independent = report["evaluations"]
    assert baseline["source_sha256"] != independent["source_sha256"]
    assert baseline["commands"][-1]["returncode"] == 8
    assert all(c["returncode"] == 0 for c in independent["commands"])


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
        def run(self, argv):
            source = (self.source / "src/stats.cpp").read_text()
            failure = argv[0] == "ctest" and "samples.front()" not in source
            return CommandResult(
                tuple(argv), 8 if failure else 0, "expected -3, got 0" if failure else "pass", 0.001
            )

    report = Harness(task, MockModel(actions), tmp_path / "runs", sandbox_factory=Strict).run()
    assert report["status"] == status and not report["verified"]


@pytest.mark.parametrize(
    "mode,status",
    [
        ("pass", "not_reproduced"),
        ("timeout", "not_reproduced"),
        ("wrong-marker", "not_reproduced"),
        ("build", "baseline_setup_failed"),
    ],
)
def test_baseline_failure_is_checked(task, tmp_path, mode, status):
    class BadBaseline(SimulatedSandbox):
        def run(self, argv):
            if argv[0] == "ctest":
                return CommandResult(
                    tuple(argv),
                    0 if mode == "pass" else 8,
                    "unrelated" if mode == "wrong-marker" else "expected -3, got 0",
                    0.01,
                    mode == "timeout",
                )
            return CommandResult(tuple(argv), 1 if mode == "build" else 0, "build", 0.01)

    report = Harness(task, MockModel([]), tmp_path / "runs", sandbox_factory=BadBaseline).run()
    assert report["status"] == status and report["model_steps"] == 0


def test_denied_tool_is_visible_to_model(task, tmp_path, model):
    script = [{"tool": "read_file", "arguments": {"path": "/etc/passwd"}}, {"finish": "stop"}]
    report = Harness(
        task, MockModel(script), tmp_path / "runs", sandbox_factory=SimulatedSandbox
    ).run()
    events = (Path(report["artifact_directory"]) / "events.jsonl").read_text()
    assert '"ok": false' in events and report["status"] == "no_patch"


def test_independent_verification_catches_regression(task, model, tmp_path):
    class Regression(SimulatedSandbox):
        def run(self, argv):
            if "independent" in self.source.name and "-R" not in argv and argv[0] == "ctest":
                return CommandResult(tuple(argv), 8, "empty_values failed", 0.01)
            return super().run(argv)

    report = Harness(task, model, tmp_path / "runs", sandbox_factory=Regression).run()
    assert report["status"] == "failed" and not report["verified"]


def test_error_still_writes_report_and_cleans_worktree(task, tmp_path):
    class BrokenModel:
        def complete(self, messages, tools):
            from repropatch.errors import ReproPatchError

            raise ReproPatchError("model offline")

    report = Harness(task, BrokenModel(), tmp_path / "runs", sandbox_factory=SimulatedSandbox).run()
    assert report["status"] == "error" and report["error"] == "model offline"
    assert not (Path(report["artifact_directory"]) / "worktrees/repair").exists()


@pytest.mark.integration
def test_real_cpp_reproduce_repair_verify(task, model, tmp_path):
    report = Harness(task, model, tmp_path / "runs", sandbox_factory=TrustedLocalSandbox).run()
    assert report["status"] == "passed", report
    assert report["isolated"] is False
    baseline = report["evaluations"][0]
    assert "expected -3, got 0" in baseline["commands"][-1]["output"]
    final = report["evaluations"][-1]
    output = final["commands"][-1]["output"]
    assert "100% tests passed" in output and "out of 4" in output
    for name in ("negative_values", "positive_values", "empty_values", "mixed_values"):
        assert name in output


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
        replace(task, max_steps=3),
        MockModel(actions),
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
        replace(task, max_steps=1),
        MockModel(actions),
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
    ).run()
    assert report["status"] == "budget_exhausted"
    assert "samples.front()" in (Path(report["artifact_directory"]) / "patch.diff").read_text()


def test_model_exception_does_not_lose_candidate_patch(task, tmp_path):
    class FaultyModel:
        def __init__(self):
            self.calls = 0

        def complete(self, messages, tools):
            self.calls += 1
            if self.calls == 1:
                from repropatch.models import ToolCall, Turn

                return Turn(
                    calls=[
                        ToolCall(
                            "1",
                            "edit_file",
                            {
                                "path": "src/stats.cpp",
                                "old": "int best = 0;",
                                "new": "int best = -1;",
                            },
                        )
                    ]
                )
            raise RuntimeError("sensitive plugin detail")

    report = Harness(task, FaultyModel(), tmp_path / "runs", sandbox_factory=SimulatedSandbox).run()
    assert report["status"] == "internal_error"
    assert "sensitive" not in report["error"]
    assert "int best = -1;" in (Path(report["artifact_directory"]) / "patch.diff").read_text()


def test_changing_execution_image_is_rejected(task, model, tmp_path):
    class DriftingImage(SimulatedSandbox):
        @property
        def image_id(self):
            return "sha256:" + ("a" if "baseline" in self.source.name else "b") * 64

    report = Harness(task, model, tmp_path / "runs", sandbox_factory=DriftingImage).run()
    assert report["status"] == "error" and "image changed" in report["error"]
