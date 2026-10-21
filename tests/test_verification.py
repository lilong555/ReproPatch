"""结构化 CTest、外部输入与两条验收路径的重要失败边界。"""

import copy
import json
import os
import re
from pathlib import Path

import pytest
from conftest import ROOT, SimulatedSandbox, scripted

from repropatch.harness import Harness
from repropatch.process import CommandResult
from repropatch.verification import (
    EvidenceInvalid,
    UnsupportedLayout,
    literal_selector,
    parse_inventory,
    parse_junit,
)
from repropatch.workspace import Worktree, git

SAMPLES = ROOT / "docs/evidence/p1-06/ctest-samples"


def verify(task, patch, tmp_path, factory=SimulatedSandbox, **kwargs):
    return Harness(
        task, output_root=tmp_path / "runs", patch_file=patch, sandbox_factory=factory, **kwargs
    ).run()


@pytest.mark.parametrize(
    "name,status,code",
    [
        ("passed", "passed", 0),
        ("failed", "failed", 8),
        ("skipped", "skipped", 0),
        ("disabled", "not_run", 0),
        ("timed_out", "timed_out", 8),
        ("crashed", "crashed", 8),
        ("will_fail", "passed", 0),
    ],
)
def test_real_ctest_samples_have_distinct_statuses(name, status, code):
    command = CommandResult(("ctest",), code, "", 0.01)
    assert parse_junit((SAMPLES / (name + ".xml")).read_bytes(), name, command)[0] == status


@pytest.mark.parametrize(
    "mutation",
    [
        "empty",
        "broken",
        "extra",
        "wrong-name",
        "count",
        "unknown-status",
        "zero-failure",
        "dtd",
        "deep",
        "nested",
        "missing-time",
    ],
)
def test_junit_cannot_turn_missing_or_contradictory_evidence_into_success(mutation):
    data = (SAMPLES / "passed.xml").read_bytes()
    if mutation == "empty":
        data = b""
    if mutation == "broken":
        data = data[:-20]
    if mutation == "extra":
        data = data.replace(
            b"</testsuite>",
            data[data.index(b"<testcase") : data.index(b"</testcase>") + 11] + b"</testsuite>",
        )
    if mutation == "wrong-name":
        data = data.replace(b"passed", b"other")
    if mutation == "count":
        data = data.replace(b'tests="1"', b'tests="0"')
    if mutation == "unknown-status":
        data = data.replace(b'status="run"', b'status="success"')
    if mutation == "zero-failure":
        data = (SAMPLES / "failed.xml").read_bytes()
    if mutation == "dtd":
        data = b'<!DOCTYPE testsuite [<!ENTITY x "yes">]>' + data
    if mutation == "deep":
        data = b"<a>" * 33 + b"</a>" * 33
    if mutation == "nested":
        data = data.replace(b"<system-out>", b"<system-out><unexpected/>")
    if mutation == "missing-time":
        data = re.sub(rb' time="[^"]+"', b"", data)
    with pytest.raises(EvidenceInvalid):
        parse_junit(
            data,
            "failed" if mutation == "zero-failure" else "passed",
            CommandResult(("ctest",), 0, "", 0.01),
        )


def test_inventory_identity_preserves_types_and_order_but_ignores_backtrace():
    raw = json.loads((SAMPLES / "inventory.json").read_bytes())
    names = {"passed", "parse[value]+edge"}
    original = parse_inventory(json.dumps(raw).encode(), names)
    changed = copy.deepcopy(raw)
    for item in changed["tests"]:
        item["backtrace"] = 999
        item["properties"].reverse()
    assert parse_inventory(json.dumps(changed).encode(), names) == original
    item = next(item for item in changed["tests"] if item["name"] == "passed")
    item["properties"].append({"name": "ENVIRONMENT", "value": ["A=1", "B=2"]})
    first = parse_inventory(json.dumps(changed).encode(), names)
    item["properties"][-1]["value"].reverse()
    assert parse_inventory(json.dumps(changed).encode(), names) != first
    item["properties"][-1]["value"] = True
    a = parse_inventory(json.dumps(changed).encode(), names)
    item["properties"][-1]["value"] = "true"
    assert parse_inventory(json.dumps(changed).encode(), names) != a


