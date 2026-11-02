"""确定性演示的 Harness、公开 SDK、恢复证据与目录保护契约。"""

import json
import os
from pathlib import Path

import pytest
from conftest import ROOT, SimulatedSandbox, TrustedLocalSandbox

import repropatch.demo as demo
from repropatch.artifacts import EvidenceRef
from repropatch.errors import ReproPatchError
from repropatch.events import read_events
from repropatch.reports import inspect_run
from repropatch.task import ImageIdentity, Task
from repropatch.workspace import git

pytestmark = pytest.mark.sdk
TEST_IMAGE = "sha256:" + "a" * 64


class DemoSimulatedSandbox(SimulatedSandbox):
    """显式模拟后端：错误初值也保留负数用例失败。"""

    def execute_test(self, name):
        source = (self.source / "src/stats.cpp").read_text()
        if name == "negative_values" and "int best = -1;" in source:
            return 8, "failed", "expected -3, got -1"
        return super().execute_test(name)


def run_simulated(output, scenario="all"):
    return demo.run_demo(output, TEST_IMAGE, scenario, sandbox_factory=DemoSimulatedSandbox)


def test_all_scenarios_use_complete_harness_and_public_scripted_sdk(tmp_path, monkeypatch):
    from agents.testing import ScriptedModel

    def forbid_paid_model(*args, **kwargs):
        pytest.fail("确定性演示调用了付费模型入口")

    monkeypatch.setattr("repropatch.models.responses_model", forbid_paid_model)
    original = demo.load_sdk_script
    models = []

    def capture(path, **kwargs):
        result = original(path, **kwargs)
        assert isinstance(result[0], ScriptedModel)
        models.append(result[0])
        return result

    monkeypatch.setattr(demo, "load_sdk_script", capture)
    result = run_simulated(tmp_path / "demo")
    assert result["status"] == "passed", result
    assert result["model_kind"] == "scripted" and result["paid_model_requests"] == 0
    assert result["verification_backend"] == "injected-test"
    assert result["sandbox_type"].endswith("DemoSimulatedSandbox")
    assert result["image_id"] == TEST_IMAGE
    assert result["repository_unchanged"]
    assert result["usage"]["synthetic"] and result["usage"]["total_tokens"] is None
    assert len(models) == 3 and [len(model.calls) for model in models] == [5, 4, 3]
    assert [item["scenario"] for item in result["runs"]] == list(demo.SCENARIOS)
    assert [item["outcome"] for item in result["runs"]] == ["ACCEPTED", "REJECTED", "ACCEPTED"]
    assert len({item["run_id"] for item in result["runs"]}) == 3
    output = Path(result["output_directory"])
    assert json.loads((output / "summary.json").read_bytes()) == result
    assert (output / "summary.md").read_text() == demo.demo_markdown(result)
    for item in result["runs"]:
        assert item["state"] == "FINISHED" and item["status"] == "passed"
        assert item["evidence_complete"] and item["artifacts_complete"]
        assert all(item["checks"].values()), item["checks"]
        assert item["isolated"] is False
        assert item["usage"]["synthetic"]
        assert item["usage"]["unknown_turns"] == item["agent"]["steps_used"]
        assert item["agent"]["http_attempts"] == 0
        directory = Path(item["artifact_directory"])
        assert directory.is_relative_to(output)
        assert inspect_run(directory)["artifacts_complete"]
        snapshot = read_events(directory, item["run_id"])
        assert snapshot.run["engine_kind"] == "fake"
        assert snapshot.run["image_id"] == TEST_IMAGE
        patch = EvidenceRef(**item["candidate"]["patch"]).read(directory, limit=100_000)
        assert (
            b"int best = -1;" in patch
            if item["scenario"] == "rejection"
            else b"samples.front()" in patch
        )
        final = item["independent"]
        assert final["evaluation_role"] == "independent"
        assert final["source_tree_sha256"] == item["candidate"]["source_tree_sha256"]
        assert final["source_tree_sha256"] != item["baseline"]["source_tree_sha256"]
        for test in final["tests"]:
            assert test["result"] is not None
            EvidenceRef(**test["result"]).read(directory, limit=100_000)
        for path in directory.rglob("*"):
            assert not path.is_symlink()
    rejection = result["runs"][1]
    assert rejection["harness_status"] == "failed" and rejection["reason_code"] == "F2P_FAILED"
    assert git(Path(result["repository"]), "status", "--porcelain") == ""
    for item in result["runs"]:
        task = Task.load(Path(result["tasks"][item["scenario"]]))
        workspace = task.workspace_root / item["run_id"]
        assert not (workspace / "repair").exists()
        assert not (workspace / "validation").exists()


