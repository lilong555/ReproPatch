"""Native SDK projection reads complete, verified command evidence behind previews."""

import json
from dataclasses import replace

import pytest

from repropatch.context import ContextPolicy


@pytest.mark.sdk
def test_runtime_hydrates_truncated_compiler_preview_without_changing_raw_receipt(task, tmp_path):
    from agents.testing import ScriptedModel, assistant_message, function_call
    from conftest import SimulatedSandbox

    from repropatch.harness import Harness

    log = "src/stats.cpp:5:3: error: repeated compiler diagnostic\n" * 1000
    log += "src/tail.cpp:99:2: error: unique tail beyond preview\n"

    class PreviewSandbox(SimulatedSandbox):
        def execute_test(self, name):
            code, status, text = super().execute_test(name)
            return code, status, log + text if code else text

        def result(self, *args, **kwargs):
            value = super().result(*args, **kwargs)
            if len(value.stdout.encode()) > 32768:
                value = replace(value, stdout=value.stdout[:32768], truncated=True)
            return value

    model = ScriptedModel(
        [
            [function_call("run_command", {"name": "reproduce"}, call_id="check")],
            [assistant_message("Done")],
        ]
    )
    harness = Harness(
        task,
        model,
        tmp_path / "runs",
        sandbox_factory=PreviewSandbox,
        context_policy=ContextPolicy(diagnostic_extraction=True),
        candidate_only=True,
    )
    report = harness.run()
    assert report["agent_stop_reason"] == "MODEL_FINISHED", report
    model.assert_complete()
    raw = json.loads((harness.directory / "agent/tool-results/s000001.t01.json").read_text())
    raw_command = raw["data"]["failed_commands"][0]
    assert raw_command["truncated"] is True
    assert len(raw_command["stdout"]) == 32768
    assert "unique tail" not in raw_command["stdout"]
    returned = next(v for v in model.calls[-1].input if v.get("type") == "function_call_output")
    visible = json.loads(returned["output"])
    parsed = visible["data"]["failed_commands"][0]["stdout"]
    assert parsed["diagnostics"][0]["occurrences"] == 1000
    assert parsed["diagnostics"][-1]["message"] == "unique tail beyond preview"
    assert parsed["full_log_ref"] == raw_command["stdout_log"]
    assert visible["progress"] == raw["progress"]
    assert visible["data"]["tests"] == raw["data"]["tests"]
    assert "unique tail" in (harness.directory / raw_command["stdout_log"]["path"]).read_text()
    assert (
        report["context"]["optimization_state"]["metrics"]["diagnostic_extraction"]["triggers"] == 1
    )