@pytest.mark.parametrize("bad", ["duplicate", "command", "property", "fixture", "version", "depth"])
def test_inventory_rejects_unsupported_or_ambiguous_selected_tests(bad):
    raw = json.loads((SAMPLES / "inventory.json").read_bytes())
    selected = next(item for item in raw["tests"] if item["name"] == "passed")
    if bad == "duplicate":
        raw["tests"].append(selected)
    if bad == "command":
        selected["command"] = []
    if bad == "property":
        selected["properties"].append(selected["properties"][0])
    if bad == "fixture":
        selected["properties"].append({"name": "FIXTURES_REQUIRED", "value": ["setup"]})
    if bad == "version":
        raw["version"]["major"] = True
    if bad == "depth":
        selected["properties"].append(
            {"name": "NESTED", "value": json.loads("[" * 35 + "0" + "]" * 35)}
        )
    with pytest.raises(UnsupportedLayout if bad == "fixture" else EvidenceInvalid):
        parse_inventory(json.dumps(raw).encode(), {"passed"})


@pytest.mark.sdk
def test_external_patch_and_automatic_repair_use_same_verifier(
    task, model, tmp_path, external_patch
):
    patch = external_patch(context=1)
    original = patch.read_bytes()
    report = verify(task, patch, tmp_path)
    automatic = Harness(task, model, tmp_path / "automatic", sandbox_factory=SimulatedSandbox).run()
    assert report["outcome"] == automatic["outcome"] == "ACCEPTED"
    assert report["provenance"]["task_sha256"] == automatic["provenance"]["task_sha256"]
    assert report["engine"]["kind"] == "none" and report["agent"] == {
        "agent_stop_reason": None,
        "steps_used": 0,
        "tool_calls_used": 0,
        "http_attempts": 0,
    }
    assert report["usage"] == {
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "synthetic": False,
    }
    assert report["cost"] is None
    root = Path(report["artifact_directory"])
    assert (root / "producer/input.patch").read_bytes() == original
    assert (root / "patch.diff").read_bytes() != original
    assert report["baseline"]["evaluation_role"] == "baseline"
    assert report["independent"]["evaluation_role"] == "independent"
    assert report["baseline"]["identities"] == report["independent"]["identities"]
    assert len(report["baseline"]["tests"]) == len(report["independent"]["tests"]) == 4
    assert patch.read_bytes() == original and git(task.repository, "status", "--porcelain") == ""


@pytest.mark.parametrize(
    "change",
    [
        "identity",
        "duplicate",
        "fixture",
        "missing",
        "disabled",
        "skip",
        "missing-junit",
        "malformed-junit",
        "later-evidence-failure",
    ],
)
def test_candidate_evidence_never_accepts_skip_identity_change_or_missing_results(
    task, tmp_path, external_patch, change
):
    class Changed(SimulatedSandbox):
        def inventory(self):
            raw = super().inventory()
            if "independent" in self.source.name:
                if change == "duplicate":
                    raw["tests"].append(copy.deepcopy(raw["tests"][0]))
                if change == "fixture":
                    raw["tests"][0]["properties"].append(
                        {"name": "FIXTURES_REQUIRED", "value": ["setup"]}
                    )
                if change == "identity":
                    raw["tests"][0]["command"].append("altered")
                if change == "missing":
                    raw["tests"].pop(0)
                if change == "disabled":
                    raw["tests"][0]["properties"].append({"name": "DISABLED", "value": True})
            return raw

        def execute_test(self, name):
            if "independent" in self.source.name and name == "negative_values":
                if change == "skip":
                    return 0, "skipped", "skip"
                if change == "later-evidence-failure":
                    return 8, "failed", "wrong"
            return super().execute_test(name)

        def run(self, argv):
            if (
                "independent" in self.source.name
                and argv[0] == "/bin/sh"
                and len(argv) > 3
                and argv[3] == "repropatch-read"
            ):
                data = self.results[argv[-1]]
                if change == "missing-junit":
                    return self.result(argv, 1, "missing")
                if change == "malformed-junit":
                    return self.result(argv, 0, b"<testsuite>")
                if change == "later-evidence-failure" and b"positive_values" in data:
                    return self.result(argv, 0, b"")
            return super().run(argv)

    report = verify(task, external_patch(), tmp_path, Changed)
    assert report["outcome"] == (
        "INCONCLUSIVE" if change in {"missing-junit", "malformed-junit"} else "REJECTED"
    ), report
    assert report["reproduced"] and not report["verified"]
    if change == "later-evidence-failure":
        assert report["reason_code"] == "F2P_FAILED"
    if change == "skip":
        test = report["independent"]["tests"][0]
        assert test["observed_status"] == "skipped" and test["ctest_exit_code"] == 0


