"""阻止计划阶段访问凭据或执行，以及把 fake 结果当作真实接口认证。"""

import json
import runpy

import pytest
from conftest import ROOT, SimulatedSandbox

from repropatch.harness import Harness


@pytest.fixture
def gate():
    return runpy.run_path(str(ROOT / "scripts/check_live_gate.py"))


@pytest.mark.parametrize("execute", [False, True])
def test_preparation_and_missing_consent_have_no_model_or_files(
    gate, tmp_path, monkeypatch, capsys, execute
):
    class Guard(dict):
        def get(self, name, *args):
            if name == "LIVE_GATE_KEY":
                pytest.fail("准备或未授权时不能读取凭据")
            return super().get(name, *args)

    monkeypatch.setattr("repropatch.models.os.environ", Guard())
    output = tmp_path / "new-live-run"
    args = [
        "--task",
        str(ROOT / "examples/tasks/negative-maximum.live.v2.yaml"),
        "--model",
        "configured-model",
        "--key-env",
        "LIVE_GATE_KEY",
        "--use-env-proxy",
        "--output",
        str(output),
    ]
    if execute:
        args.append("--execute")
    code = gate["main"](args)
    captured = capsys.readouterr()
    assert not output.exists()
    if execute:
        assert code == 2 and "PAID_MODEL_CONSENT_REQUIRED" in captured.err
    else:
        assert code == 0
        plan = json.loads(captured.out)
        assert plan["status"] == "prepared"
        assert plan["budget"]["max_steps"] == 6 and plan["budget"]["max_tool_calls"] == 12
        assert plan["cost_usd"] is None and plan["automatic_run_retries"] == 0
        assert plan["use_env_proxy"] is True


@pytest.mark.sdk
def test_fake_repair_is_never_real_endpoint_certification(gate, task, model, tmp_path):
    report = Harness(task, model, tmp_path / "runs", sandbox_factory=SimulatedSandbox).run()
    result = gate["live_observations"](report["artifact_directory"])
    assert report["outcome"] == "ACCEPTED" and result["tool_round_trips"]
    assert result["status"] == "failed" and "REAL_ENGINE_REQUIRED" in result["failures"]
