"""工程验收对演示身份、目录归属和零付费声明的检查。"""

import copy
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import SimulatedSandbox

from repropatch.artifacts import AuditBudget
from repropatch.harness import Harness


@pytest.fixture
def gate():
    path = Path(__file__).resolve().parents[1] / "scripts/check_engineering_gate.py"
    spec = importlib.util.spec_from_file_location("engineering_gate_contract", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def demo_result(tmp_path):
    return {
        "status": "passed",
        "model_kind": "scripted",
        "paid_model_requests": 0,
        "runs": [
            {
                "scenario": scenario,
                "run_id": str(index) * 32,
                "artifact_directory": str(tmp_path / "demo" / "runs" / (str(index) * 32)),
                "outcome": outcome,
            }
            for index, (scenario, outcome) in enumerate(
                (("repair", "ACCEPTED"), ("rejection", "REJECTED"), ("recovery", "ACCEPTED")),
                1,
            )
        ],
    }


def test_gate_accepts_complete_independent_scenarios(gate, demo_result, tmp_path):
    rows = gate.validate_demo(demo_result, tmp_path / "demo")
    assert set(rows) == {"repair", "rejection", "recovery"}


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "failed"),
        ("model_kind", "live"),
        ("paid_model_requests", 1),
        ("paid_model_requests", False),
        ("paid_model_requests", None),
    ],
)
def test_gate_rejects_incompatible_execution_claims(gate, demo_result, tmp_path, field, value):
    demo_result[field] = value
    with pytest.raises(ValueError):
        gate.validate_demo(demo_result, tmp_path / "demo")


@pytest.mark.parametrize("change", ["missing", "duplicate", "outside", "run_id", "outcome"])
def test_gate_checks_each_scenario_identity(gate, demo_result, tmp_path, change):
    value = copy.deepcopy(demo_result)
    if change == "missing":
        value["runs"].pop()
    elif change == "duplicate":
        value["runs"][1] = copy.deepcopy(value["runs"][0])
    elif change == "outside":
        value["runs"][0]["artifact_directory"] = str(tmp_path / ("1" * 32))
    elif change == "run_id":
        value["runs"][0]["run_id"] = "../other"
    else:
        value["runs"][0]["outcome"] = "REJECTED"
    with pytest.raises(ValueError):
        gate.validate_demo(value, tmp_path / "demo")


def test_fingerprint_detects_changes_and_refuses_linked_evidence(gate, tmp_path):
    (tmp_path / "events.sqlite3").write_bytes(b"database")
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"state": "FINISHED"}))
    before = gate.fingerprint(tmp_path)
    report.write_text(json.dumps({"state": "INTERRUPTED"}))
    assert before != gate.fingerprint(tmp_path)
    (tmp_path / "linked").symlink_to(report)
    with pytest.raises(ValueError, match="链接"):
        gate.fingerprint(tmp_path)


@pytest.mark.parametrize("scenario", ["repair", "rejection"])
def test_audit_reads_serialized_evaluation_contract(gate, task, external_patch, tmp_path, scenario):
    class CandidateSandbox(SimulatedSandbox):
        def execute_test(self, name):
            source = (self.source / "src/stats.cpp").read_text()
            if name == "negative_values" and "int best = -1;" in source:
                return 8, "failed", "expected -3, got -1"
            return super().execute_test(name)

    patch = external_patch(
        "int best = -1;" if scenario == "rejection" else "int best = samples.front();"
    )
    report = Harness(task, patch_file=patch, sandbox_factory=CandidateSandbox).run()
    directory = Path(report["artifact_directory"])
    query_root = tmp_path / "queries"
    query_root.mkdir()
    # 此测试只核对报告格式，隔离与脚本模型身份由真实 Docker gate 验证。
    report.update(isolated=True, engine={"kind": "fake"})
    report["agent"]["http_attempts"] = 0
    assert "successful" not in report["independent"]

    def execute(name, arguments):
        from repropatch.diagnostics import diagnose_run
        from repropatch.reports import inspect_run
        from repropatch.trace import export_trace, replay_trace

        command = arguments[0]
        if command == "report":
            return json.dumps(report)
        if command == "export-trace":
            _, problems = export_trace(directory, Path(arguments[-1]))
            assert not problems
            return ""
        query = {"inspect": inspect_run, "diagnose": diagnose_run, "replay": replay_trace}[command]
        return json.dumps(query(directory))

    result = gate.audit_run(
        {"scenario": scenario, "run_id": directory.name, "artifact_directory": str(directory)},
        query_root,
        execute,
    )
    assert result["outcome"] == gate.EXPECTED[scenario]
    assert result["independent_successful"] is (scenario != "rejection")
    assert result["readonly_queries_preserved_all_files"]


