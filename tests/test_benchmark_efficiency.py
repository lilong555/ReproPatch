"""Benchmark 模式只改变执行成本；补丁完整性与冷 Oracle 仍决定最终结果。"""

import json
from pathlib import Path

import pytest
from conftest import ROOT, SimulatedSandbox

from repropatch.errors import ReproPatchError
from repropatch.harness import Harness
from repropatch.sandbox import DockerSandbox


class FixtureRepair(Harness):
    """在无模型依赖的测试中走真实冻结、Git 往返及报告路径。"""

    replacement = "int best = samples.front();"

    def _agent(self, workspace):
        workspace.edit_text("src/stats.cpp", "int best = 0;", self.replacement)
        self.agent_stop_reason = "MODEL_FINISHED"


@pytest.mark.parametrize("correct", [True, False])
def test_exported_candidate_requires_the_same_external_cold_oracle(task, tmp_path, correct):
    harness = FixtureRepair(
        task, object(), tmp_path / "export", sandbox_factory=SimulatedSandbox, candidate_only=True
    )
    if not correct:
        harness.replacement = "int best = 0; // incomplete repair"
    exported = harness.run()
    assert exported["outcome"] == "INCONCLUSIVE", exported
    assert exported["reason_code"] == "EXTERNAL_ORACLE_REQUIRED"
    assert exported["verified"] is False
    assert exported["candidate_roundtrip_verified"] is True
    assert exported["benchmark"]["internal_verification"] == "skipped_candidate_only"
    assert [e["evaluation_role"] for e in exported["evaluations"]] == ["baseline"]
    assert exported["artifacts_complete"] and exported["cleanup_confirmed"]
    result = Harness(
        task,
        output_root=tmp_path / "oracle",
        patch_file=Path(exported["artifact_directory"]) / "patch.diff",
        sandbox_factory=SimulatedSandbox,
    ).run()
    assert result["outcome"] == ("ACCEPTED" if correct else "REJECTED"), result
    assert result["benchmark"]["internal_verification"] == "executed"
    assert [e["evaluation_role"] for e in result["evaluations"]] == ["baseline", "independent"]


def test_candidate_only_still_rejects_tampered_patch(task, tmp_path, monkeypatch):
    import repropatch.verification as verification

    original = verification.apply_candidate

    def corrupt_then_apply(target, candidate, directory, *args):
        (directory / candidate.patch.path).write_bytes(b"tampered")
        return original(target, candidate, directory, *args)

    monkeypatch.setattr(verification, "apply_candidate", corrupt_then_apply)
    result = FixtureRepair(
        task, object(), tmp_path / "runs", sandbox_factory=SimulatedSandbox, candidate_only=True
    ).run()
    assert result["outcome"] == "ERROR", result
    assert not result["candidate_roundtrip_verified"] and not result["verified"]


def test_candidate_export_deadline_is_not_reported_as_baseline_failure(task, tmp_path, monkeypatch):
    from repropatch.verification import StageDeadline

    def expired(*args):
        raise StageDeadline("independent deadline")

    monkeypatch.setattr("repropatch.harness.prepare_candidate_validation", expired)
    result = FixtureRepair(
        task, object(), tmp_path / "runs", sandbox_factory=SimulatedSandbox, candidate_only=True
    ).run()
    assert result["reproduced"]
    assert result["reason_code"] == "VERIFICATION_TIMEOUT"
    assert result["benchmark"]["internal_verification"] == "unavailable"
    assert not result["verified"] and result["cleanup_confirmed"]


def test_compiler_cache_is_shared_only_by_checks_and_removed_after_run(task, tmp_path):
    mounted = []
    stats_calls = 0

    class ObservedSandbox(SimulatedSandbox):
        def __enter__(self):
            mounted.append((self.source.name, getattr(self, "compiler_cache", None)))
            return super().__enter__()

        def run(self, argv):
            nonlocal stats_calls
            if argv[0] == "ccache":
                stats_calls += 1
                if stats_calls == 1:
                    raise RuntimeError("telemetry unavailable")
            return super().run(argv)

    class CheckedRepair(FixtureRepair):
        def _agent(self, workspace):
            assert self._agent_check(workspace, "reproduce")["passed"] is False
            super()._agent(workspace)
            assert self._agent_check(workspace, "verify")["passed"] is True

    result = CheckedRepair(
        task, object(), tmp_path / "runs", sandbox_factory=ObservedSandbox, compiler_cache=True
    ).run()
    assert result["outcome"] == "ACCEPTED", result
    checks = [e for e in result["evaluations"] if e["evaluation_role"] == "agent_check"]
    assert len(checks) == 2
    for check in checks:
        assert "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache" in check["configure"]["argv"]
    assert checks[0]["compiler_cache"]["stats_error"] == "RuntimeError"
    assert checks[1]["compiler_cache"]["stats"]["argv"] == ["ccache", "--print-stats"]
    caches = [path for name, path in mounted if "agent-check" in name]
    assert len(caches) == 2 and caches[0] == caches[1]
    assert caches[0].parent == Path(result["workspace_directory"])
    assert not caches[0].exists()
    assert all(path is None for name, path in mounted if "agent-check" not in name)
    assert result["independent"]["compiler_cache"] is None
    assert "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache" not in result["independent"]["configure"]["argv"]
    resources = json.loads((Path(result["artifact_directory"]) / "resources.json").read_text())
    assert resources["compiler_cache"]["exists"] is False


def test_verify_patch_entry_keeps_cold_verification(task, tmp_path):
    with pytest.raises(ReproPatchError, match="BENCHMARK_MODE"):
        Harness(task, patch_file=tmp_path / "patch", candidate_only=True)
    with pytest.raises(ReproPatchError, match="BENCHMARK_MODE"):
        Harness(task, patch_file=tmp_path / "patch", compiler_cache=True)


def test_cache_mount_keeps_original_container_isolation(tmp_path):
    source, cache = tmp_path / "source", tmp_path / "cache"
    source.mkdir()
    cache.mkdir()
    args = DockerSandbox(source, "repropatch-cpp:0.1", compiler_cache=cache).create_argv()
    assert args.count("--mount") == 2
    assert f"type=bind,source={source},target=/src,readonly" in args
    assert f"type=bind,source={cache},target=/cache" in args
    assert "--network=none" in args and "--read-only" in args
    assert "--env=CCACHE_COMPILERCHECK=content" in args
    assert not any("SLOPPINESS" in arg for arg in args)
    assert any(arg.startswith("--tmpfs=/build:") for arg in args)


@pytest.mark.sdk
def test_resume_preserves_candidate_mode_and_compiler_cache(task, tmp_path):
    from repropatch.models import load_sdk_script
    from repropatch.recovery import resume_run

    model, source = load_sdk_script(
        ROOT / "examples/models/fix-negative-maximum.json", with_source=True
    )
    harness = Harness(
        task,
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        pause_after_step=3,
        script_source=source,
        candidate_only=True,
        compiler_cache=True,
    )
    paused = harness.run()
    assert paused["paused"] and paused["artifacts_complete"], paused
    resumed = resume_run(harness.directory, sandbox_factory=SimulatedSandbox)
    assert resumed["reason_code"] == "EXTERNAL_ORACLE_REQUIRED", resumed
    assert resumed["candidate_roundtrip_verified"] and not resumed["verified"]
    assert resumed["benchmark"]["compiler_cache"] == "ccache"
    assert any(e["compiler_cache"] is not None for e in resumed["evaluations"])
    assert resumed["independent"] is None and resumed["cleanup_confirmed"]