@pytest.mark.parametrize("where", ["stdout", "stderr", "middle", "cross"])
def test_baseline_signature_uses_complete_individual_raw_streams(
    task, tmp_path, external_patch, where
):
    class Signature(SimulatedSandbox):
        def run(self, argv):
            result = super().run(argv)
            if (
                self.source.name.endswith("baseline")
                and argv[0] == "ctest"
                and "--output-junit" in argv
                and "negative_values" in argv[argv.index("-R") + 1]
            ):
                marker = b"expected -3, got 0"
                output = (
                    marker
                    if where == "stdout"
                    else b"x" * 100000 + marker + b"y" * 100000
                    if where == "middle"
                    else b"expected -3,"
                    if where == "cross"
                    else b""
                )
                error = marker if where == "stderr" else b" got 0" if where == "cross" else b""
                return self.result(argv, 8, output, stderr=error)
            return result

    report = verify(task, external_patch(), tmp_path, Signature)
    assert report["outcome"] == ("NOT_REPRODUCED" if where == "cross" else "ACCEPTED"), report
    assert report["baseline"]["tests"][0]["marker_seen"] is (where != "cross")


@pytest.mark.parametrize(
    "kind", ["empty", "malformed", "protected", "mode", "new", "delete", "binary", "escape"]
)
def test_external_patch_policy_rejection_happens_before_any_container(task, tmp_path, kind):
    with Worktree(task.repository, tmp_path / "producer", task.revision) as work:
        if kind == "protected":
            (work.path / "tests/stats_test.cpp").write_bytes(b"changed\n")
        elif kind == "mode":
            (work.path / "src/stats.cpp").chmod(0o755)
        elif kind == "delete":
            (work.path / "src/stats.cpp").unlink()
        elif kind == "binary":
            (work.path / "src/stats.cpp").write_bytes(b"\0binary")
        content = work.diff_bytes()
    if kind == "empty":
        content = b""
    if kind == "malformed":
        content = b"not a patch"
    if kind == "new":
        content = (
            b"diff --git a/new.cpp b/new.cpp\nnew file mode 100644\n"
            b"--- /dev/null\n+++ b/new.cpp\n@@ -0,0 +1 @@\n+int x;\n"
        )
    if kind == "escape":
        content = b"--- a/../../outside.cpp\n+++ b/../../outside.cpp\n@@ -1 +1 @@\n-old\n+new\n"
    path = tmp_path / "input.patch"
    path.write_bytes(content)
    sentinel = tmp_path / "outside.cpp"
    sentinel.write_bytes(b"keep")

    def forbidden(source):
        pytest.fail("策略检查失败前不能创建执行容器")

    index = (task.repository / ".git/index").read_bytes()
    report = verify(task, path, tmp_path, forbidden)
    assert (
        report["outcome"] == "REJECTED"
        and report["baseline"] is None
        and report["independent"] is None
    ), report
    assert (
        sentinel.read_bytes() == b"keep" and (task.repository / ".git/index").read_bytes() == index
    )


@pytest.mark.parametrize("kind", ["symlink", "fifo", "directory", "oversize"])
def test_external_input_must_be_complete_bounded_regular_file(task, tmp_path, kind):
    path = tmp_path / "input.patch"
    if kind == "symlink":
        target = tmp_path / "real"
        target.write_bytes(b"data")
        path.symlink_to(target)
    elif kind == "fifo":
        os.mkfifo(path)
    elif kind == "directory":
        path.mkdir()
    else:
        path.write_bytes(b"x" * (8 * 1024 * 1024 + 1))
    report = verify(task, path, tmp_path, lambda source: pytest.fail("无效输入不允许执行"))
    assert report["outcome"] == "ERROR" and report["baseline"] is None


