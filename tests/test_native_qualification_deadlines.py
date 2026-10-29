"""大型原生套件获得完整阶段预算，显式资格期限始终优先。"""

import argparse
import importlib
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
qualification = importlib.import_module("qualify_cross_repo")
adapter = importlib.import_module("cpp_native_adapter")


def test_duckdb_baseline_and_cold_oracle_have_independent_phase_deadlines(tmp_path, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(qualification.time, "monotonic", lambda: clock[0])
    configuration = adapter.recipe({"org": "duckdb", "repo": "duckdb"})
    executor = qualification.NativeExecutor("native", None, tmp_path, 10000.0, configuration)

    def baseline(self, source, phase, required, selected=None):
        assert phase == "baseline"
        assert self.deadline == 3700.0
        clock[0] += 2000  # O3 编译超过旧的 1800 秒阶段限制后仍有测试时间。
        assert clock[0] < self.deadline
        return {"status": "TESTS_FAILED", "tests": {"regression": "failed", "control": "passed"}}

    monkeypatch.setattr(qualification.Executor, "suite", baseline)
    baseline_result = executor.suite(tmp_path, "baseline", ["regression", "control"])
    assert baseline_result["status"] == "TESTS_FAILED"
    assert executor.deadline == 10000.0
    clock[0] = 3000.0
    stages = []

    def run(command, source, build, phase, stage):
        stages.append(stage)
        assert executor.deadline == 6600.0
        clock[0] += 2000 if stage == "build" else 10
        assert clock[0] < executor.deadline
        if stage == "ctest":
            build.mkdir(parents=True)
            (build / "native-results.json").write_text(
                json.dumps(
                    {
                        "tests": {"regression": "passed", "control": "passed"},
                        "missing": [],
                        "additional_failures": [],
                    }
                )
            )
        return {"exit_code": 0}

    monkeypatch.setattr(executor, "run", run)
    contract = {"mode": "duckdb", "groups": {"f2p": ["regression"], "p2p": ["control"]}}
    try:
        assert executor.native_oracle(tmp_path, "native-oracle", contract)["status"] == "PASSED"
        assert stages == ["configure", "build", "ctest"]
        assert executor.deadline == 10000.0
    finally:
        shutil.rmtree(executor.build_root)


@pytest.mark.parametrize("phase", ["baseline", "native_oracle"])
def test_phase_exception_restores_and_never_extends_outer_deadline(tmp_path, monkeypatch, phase):
    monkeypatch.setattr(qualification.time, "monotonic", lambda: 100.0)
    executor = qualification.NativeExecutor(
        "native", None, tmp_path, 500.0, adapter.recipe({"org": "duckdb", "repo": "duckdb"})
    )

    def fail(*args, **kwargs):
        assert executor.deadline == 500.0
        raise TimeoutError("TASK_DEADLINE")

    monkeypatch.setattr(qualification.Executor, "suite", fail)
    monkeypatch.setattr(executor, "run", fail)
    try:
        with pytest.raises(TimeoutError, match="TASK_DEADLINE"):
            if phase == "baseline":
                executor.suite(tmp_path, "baseline", [])
            else:
                executor.native_oracle(tmp_path, "native-oracle", {})
        assert executor.deadline == 500.0
    finally:
        shutil.rmtree(executor.build_root)


@pytest.mark.parametrize(
    ("org", "repo", "explicit", "expected"),
    [
        ("duckdb", "duckdb", None, 9000),
        ("duckdb", "duckdb", 60, 60),
        ("nlohmann", "json", None, 5400),
    ],
)
def test_qualify_respects_explicit_total_deadline(
    tmp_path, monkeypatch, org, repo, explicit, expected
):
    monkeypatch.setattr(qualification.time, "monotonic", lambda: 100.0)
    monkeypatch.setattr(qualification, "production_reference", lambda record: ("", []))
    deadlines = []

    def stop_preparation(*args, deadline):
        deadlines.append(deadline)
        raise TimeoutError("PREPARATION_STOP")

    monkeypatch.setattr(qualification, "materialize", stop_preparation)
    record = {
        "instance_id": f"{org}__{repo}-999999",
        "org": org,
        "repo": repo,
        "base": {"sha": "a" * 40},
        "fix_patch": "",
        "test_patch": "",
    }
    args = SimpleNamespace(
        output=tmp_path / "results",
        repository=tmp_path / "git",
        backend="native",
        image=None,
        cxx="c++",
        cc="cc",
        task_timeout=explicit,
    )
    result = qualification.qualify(record, args)
    assert deadlines == [100.0 + expected]
    assert result["qualification_timeout_seconds"] == expected
    assert result["status"] == "TIMED_OUT"


@pytest.mark.parametrize("value", ["0", "-1"])
def test_nonpositive_explicit_timeout_is_rejected(value):
    with pytest.raises(argparse.ArgumentTypeError, match="正整数"):
        qualification.positive_seconds(value)


def test_other_repositories_keep_previous_deadlines():
    configuration = adapter.recipe({"org": "nlohmann", "repo": "json"})
    assert configuration["phase_timeout_seconds"] == 1800
    assert configuration["qualification_timeout_seconds"] == 5400