def test_gate_preflight_preserves_existing_run(gate, task, external_patch, monkeypatch, capsys):
    report = Harness(task, patch_file=external_patch(), sandbox_factory=SimulatedSandbox).run()
    assert report["outcome"] == "ACCEPTED" and report["artifacts_complete"]
    directory = Path(report["artifact_directory"])
    before = {
        path.relative_to(directory): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }
    audit_bytes = AuditBudget(directory).usage()
    output = directory / "nested-engineering-output"
    monkeypatch.setattr(sys, "argv", ["engineering-gate", "--output", str(output)])

    def forbidden(*args, **kwargs):
        pytest.fail("既有 Run 路径预检须先于 CLI 执行")

    monkeypatch.setattr(gate.subprocess, "run", forbidden)
    with pytest.raises(SystemExit) as stopped:
        gate.main()
    assert stopped.value.code == 2
    assert "DEMO_ROOT_OVERLAP" in capsys.readouterr().err
    assert not output.exists()
    assert {
        path.relative_to(directory): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    } == before
    assert AuditBudget(directory).usage() == audit_bytes


@pytest.mark.parametrize("kind", ["parent", "directory", "dangling"])
def test_gate_preflight_preserves_linked_paths(gate, tmp_path, monkeypatch, capsys, kind):
    target = tmp_path / "target"
    target.mkdir()
    original = target / "keep.txt"
    original.write_bytes(b"keep")
    missing = tmp_path / "missing"
    link = tmp_path / "linked"
    link.symlink_to(missing if kind == "dangling" else target, target_is_directory=True)
    output = link / "nested" if kind == "parent" else link
    monkeypatch.setattr(sys, "argv", ["engineering-gate", "--output", str(output)])

    def forbidden(*args, **kwargs):
        pytest.fail("链接路径预检须先于 CLI 执行")

    monkeypatch.setattr(gate.subprocess, "run", forbidden)
    with pytest.raises(SystemExit) as stopped:
        gate.main()
    assert stopped.value.code == 2
    assert "DEMO_OUTPUT_SYMLINK" in capsys.readouterr().err
    assert link.is_symlink()
    assert sorted(target.iterdir()) == [original]
    assert original.read_bytes() == b"keep"
    assert not missing.exists()


def test_gate_preflight_rejects_parent_traversal(gate, tmp_path, monkeypatch, capsys):
    output = tmp_path / "new" / ".." / "elsewhere"
    monkeypatch.setattr(sys, "argv", ["engineering-gate", "--output", str(output)])

    def forbidden(*args, **kwargs):
        pytest.fail("父目录跳转预检须先于 CLI 执行")

    monkeypatch.setattr(gate.subprocess, "run", forbidden)
    with pytest.raises(SystemExit) as stopped:
        gate.main()
    assert stopped.value.code == 2
    assert "DEMO_OUTPUT_UNSAFE" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_gate_output_directories_are_private(gate, tmp_path, monkeypatch, capsys):
    output = tmp_path / "engineering-output"
    monkeypatch.setattr(
        sys,
        "argv",
        ["engineering-gate", "--output", str(output), "--require-installed-wheel"],
    )
    monkeypatch.setattr(
        gate, "distribution", lambda name: SimpleNamespace(read_text=lambda filename: "{}")
    )
    mask = os.umask(0o022)
    try:
        assert gate.main() == 1
    finally:
        os.umask(mask)
    capsys.readouterr()
    assert output.stat().st_mode & 0o777 == 0o700
    assert (output / "queries").stat().st_mode & 0o777 == 0o700