@pytest.mark.parametrize("scenario", demo.SCENARIOS)
def test_selected_scenario_has_one_run(tmp_path, scenario):
    result = run_simulated(tmp_path / "demo", scenario)
    assert result["status"] == "passed", result
    assert list(result["tasks"]) == list(result["scripts"]) == result["scenarios"] == [scenario]
    assert [item["scenario"] for item in result["runs"]] == [scenario]


def test_recovery_preserves_same_run_checkpoint_event_prefix_and_counters(tmp_path):
    result = run_simulated(tmp_path / "demo", "recovery")
    run = result["runs"][0]
    recovery = run["recovery"]
    assert run["status"] == "passed", run["checks"]
    assert recovery["paused_run_id"] == recovery["resumed_run_id"] == run["run_id"]
    assert recovery["paused_state"] == "INTERRUPTED" and recovery["pause_after_step"] == 3
    assert (recovery["steps_before"], recovery["steps_after"]) == (3, 5)
    assert (recovery["tool_calls_before"], recovery["tool_calls_after"]) == (3, 4)
    output = Path(result["output_directory"])
    directory = Path(run["artifact_directory"])
    paused = json.loads(EvidenceRef(**recovery["paused_report"]).read(output, limit=1_000_000))
    assert paused["paused"] and paused["outcome"] is None and paused["artifacts_complete"]
    prefix = EvidenceRef(**recovery["paused_events"]).read(output, limit=1_000_000)
    assert (directory / "events.jsonl").read_bytes().startswith(prefix)
    manifest = json.loads(
        EvidenceRef(**recovery["checkpoint_manifest"]).read(directory, limit=100_000)
    )
    assert manifest["step_id"] == 3 and manifest["boundary"] == "model_input_ready"
    assert manifest["source_tree_sha256"] == run["candidate"]["source_tree_sha256"]
    patch = EvidenceRef(**recovery["checkpoint_patch"]).read(directory, limit=100_000)
    assert b"+    int best = samples.front();" in patch
    snapshot = read_events(directory, run["run_id"])
    assert snapshot.run["recovery_attempt"] == 1
    assert len([event for event in snapshot.events if event["type"] == "baseline_finished"]) == 1
    assert (
        len(
            [
                event
                for event in snapshot.events
                if event["type"] == "tool_started" and event["payload"]["name"] == "edit_file"
            ]
        )
        == 1
    )


def test_unexpected_acceptance_of_wrong_candidate_fails_demo(tmp_path):
    result = demo.run_demo(
        tmp_path / "demo", TEST_IMAGE, "rejection", sandbox_factory=SimulatedSandbox
    )
    assert result["status"] == "failed"
    run = result["runs"][0]
    assert run["outcome"] == "ACCEPTED" and run["evidence_complete"]
    assert run["checks"]["terminal_outcome"] is False
    assert run["checks"]["f2p_expected"] is False
    assert "terminal_outcome" in demo.demo_markdown(result)


def test_incomplete_evidence_fails_demo_even_for_accepted_patch(tmp_path, monkeypatch):
    original = demo.inspect_run

    def incomplete(directory):
        result = original(directory)
        result["evidence_complete"] = False
        return result

    monkeypatch.setattr(demo, "inspect_run", incomplete)
    result = run_simulated(tmp_path / "demo", "repair")
    assert result["status"] == "failed"
    assert result["runs"][0]["outcome"] == "ACCEPTED"
    assert result["runs"][0]["checks"]["evidence_complete"] is False


def test_recovery_baseline_failure_returns_failed_summary(tmp_path):
    class AllPass(SimulatedSandbox):
        def execute_test(self, name):
            return 0, "passed", "pass"

    result = demo.run_demo(tmp_path / "demo", TEST_IMAGE, "recovery", sandbox_factory=AllPass)
    assert result["status"] == "failed"
    run = result["runs"][0]
    assert run["outcome"] == "NOT_REPRODUCED"
    assert run["checks"]["paused_after_edit"] is False
    assert run["recovery"]["checks"] == {"paused_after_edit": False}


def test_preparation_creates_locked_tasks_deterministic_fixture_and_no_run(tmp_path):
    first = demo.prepare_demo(tmp_path / "first", TEST_IMAGE, sandbox_factory=DemoSimulatedSandbox)
    second = demo.prepare_demo(
        tmp_path / "second", TEST_IMAGE, sandbox_factory=DemoSimulatedSandbox
    )
    assert first["base_commit"] == second["base_commit"]
    assert not (Path(first["output_directory"]) / "runs").exists()
    for scenario, task_path in first["tasks"].items():
        task = Task.load(Path(task_path))
        assert task.environment.image == TEST_IMAGE
        assert task.revision == first["base_commit"]
        assert task.repository == Path(first["repository"])
        assert task.workspace_root.is_relative_to(Path(first["output_directory"]))
        assert task.output_root.is_relative_to(Path(first["output_directory"]))
        assert task.editable_paths == ("src/stats.cpp",)
        assert task.retain == "none"
        script = json.loads(Path(first["scripts"][scenario]).read_bytes())
        assert all("usage" not in step for step in script["steps"])
    for name in ("CMakeLists.txt", "src/stats.cpp", "tests/stats_test.cpp"):
        assert (Path(first["repository"]) / name).read_bytes() == (
            ROOT / "examples/cpp-bugs" / name
        ).read_bytes()
    assert {item["path"] for item in first["assets"]} == set(demo.DEMO_ASSETS)