def test_untrusted_producer_trace_does_not_change_failed_patch_or_usage(
    task, tmp_path, external_patch
):
    class Wrong(SimulatedSandbox):
        def execute_test(self, name):
            if name == "negative_values":
                return 8, "failed", "expected -3, got 0"
            return super().execute_test(name)

    trace = tmp_path / "trace.json"
    trace.write_text('{"outcome":"ACCEPTED","tokens":0,"run":"touch /tmp/forbidden"}')
    report = verify(
        task,
        external_patch("int best = -1;"),
        tmp_path,
        Wrong,
        producer="external",
        producer_trace=trace,
    )
    assert (
        report["outcome"] == "REJECTED"
        and report["producer"]["trace_trust"] == "external-untrusted"
    )
    assert report["trace"]["path"] == "events.jsonl" and report["usage"]["total_tokens"] is None
    assert (
        Path(report["artifact_directory"]) / "producer/trace.bin"
    ).read_bytes() == trace.read_bytes()


def test_selector_escapes_ctest_regular_expression_metacharacters():
    name = "parse[value]+edge"
    assert re.fullmatch(literal_selector(name), name)
    assert not re.fullmatch(literal_selector(name), "parsevvedge")


def test_baseline_uncertainty_and_regression_take_priority_over_f2p_pass(
    task, tmp_path, external_patch
):
    class Regression(SimulatedSandbox):
        def execute_test(self, name):
            if self.source.name.endswith("baseline"):
                return (
                    (8, "failed", "regression")
                    if name == "positive_values"
                    else (0, "passed", "pass")
                )
            pytest.fail("基线 P2P 失败不能进入独立执行")

    report = verify(task, external_patch(), tmp_path, Regression)
    assert (
        report["outcome"] == "INCONCLUSIVE"
        and report["reason_code"] == "BASELINE_REGRESSION_FAILED"
    )
    assert report["agent"]["steps_used"] == 0 and report["independent"] is None


@pytest.mark.sdk
def test_saved_baseline_corruption_is_error_and_never_starts_independent(task, model, tmp_path):
    from agents.testing import ModelStep, ScriptedModel, assistant_message, function_call

    def corrupt(call):
        run = next((tmp_path / "runs").iterdir())
        saved = next(
            json.loads(path.read_bytes())
            for path in (run / "evidence").glob("*/evaluation.json")
            if json.loads(path.read_bytes())["evaluation_role"] == "baseline"
        )
        (run / saved["source_manifest"]["path"]).write_bytes(b"corrupt")
        return ModelStep(output=[assistant_message("完成")])

    selected = ScriptedModel(
        [
            ModelStep(
                output=[
                    function_call(
                        "edit_file",
                        {
                            "path": "src/stats.cpp",
                            "old": "int best = 0;",
                            "new": "int best = samples.front();",
                        },
                        call_id="edit",
                    )
                ]
            ),
            ModelStep(responder=corrupt),
        ]
    )
    report = Harness(task, selected, tmp_path / "runs", sandbox_factory=SimulatedSandbox).run()
    assert report["outcome"] == "ERROR" and report["reason_code"] == "ARTIFACT_CORRUPT"
    assert report["independent"] is None and not report["artifacts_complete"]


def test_independent_deadline_cannot_be_replaced_by_agent_check(
    task, tmp_path, external_patch, monkeypatch
):
    from repropatch.verification import RunClock, StageDeadline

    original = RunClock.timeout

    def limited(self, role, cap):
        if role == "independent":
            raise StageDeadline("验证时间耗尽")
        return original(self, role, cap)

    monkeypatch.setattr(RunClock, "timeout", limited)
    report = verify(task, external_patch(), tmp_path)
    assert report["outcome"] == "INCONCLUSIVE" and report["reason_code"] == "VERIFICATION_TIMEOUT"
    assert report["reproduced"] and report["independent"] is None


@pytest.mark.sdk
def test_agent_check_unknown_cleanup_stops_before_another_model_turn(task, tmp_path):
    from repropatch.errors import CleanupUnconfirmed

    class BrokenCleanup(SimulatedSandbox):
        def __exit__(self, *args):
            if "agent-check" in self.source.name:
                raise CleanupUnconfirmed("未知清理状态")

    actions = [{"tool": "run_command", "arguments": {"name": "verify"}}, {"finish": "不得请求此轮"}]
    model = scripted(actions)
    report = Harness(task, model, tmp_path / "runs", sandbox_factory=BrokenCleanup).run()
    assert len(model.calls) == 1 and report["outcome"] == "ERROR"
    assert (
        report["reason_code"] == "CLEANUP_UNCONFIRMED"
        and not report["cleanup"]["active_code_stopped"]
    )
