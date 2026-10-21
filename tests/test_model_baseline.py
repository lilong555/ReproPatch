"""真实工程规模的初始模型视图不得重复携带通过测试的原始日志。"""

import copy

from repropatch.task import canonical_json
from repropatch.tools import model_baseline


def test_large_baseline_keeps_observations_failure_bytes_and_original_evidence():
    record = {
        "evaluation_id": "baseline",
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
    view = model_baseline(record)
    assert record == original
    assert len(view["tests"]) == 200
    assert [item["name"] for item in view["tests"]] == [item["name"] for item in record["tests"]]
    assert view["evidence"] == record["evidence"]
    assert view["configure"]["exit_code"] == view["build"]["exit_code"] == 0
    assert len(view["failed_commands"]) == 1
    failed = view["failed_commands"][0]
    assert failed["stdout"] == original["commands"][0]["stdout"]
    assert failed["stderr"] == original["commands"][0]["stderr"]
    assert "output" not in failed
    assert len(canonical_json(view)) < 40 * 1024