def test_default_preparation_inspects_real_docker_image(tmp_path, monkeypatch):
    images = []

    def inspect(reference):
        images.append(reference)
        return ImageIdentity(TEST_IMAGE)

    monkeypatch.setattr(demo, "inspect_image", inspect)
    result = demo.prepare_demo(tmp_path / "demo", scenario="repair")
    assert images == ["repropatch-cpp:0.1"]
    assert result["verification_backend"] == "docker"
    assert result["sandbox_type"] == "repropatch.sandbox.DockerSandbox"
    assert Task.load(Path(result["tasks"]["repair"])).environment.image == TEST_IMAGE


def test_missing_docker_raises_before_output_creation(tmp_path, monkeypatch):
    def missing(reference):
        raise ReproPatchError("DOCKER_UNAVAILABLE: 需要本地 Docker")

    monkeypatch.setattr(demo, "inspect_image", missing)
    output = tmp_path / "demo"
    with pytest.raises(ReproPatchError, match="DOCKER_UNAVAILABLE"):
        demo.run_demo(output)
    assert not output.exists()


@pytest.mark.parametrize("scenario", ["unknown", "ALL", "", None, [], {}])
def test_invalid_scenario_preserves_files_and_has_no_side_effect(tmp_path, scenario):
    output = tmp_path / "demo"
    with pytest.raises(ReproPatchError, match="DEMO_SCENARIO_INVALID"):
        run_simulated(output, scenario)
    assert not output.exists()


@pytest.mark.parametrize("kind", ["directory", "file", "symlink", "dangling"])
def test_existing_output_is_preserved(tmp_path, kind):
    output = tmp_path / "demo"
    original = tmp_path / "original"
    original.write_bytes(b"keep")
    if kind == "directory":
        output.mkdir()
        (output / "keep.txt").write_bytes(b"keep")
    elif kind == "file":
        output.write_bytes(b"keep")
    else:
        output.symlink_to(original if kind == "symlink" else tmp_path / "missing")
    with pytest.raises(ReproPatchError, match="DEMO_OUTPUT_EXISTS|DEMO_OUTPUT_SYMLINK"):
        run_simulated(output)
    assert original.read_bytes() == b"keep"
    if kind == "directory":
        assert sorted(path.name for path in output.iterdir()) == ["keep.txt"]
        assert (output / "keep.txt").read_bytes() == b"keep"
    elif kind == "file":
        assert output.read_bytes() == b"keep"
    else:
        assert output.is_symlink()


def test_repeat_run_preserves_every_existing_file(tmp_path):
    output = tmp_path / "demo"
    run_simulated(output, "repair")
    before = {
        str(path.relative_to(output)): path.read_bytes()
        for path in output.rglob("*")
        if path.is_file()
    }
    with pytest.raises(ReproPatchError, match="DEMO_OUTPUT_EXISTS"):
        run_simulated(output)
    after = {
        str(path.relative_to(output)): path.read_bytes()
        for path in output.rglob("*")
        if path.is_file()
    }
    assert before == after


