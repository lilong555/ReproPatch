"""基线与自检的模型反馈保留失败原因，避免重复传入成功日志。"""

import copy

import pytest

from repropatch.task import canonical_json
from repropatch.tools import model_evaluation


@pytest.mark.parametrize("role", ["baseline", "agent_check"])
def test_large_evaluation_keeps_observations_failure_bytes_and_original_evidence(role):
    record = {
        "evaluation_id": "baseline",
        "evaluation_role": role,
        "evidence": {"path": "baseline.json", "sha256": "a" * 64, "size_bytes": 900000},
        "configure": {"command_id": "configure", "status": "exited", "exit_code": 0},
        "build": {"command_id": "build", "status": "exited", "exit_code": 0},
        "tests": [],
        "commands": [],
    }
    for number in range(200):
        failed = number == 0
        identity = str(number)
        record["tests"].append(
            {
                "name": "regression" if failed else "control-" + identity,
                "group": "F2P" if failed else "P2P",
                "command_id": identity,
                "observed_status": "failed" if failed else "passed",
                "ctest_exit_code": 8 if failed else 0,
                "marker_seen": True if failed else None,
                "diagnostic": "Failed" if failed else "",
            }
        )
        record["commands"].append(
            {
                "command_id": identity,
                "stdout": "expected -3, got 0" if failed else "passed XML\n" * 4096,
                "stderr": "失败诊断\x00\x1b[31m" if failed else "",
                "stdout_log": {"path": identity + ".bin"},
                "output": "旧兼容别名",
            }
        )
    original = copy.deepcopy(record)
    view = model_evaluation(record)
    assert record == original
    assert len(view["tests"]) == 200
    assert [item["name"] for item in view["tests"]] == [item["name"] for item in record["tests"]]
    assert view["evidence"] == record["evidence"]
    assert view["evaluation_role"] == role
    assert view["configure"]["exit_code"] == view["build"]["exit_code"] == 0
    assert len(view["failed_commands"]) == 1
    failed = view["failed_commands"][0]
    assert failed["stdout"] == original["commands"][0]["stdout"]
    assert failed["stderr"] == original["commands"][0]["stderr"]
    assert "output" not in failed
    assert len(canonical_json(view)) < 40 * 1024


@pytest.mark.parametrize("phase", ["configure", "build", "discovery"])
def test_failed_phase_keeps_diagnostics_without_test_command(phase):
    command = {
        "command_id": phase,
        "status": "exited",
        "exit_code": 1,
        "error_code": None,
        "stdout": "编译器或 CTest 的原始诊断",
        "stderr": "error: invalid operands",
        "stdout_log": {"path": "stdout.bin"},
        "stderr_log": {"path": "stderr.bin"},
    }
    record = {
        "evaluation_id": "self-check",
        "evaluation_role": "agent_check",
        phase: command,
        "tests": [{"name": "regression", "observed_status": "not_run", "command_id": None}],
        "commands": [command],
        "issue_code": "COMMAND_FAILED",
        "cleanup": {"confirmed": True},
    }
    view = model_evaluation(record)
    assert view[phase]["exit_code"] == 1
    assert view["issue_code"] == "COMMAND_FAILED" and view["cleanup"]["confirmed"]
    assert view["failed_commands"][0]["stdout"] == command["stdout"]
    assert view["failed_commands"][0]["stderr"] == command["stderr"]