def test_symlinked_parent_is_rejected_without_writing_target(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(ReproPatchError, match="DEMO_OUTPUT_SYMLINK"):
        run_simulated(link / "nested" / "demo")
    assert list(real.iterdir()) == []


def test_output_inside_existing_demo_repository_is_rejected(tmp_path):
    prepared = demo.prepare_demo(
        tmp_path / "first", TEST_IMAGE, "repair", sandbox_factory=DemoSimulatedSandbox
    )
    repository = Path(prepared["repository"])
    output = repository / "nested-demo"
    with pytest.raises(ReproPatchError, match="DEMO_ROOT_OVERLAP"):
        run_simulated(output)
    assert not output.exists()
    assert git(repository, "status", "--porcelain") == ""


def test_output_inside_existing_run_is_rejected(tmp_path):
    directory = tmp_path / "run"
    directory.mkdir()
    (directory / "events.sqlite3").write_bytes(b"keep")
    with pytest.raises(ReproPatchError, match="DEMO_ROOT_OVERLAP"):
        run_simulated(directory / "nested-demo")
    assert sorted(path.name for path in directory.iterdir()) == ["events.sqlite3"]
    assert (directory / "events.sqlite3").read_bytes() == b"keep"


def test_output_created_during_preflight_is_preserved(tmp_path, monkeypatch):
    output = tmp_path / "demo"
    original = demo._scripts

    def concurrent_output(source, selected):
        scripts = original(source, selected)
        output.mkdir()
        (output / "keep.txt").write_bytes(b"keep")
        return scripts

    monkeypatch.setattr(demo, "_scripts", concurrent_output)
    with pytest.raises(ReproPatchError, match="DEMO_OUTPUT_EXISTS"):
        run_simulated(output)
    assert sorted(path.name for path in output.iterdir()) == ["keep.txt"]
    assert (output / "keep.txt").read_bytes() == b"keep"


def test_missing_sdk_raises_before_output_creation(tmp_path, monkeypatch):
    def missing(source):
        raise ReproPatchError("ENGINE_DEPENDENCY_MISSING: 请安装 repropatch[agent]")

    monkeypatch.setattr(demo, "sdk_script_bytes", missing)
    with pytest.raises(ReproPatchError, match="ENGINE_DEPENDENCY_MISSING"):
        run_simulated(tmp_path / "demo")
    assert not (tmp_path / "demo").exists()


def test_symlinked_packaged_assets_are_rejected(tmp_path, monkeypatch):
    root = tmp_path / "resources"
    root.mkdir()
    (root / "demo_assets").symlink_to(ROOT / "src/repropatch/demo_assets", target_is_directory=True)
    monkeypatch.setattr(demo, "files", lambda package: root)
    with pytest.raises(ReproPatchError, match="DEMO_ASSET_UNSAFE"):
        run_simulated(tmp_path / "demo")
    assert not (tmp_path / "demo").exists()


def test_parent_file_is_rejected_before_preparation(tmp_path):
    parent = tmp_path / "file"
    parent.write_text("keep")
    with pytest.raises(ReproPatchError, match="DEMO_OUTPUT_UNSAFE"):
        run_simulated(parent / "demo")
    assert parent.read_text() == "keep"


@pytest.mark.parametrize(
    "path",
    [
        ROOT / "examples/cpp-bugs/demo",
        ROOT / "src/repropatch/demo-output",
        ROOT / "src/repropatch/demo_assets/demo-output",
        ROOT,
    ],
)
def test_output_overlapping_fixture_or_package_is_rejected(path):
    with pytest.raises(ReproPatchError, match="DEMO_ROOT_OVERLAP"):
        run_simulated(path)


@pytest.mark.parametrize(
    "path",
    [
        Path("/etc/repropatch-demo"),
        Path("/proc/repropatch-demo"),
        Path("/tmp"),
        ROOT / ".git/demo",
        Path("/tmp/demo/../elsewhere"),
    ],
)
def test_unsafe_output_is_rejected(path):
    with pytest.raises(ReproPatchError, match="DEMO_OUTPUT_UNSAFE"):
        run_simulated(path)


@pytest.mark.parametrize("image", ["repropatch-cpp:0.1", "sha256:" + "0" * 64, "", "sha256:abc"])
def test_injected_backend_requires_explicit_fixed_test_image(tmp_path, image):
    with pytest.raises(ReproPatchError, match="DEMO_TEST_IMAGE_INVALID|demo.image"):
        demo.run_demo(tmp_path / "demo", image, sandbox_factory=DemoSimulatedSandbox)
    assert not (tmp_path / "demo").exists()


def test_invalid_factory_is_rejected_before_preparation(tmp_path):
    with pytest.raises(ReproPatchError, match="DEMO_SANDBOX_INVALID"):
        demo.run_demo(tmp_path / "demo", TEST_IMAGE, sandbox_factory=object())
    assert not (tmp_path / "demo").exists()


@pytest.mark.integration
def test_demo_compiles_fixture_with_explicit_trusted_local_test_backend(tmp_path):
    result = demo.run_demo(tmp_path / "demo", TEST_IMAGE, sandbox_factory=TrustedLocalSandbox)
    assert result["status"] == "passed", result
    assert result["verification_backend"] == "injected-test"
    assert all(run["isolated"] is False for run in result["runs"])


@pytest.mark.docker
@pytest.mark.skipif(
    os.environ.get("REPROPATCH_DOCKER_TESTS") != "1", reason="真实 Docker 验证由显式环境开关启用"
)
def test_demo_all_scenarios_with_real_docker(tmp_path):
    image = os.environ.get("REPROPATCH_TEST_IMAGE", demo.DEFAULT_IMAGE)
    result = demo.run_demo(tmp_path / "demo", image)
    assert result["status"] == "passed", result
    assert result["verification_backend"] == "docker"
    assert all(run["isolated"] is True for run in result["runs"])
    assert all(run["evidence_complete"] and all(run["checks"].values()) for run in result["runs"])
